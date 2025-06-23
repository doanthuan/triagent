import asyncio
import nest_asyncio
from Bio import Medline, Entrez
from google.adk.tools import LongRunningFunctionTool
from triagent.agents.tx_emerging.services.trial.service import TrialService, PatientData
from triagent.agents.tx_emerging.services.rerank.service import TourRankService
from triagent.logging import logger
nest_asyncio.apply()

def parse_patient_data(patient_info: str) -> PatientData:
    """
    This tool is designed to parse patient data from a string.
    It uses the TrialService to parse patient data and returns the results.
    Args:
        patient_info (str): The patient information.

    Returns:
        PatientData: The parsed patient data.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(TrialService.parse_patient_data_from_string(patient_info))


def search_clinical_trials(patient_info: str) -> list[dict]:
    """
    This tool is designed to search for clinical trials based on patient data.
    It uses the TrialService to search for clinical trials and returns the results.
    Args:
        patient_info (str): The patient information.

    Returns:
        list[dict]: The results of the clinical trial search.
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(TrialService.search_clinical_trials(patient_info))

def rerank_trials(trials: list[dict], patient_info: str) -> list[dict]:
    """
    This tool is designed to rank clinical trials based on patient data.
    It uses the TrialService to rank clinical trials and returns the results.
    Args:
        trials (list[dict]): The trials to rank.
        patient_info (str): The patient information.

    Returns:
        list[dict]: The ranked trials.
    """
    rerank_service = TourRankService()
    # loop = asyncio.get_event_loop()
    # return loop.run_until_complete(rerank_service.rerank_trials(trials, patient_info))
    ranked_trials, scores = asyncio.run(rerank_service.rerank_trials(trials, patient_info))
    logger.info(f"Ranked trials: {ranked_trials}")
    logger.info(f"Scores: {scores}")
    return ranked_trials
