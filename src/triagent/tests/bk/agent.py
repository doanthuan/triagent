"""
Agent classes for the Tx Gemma system using Google ADK.
Implements the multi-agent architecture for Tx Gemma.
"""

import sys
sys.path.append("../../")

from google.adk.agents import LlmAgent

from triagent.agents.tx_emerging.prompts import clinical_trial_search_agent_prompt, patient_extractor_agent_prompt, rerank_agent_prompt
from triagent.agents.tx_emerging.tools import search_clinical_trials, rerank_trials, parse_patient_data
from triagent.config import settings

# Patient Extractor Agent
patient_extractor_agent = LlmAgent(
    name="patient_extractor_agent", 
    model=settings.gemini_pro_model,
    instruction=patient_extractor_agent_prompt,
    description="You are an expert patient extractor agent.",
    tools=[parse_patient_data],
    output_key="patient_extractor_agent_response",  # Stores output in state['patient_extractor_agent_response']
)

# Clinical Trial Search Agent
clinical_trial_search_agent = LlmAgent(
    name="clinical_trial_search_agent",
    model=settings.gemini_pro_model,
    instruction=clinical_trial_search_agent_prompt,
    description="You are an expert clinical trial search agent.",
    tools=[search_clinical_trials],
    output_key="clinical_trial_search_agent_response",  # Stores output in state['clinical_trial_search_agent_response']
)

# Rerank Agent
rerank_agent = LlmAgent(
    name="rerank_agent",
    model=settings.gemini_pro_model,
    instruction=rerank_agent_prompt,
    description="You are an expert rerank agent.",
    tools=[rerank_trials],
    output_key="rerank_agent_response",  # Stores output in state['rerank_agent_response']
)
