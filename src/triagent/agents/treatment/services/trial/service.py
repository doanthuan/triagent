import json
import re
import asyncio
import aiohttp
from litellm import acompletion
from triagent.config import settings
from triagent.logging import logger
from triagent.agents.treatment.services.trial.prompts import CLINICAL_TRIALS_SEARCH_QUERY_PROMPT, CLINICAL_TRIAL_ELIGIBILITY_PROMPT, PATIENT_DATA_EXTRACTION_PROMPT
from triagent.agents.treatment.services.trial.entity import PatientData
from triagent.agents.treatment.services.trial.utils import parse_json_from_response


class TrialService:
    @staticmethod
    async def _parse_patient_data_from_string(patient_info: str) -> PatientData:
        """
        Uses an LLM to extract structured patient data from an unstructured string.

        Args:
            patient_info (str): The unstructured patient information.

        Returns:
            PatientData: The structured patient data.
        """
        system_prompt = PATIENT_DATA_EXTRACTION_PROMPT
        user_prompt = "Unstructured Patient Information: \n" + patient_info
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response = await acompletion(
            model=settings.litellm_model_default,
            messages=messages,
            stream=False,
        )
        content = response.choices[0].message.content
        logger.info(f"Patient data extraction response: {content}")
        data = parse_json_from_response(content)
        logger.info(f"Parsed patient data: {data}")
        return PatientData(**data)

    @staticmethod
    async def _generate_clinical_trial_search_criteria(patient_data: PatientData) -> str:
        """
        Generates a search query that can be used to call the clinical trial API on https://clinicaltrials.gov.

        Args:
            biomarkers (str): The biomarkers information of the patient.
            histology (str): The histology information of the patient.
            staging (str): The staging information of the patient.
        """
        system_prompt = CLINICAL_TRIALS_SEARCH_QUERY_PROMPT
        user_prompt = "Structured Patient Attributes: \ndata= " + json.dumps({
            'biomarkers': patient_data.biomarkers,
            'histology': patient_data.histology,
            'staging': patient_data.staging,
        }, indent=4)
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await acompletion(
            model=settings.litellm_model_default,
            messages=messages,
            stream=False,
        )

        clinical_trials_query = response.choices[0].message.content
        # Remove triple quotes from clinical_trials_query
        clinical_trials_query = clinical_trials_query.replace('```', '')
        return clinical_trials_query
    
    @staticmethod
    async def _search_clinical_trials_with_query(clinical_trials_query: str, limit: int = 1000) -> list[dict]:
        """
        Searches for clinical trials based on a query.
        """
        params = {
            "query.term": clinical_trials_query,
            "pageSize": 1000,
            "filter.overallStatus": "RECRUITING",
            "fields": "ConditionsModule|EligibilityModule|IdentificationModule"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get("https://clinicaltrials.gov/api/v2/studies", params=params) as resp:
                resp.raise_for_status()
                result = await resp.json()

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
            contacts_module = protocol.get("contactsLocationsModule", {})

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
                "arm_groups": interventions_module.get("armGroups", []),
                "eligibility": protocol.get("eligibilityModule", {}),
                "sponsor": protocol.get("sponsorCollaboratorsModule", {})
                .get("leadSponsor", {})
                .get("name"),
                "country": contacts_module.get("locations", []),
                "completion_date": status_module.get(
                    "completionDateStruct",
                    {},
                ).get("date"),
            }

            # get the country from the country field
            country_set = set()
            for loc in trial_info["country"]:
                new_country = loc.get("country", "")
                if new_country:
                    country_set.add(new_country)
            trial_info["country"] = list(country_set)

            if trial_info["nct_id"] not in seen_nct_ids:
                trials_data.append(trial_info)
                seen_nct_ids.add(trial_info["nct_id"])

            # If a trial limit is specified, stop when reached
            if limit and len(trials_data) >= limit:
                logger.info(f"Reached limit of {limit} trials")
                return trials_data[:limit]
            
        return trials_data

    @staticmethod
    async def search_clinical_trials(patient_info: str) -> list[dict]:
        """
        Asynchronously searches for clinical trials based on patient data and returns a response for each trial, indicating Yes/No if the patient meets all eligibility criteria. Additionally provides an exaplanation as to why.

        Args:
            patient_info(str): The patient information.

        Returns:
            str: A JSON string containing the responses for each clinical trial.
        """
        if not patient_info:
            logger.error("No patient information provided")
            return []

        # Parse patient data from string
        patient_data = await TrialService._parse_patient_data_from_string(patient_info)
        logger.info(f"Parsed patient data: {patient_data}")

        # Generate clinical trial search criteria
        clinical_trials_query = await TrialService._generate_clinical_trial_search_criteria(patient_data)
        logger.info(f"Generated clinical trial search criteria: {clinical_trials_query}")

        # Search for clinical trials
        trials = await TrialService._search_clinical_trials_with_query(clinical_trials_query)
        logger.info(f"Clinical trials found: {len(trials)}")

        return trials

    @staticmethod
    async def match_trials_to_patient(trials: list[dict], patient_data: PatientData) -> list[dict]:
        trial_matching_tasks = []
        for trial in trials:
            system_prompt = CLINICAL_TRIAL_ELIGIBILITY_PROMPT
            user_prompt = "Structured Patient Attributes: \ndata= " + patient_data.model_dump_json(indent=4) + "\nClinical Trial Eligibility Criteria:\n" + json.dumps(trial, indent=4)
            response = acompletion(
                model=settings.litellm_model_default,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                stream=False,
            )
            trial_matching_tasks.append(response)
        trial_matching_results = await asyncio.gather(*trial_matching_tasks)
        eligible_trials = []
        for trial, trial_matching_result in zip(trials, trial_matching_results):
            eligibility_result = str(trial_matching_result.choices[0].message.content)
            if eligibility_result == "Yes":
                eligible_trials.append(trial)
            else:
                logger.info(f"Trial {trial['protocolSection']['identificationModule']['nctId']} is not eligible for the patient. Reason: {eligibility_result}")

        return eligible_trials

    @staticmethod
    def format_trials_human_readable(trials: list[dict]) -> str:
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
            lines.append(f"  Sponsor: {trial.get('sponsor', 'N/A')}")
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


