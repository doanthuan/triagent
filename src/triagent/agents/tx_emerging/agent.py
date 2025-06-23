"""
Agent classes for the Tx Gemma system using Google ADK.
Implements the multi-agent architecture for Tx Gemma.
"""

import sys
sys.path.append("../../")

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from triagent.agents.tx_emerging.prompts import tx_emerging_agent_prompt
from triagent.agents.tx_emerging.tools import parse_patient_data, search_clinical_trials, rerank_trials
from triagent.config import settings

# Emerging Treatment Agent
root_agent = LlmAgent(
    name="emerging_treatment_agent",
    #model=LiteLlm(settings.litellm_openai_gpt_4o_mini_model),
    model=settings.gemini_flash_model,
    instruction=tx_emerging_agent_prompt,
    description="You are an expert tx emerging agent.",
    tools=[parse_patient_data, search_clinical_trials, rerank_trials],
    output_key="tx_emerging_agent_response",  # Stores output in state['tx_emerging_agent_response']
)
