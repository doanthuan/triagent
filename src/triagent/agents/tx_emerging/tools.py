from triagent.agents.tx_emerging.services.trial.service import TrialService
from triagent.agents.tx_emerging.services.rerank.service import TourRankService
from triagent.logging import logger


def parse_patient_data(patient_info: str) -> dict:
    """
    This tool is designed to parse patient data from a string.
    It uses the TrialService to parse patient data and returns the results.
    Args:
        patient_info (str): The patient information.

    Returns:
        dict: The parsed patient data.
    """
    return TrialService.parse_patient_data_from_string(patient_info)

def search_clinical_trials(patient_data: dict) -> list[dict]:
    """
    This tool is designed to search for clinical trials based on patient data.
    It uses the TrialService to search for clinical trials and returns the results.
    Args:
        patient_data (dict): The patient data.

    Returns:
        list[dict]: The results of the clinical trial search.
    """
    return TrialService.search_clinical_trials(patient_data)

def rerank_trials(trials: list[dict], patient_info: str) -> list[dict]:
    """
    This tool is designed to rank clinical trials based on patient data.
    It uses the TrialService to rank clinical trials and returns the results.
    Args:
        trials (list[dict]): The clinical trials to rank.
        patient_info (str): The patient information.
    """
    rerank_service = TourRankService()
    ranked_trials, scores = rerank_service.rerank_trials(trials, patient_info)
    logger.info(f"Ranked trials: {ranked_trials}")
    logger.info(f"Scores: {scores}")
    return ranked_trials
