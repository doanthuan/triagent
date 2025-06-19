from Bio import Medline, Entrez
from google.adk.tools import LongRunningFunctionTool
from triagent.agents.treatment.services.trial.service import TrialService
from triagent.agents.treatment.services.rerank.service import TourRankService

def pubmed_search(query: str) -> str:
    """
    This tool is designed to search PubMed for articles related to a given query.
    It uses the Entrez API to search for articles and retrieves metadata for a few of the top articles (PMID, title, authors, journal, date, abstract)
    Args:
        query (str): The query to search for.

    Returns:
        str: The results of the PubMed search.
    """
    # Here, we are searching through PubMed and returning relevant articles
    pmids = list()
    handle = Entrez.esearch(db="pubmed", sort="relevance", term=query, retmax=3)
    record = Entrez.read(handle)
    pmids = record.get("IdList", [])
    handle.close()

    if not pmids:
        return f"No PubMed articles found for '{query}' Please try a simpler search query."

    fetch_handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="medline", retmode="text")
    records = list(Medline.parse(fetch_handle))
    fetch_handle.close()

    result_str = f"=== PubMed Search Results for: '{query}' ===\n"
    for i, record in enumerate(records, start=1):
        pmid = record.get("PMID", "N/A")
        title = record.get("TI", "No title available")
        abstract = record.get("AB", "No abstract available")
        journal = record.get("JT", "No journal info")
        pub_date = record.get("DP", "No date info")
        authors = record.get("AU", [])
        authors_str = ", ".join(authors[:3])
        result_str += (
            f"\n--- Article #{i} ---\n"
            f"PMID: {pmid}\n"
            f"Title: {title}\n"
            f"Authors: {authors_str}\n"
            f"Journal: {journal}\n"
            f"Publication Date: {pub_date}\n"
            f"Abstract: {abstract}\n")
    return f"Query: {query}\nResults: {result_str}"

async def search_clinical_trials_async(patient_info: str) -> dict:
    """
    This tool is designed to search for clinical trials based on patient data.
    It uses the TrialService to search for clinical trials and returns the results.
    Args:
        patient_info (str): The patient information.

    Returns:
        dict: The results of the clinical trial search.
    """
    return await TrialService.search_clinical_trials(patient_info)

search_clinical_trials = LongRunningFunctionTool(func=search_clinical_trials_async)

async def rerank_trials_async(trials: list[dict], patient_info: str) -> list[dict]:
    """
    This tool is designed to rank clinical trials based on patient data.
    It uses the TrialService to rank clinical trials and returns the results.
    Args:
        trials (list[dict]): The trials to rank.
        patient_info (str): The patient information.
    """
    rerank_service = TourRankService()
    return await rerank_service.rerank_trials(trials, patient_info)

rerank_trials = LongRunningFunctionTool(func=rerank_trials_async)