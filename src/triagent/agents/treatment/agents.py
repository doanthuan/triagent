"""
Agent classes for the Tx Gemma system using Google ADK.
Implements the multi-agent architecture for Tx Gemma.
"""

from google.adk.agents import LlmAgent

from triagent.agents.treatment.prompts import clinical_trial_agent_prompt, ranking_agent_prompt
from triagent.agents.treatment.tools import search_clinical_trials, rerank_trials
from triagent.config import settings

# Treatment Agent
treatment_agent = LlmAgent(
    name="treatment_agent",
    model=settings.gemini_pro_model,
    instruction=clinical_trial_agent_prompt,
    description="You are an expert clinical trial agent.",
    tools=[search_clinical_trials],
    output_key="clinical_trial_agent_response",  # Stores output in state['clinical_trial_agent_response']
)
