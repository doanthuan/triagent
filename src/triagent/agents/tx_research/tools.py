import json
import os
from litellm import text_completion
from triagent.logging import logger
from Bio import Medline, Entrez

TDC_PROMPTS_JSON = {}
json_path = os.path.join(os.path.dirname(__file__), "assets", "tdc_prompts.json")
with open(json_path, "r") as f:
    TDC_PROMPTS_JSON = json.load(f)

TXGEMMA_MODEL = "google/txgemma-2b-predict"
SERVER_URL = "http://116.127.115.18:20994"

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
    Args:
        drug_smiles (str): The SMILES string of the drug to predict toxicity for.

    Returns:
        str: The predicted toxicity of the drug. (A) is not toxic, (B) is toxic
    """
    input_type = "{Drug SMILES}"
    task_name = "ClinTox"
    prompt = TDC_PROMPTS_JSON[task_name].replace(input_type, drug_smiles)
    logger.info(f"txgemma_predict: {prompt}")
    prediction =  txgemma_predict(prompt)
    if "(A)" in prediction:   
        return f"{drug_smiles} is not toxic!"
    elif "(B)" in prediction: 
        return f"{drug_smiles} is toxic!"
    return prediction


def predict_mutagenic_effect(drug_smiles: str) -> str:
    """
    This tool is designed to predict potential for mutagenic effect for humans in clinicial trials.
    Args:
        drug_smiles (str): The SMILES string of the drug to predict toxicity for.

    Returns:
        str: The predicted mutagenic effect of the drug. (A) is not mutagenic, (B) is mutagenic
    """
    input_type = "{Drug SMILES}"
    task_name = "AMES"
    prompt = TDC_PROMPTS_JSON[task_name].replace(input_type, drug_smiles)
    logger.info(f"txgemma_predict: {prompt}")
    prediction =  txgemma_predict(prompt)
    if "(A)" in prediction:   
        return f"{drug_smiles} is not mutagenic!"
    elif "(B)" in prediction: 
        return f"{drug_smiles} is mutagenic!"
    return prediction

def predict_reactant_SMILES(product_smiles: str) -> str:
    """
    Given a product SMILES string, predict the reactant SMILES string
    Args:
        product_smiles (str): The SMILES string of the product to predict reactant for.

    Returns:
        str: reactant SMILES string
    """
    input_type = "{Product SMILES}"
    task_name = "USPTO"
    prompt = TDC_PROMPTS_JSON[task_name].replace(input_type, product_smiles)
    logger.info(f"txgemma_predict: {prompt}")
    return txgemma_predict(prompt)


def predict_drug_synergy(drug1_smiles: str, drug2_smiles: str, cell_line_description: str) -> str:
    """
    Given two drug SMILES strings and a cell line description, predict the drug synergy
    Args:
        drug1_smiles (str): The SMILES string of the first drug to predict synergy for.
        drug2_smiles (str): The SMILES string of the second drug to predict synergy for.
        cell_line_description (str): The description of the cell line to predict synergy for.

    Returns:
        str: drug synergy
    """
    drug1_smiles_input = "{Drug1 SMILES}"
    drug2_smiles_input = "{Drug2 SMILES}"
    cell_line_description_input = "{Cell line description}"
    task_name = "OncoPolyPharmacology"
    prompt = TDC_PROMPTS_JSON[task_name].replace(drug1_smiles_input, drug1_smiles).replace(drug2_smiles_input, drug2_smiles).replace(cell_line_description_input, cell_line_description)
    logger.info(f"txgemma_predict: {prompt}")
    return txgemma_predict(prompt)

def predict_drug_target_interaction(drug_smiles: str, target_amino_acid_sequence: str) -> str:
    """
    Given a drug SMILES string and a target name, predict the drug target interaction
    Args:
        drug_smiles (str): The SMILES string of the drug to predict target interaction for.
        target_amino_acid_sequence (str): The amino acid sequence of the target to predict target interaction for.

    Returns:
        str: drug target interaction
    """
    drug_smiles_input = "{Drug SMILES}"
    target_amino_acid_sequence_input = "{Target amino acid sequence}"
    task_name = "BindingDB_kd"
    prompt = TDC_PROMPTS_JSON[task_name].replace(drug_smiles_input, drug_smiles).replace(target_amino_acid_sequence_input, target_amino_acid_sequence)
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
