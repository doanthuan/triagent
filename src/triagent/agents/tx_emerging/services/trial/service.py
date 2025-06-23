import json
import re
import requests
from litellm import completion
from triagent.config import settings
from triagent.logging import logger
from triagent.agents.tx_emerging.services.trial.prompts import CLINICAL_TRIALS_SEARCH_QUERY_PROMPT, CLINICAL_TRIAL_ELIGIBILITY_PROMPT, PATIENT_DATA_EXTRACTION_PROMPT
from triagent.agents.tx_emerging.services.trial.entity import PatientData
from triagent.agents.tx_emerging.services.trial.utils import parse_json_from_response


class TrialService:
    @staticmethod
    def parse_patient_data_from_string(patient_info: str) -> dict:
        """
        Uses an LLM to extract structured patient data from an unstructured string.

        Args:
            patient_info (str): The unstructured patient information.

        Returns:
            dict: The structured patient data.
        """
        system_prompt = PATIENT_DATA_EXTRACTION_PROMPT
        user_prompt = "Unstructured Patient Information: \n" + patient_info
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = completion(
            model=settings.litellm_model_default,
            messages=messages,
            stream=False,
        )
        content = response.choices[0].message.content
        logger.info(f"Patient data extraction response: {content}")
        data = parse_json_from_response(content)
        logger.info(f"Parsed patient data: {data}")
        return data

    @staticmethod
    def _generate_clinical_trial_search_criteria(patient_data: dict) -> str:
        """
        Generates a search query that can be used to call the clinical trial API on https://clinicaltrials.gov.

        Args:
            patient_data: dict
        """
        system_prompt = CLINICAL_TRIALS_SEARCH_QUERY_PROMPT
        logger.info(f"Patient data: {patient_data}")
        patient_data_query_json = {}
        if 'biomarkers' in patient_data:
            patient_data_query_json['biomarkers'] = patient_data['biomarkers']
        if 'histology' in patient_data:
            patient_data_query_json['histology'] = patient_data['histology']
        if 'staging' in patient_data:
            patient_data_query_json['staging'] = patient_data['staging']

        user_prompt = "Structured Patient Attributes: \ndata= " + json.dumps(patient_data_query_json, indent=4)
        logger.info(f"Generate_clinical_trial_search_criteria with user prompt: {user_prompt}")
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = completion(
            model=settings.litellm_model_default,
            messages=messages,
            stream=False,
        )

        clinical_trials_query = response.choices[0].message.content
        # Remove triple quotes from clinical_trials_query
        clinical_trials_query = clinical_trials_query.replace('```', '')
        return clinical_trials_query
    
    @staticmethod
    def _search_clinical_trials_with_query(clinical_trials_query: str, limit: int = 10) -> list[dict]:
        """
        Searches for clinical trials based on a query.
        """
        params = {
            "query.term": clinical_trials_query,
            "pageSize": limit,
            "filter.overallStatus": "RECRUITING",
        }
        try:
            resp = requests.get("https://clinicaltrials.gov/api/v2/studies", params=params)
            resp.raise_for_status()
            result = resp.json()

            studies = result["studies"]
            seen_nct_ids = set()
            trials_data = []
            for study in studies:
                protocol = study.get("protocolSection", {})
                identification = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                design_module = protocol.get("designModule", {})
                description_module = protocol.get("descriptionModule", {})
                interventions_module = protocol.get(
                    "armsInterventionsModule",
                    {},
                )
                trial_info = {
                    "nct_id": identification.get("nctId"),
                    "title": identification.get("briefTitle"),
                    "status": status_module.get("overallStatus"),
                    "phase": design_module.get("phases", []),
                    "study_type": design_module.get("studyType"),
                    "brief_summary": description_module.get("briefSummary"),
                    "detailed_description": description_module.get(
                        "detailedDescription",
                    ),
                    "interventions": interventions_module.get(
                        "interventions",
                        [],
                    ),
                    "eligibility": protocol.get("eligibilityModule", {}),
                    "completion_date": status_module.get(
                        "completionDateStruct",
                        {},
                    ).get("date"),
                }

                if trial_info["nct_id"] not in seen_nct_ids:
                    trials_data.append(trial_info)
                    seen_nct_ids.add(trial_info["nct_id"])

                # If a trial limit is specified, stop when reached
                if limit and len(trials_data) >= limit:
                    logger.info(f"Reached limit of {limit} trials")
                    return trials_data[:limit]
        except Exception as e:
            logger.error(f"Error searching clinical trials with query: {clinical_trials_query}")
            logger.error(f"Error: {e}")
            return []
            
        return trials_data

    @staticmethod
    def search_clinical_trials(patient_data: dict) -> list[dict]:
        """
        Asynchronously searches for clinical trials based on patient data and returns a response for each trial, indicating Yes/No if the patient meets all eligibility criteria. Additionally provides an exaplanation as to why.

        Args:
            patient_data(dict): The patient data.

        Returns:
            str: A JSON string containing the responses for each clinical trial.
        """
        if not patient_data:
            logger.error("No patient information provided")
            return []

        # Generate clinical trial search criteria
        clinical_trials_query = TrialService._generate_clinical_trial_search_criteria(patient_data)
        logger.info(f"Generated clinical trial search criteria: {clinical_trials_query}")

        # Search for clinical trials
        trials = TrialService._search_clinical_trials_with_query(clinical_trials_query)
        logger.info(f"Clinical trials found: {len(trials)}")

        return trials

    @staticmethod
    def match_trials_to_patient(trials: list[dict], patient_data: dict) -> list[dict]:
        eligible_trials = []
        for trial in trials:
            system_prompt = CLINICAL_TRIAL_ELIGIBILITY_PROMPT
            user_prompt = "Structured Patient Attributes: \ndata= " + patient_data.model_dump_json(indent=4) + "\nClinical Trial Eligibility Criteria:\n" + json.dumps(trial, indent=4)
            response = completion(
                model=settings.litellm_model_default,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False,
            )
            eligibility_result = str(response.choices[0].message.content)
            if eligibility_result == "Yes":
                eligible_trials.append(trial)
            else:
                try:
                    nct_id = trial['protocolSection']['identificationModule']['nctId']
                    logger.info(f"Trial {nct_id} is not eligible for the patient. Reason: {eligibility_result}")
                except KeyError:
                    logger.info(f"Trial is not eligible for the patient. Reason: {eligibility_result}")
        return eligible_trials

    @staticmethod
    def format_trials_response(trials: list[dict]) -> str:
        """
        Formats a list of clinical trial dictionaries into a human-readable text summary.

        Args:
            trials (list[dict]): List of clinical trial dictionaries.

        Returns:
            str: Human-readable summary of trials.
        """
        if not trials:
            return "No clinical trials found."
        lines = []
        for idx, trial in enumerate(trials, 1):
            lines.append(f"Trial {idx}:")
            lines.append(f"  Title: {trial.get('title', 'N/A')}")
            lines.append(f"  NCT ID: {trial.get('nct_id', 'N/A')}")
            lines.append(f"  Status: {trial.get('status', 'N/A')}")
            phase = trial.get('phase')
            if isinstance(phase, list):
                phase = ', '.join(phase)
            lines.append(f"  Phase: {phase or 'N/A'}")
            lines.append(f"  Study Type: {trial.get('study_type', 'N/A')}")
            countries = trial.get('country', [])
            if isinstance(countries, list):
                countries = ', '.join(countries)
            lines.append(f"  Country: {countries or 'N/A'}")
            lines.append(f"  Completion Date: {trial.get('completion_date', 'N/A')}")
            brief_summary = trial.get('brief_summary')
            if brief_summary:
                lines.append(f"  Brief Summary: {brief_summary}")
            detailed_description = trial.get('detailed_description')
            if detailed_description:
                lines.append(f"  Detailed Description: {detailed_description}")
            interventions = trial.get('interventions', [])
            if interventions:
                if isinstance(interventions, list):
                    interventions = ', '.join([str(i) for i in interventions])
                lines.append(f"  Interventions: {interventions}")
            lines.append("")  # Blank line between trials
        return '\n'.join(lines)


