import json
from litellm import text_completion
from triagent.logging import logger
from Bio import Medline, Entrez

TDC_PROMPTS_JSON = {}
with open("triagent/assets/tdc_prompts.json", "r") as f:
    TDC_PROMPTS_JSON = json.load(f)

TXGEMMA_MODEL = "google/txgemma-2b-predict"
SERVER_URL = "http://172.81.127.41:31648"

def txgemma_predict(prompt):    
    response = text_completion(
        model=f"hosted_vllm/{TXGEMMA_MODEL}",
        api_base=f"{SERVER_URL}/v1",
        prompt=prompt,
        temperature=0.01,
    )
    return response['choices'][0].text


def predict_drug_toxicity(drug_smiles: str) -> str:
    """
    This tool is designed to predict potential for toxicity for humans in clinicial trials.
    It uses the Tx Gemma model to predict the toxicity of a drug.
    Args:
        drug_smiles (str): The SMILES string of the drug to predict toxicity for.

    Returns:
        str: The predicted toxicity of the drug.
    """
    input_type = "{Drug SMILES}"
    task_name = "ClinTox"
    prompt = TDC_PROMPTS_JSON[task_name].replace(input_type, drug_smiles)
    logger.info(f"txgemma_predict: {prompt}")
    return txgemma_predict(prompt)


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
