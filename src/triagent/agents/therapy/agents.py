"""
Agent classes for the Tx Gemma system using Google ADK.
Implements the multi-agent architecture for Tx Gemma.
"""

from google.adk.agents import LlmAgent

from triagent.agents.therapy.prompts import therapy_agent_prompt
from triagent.agents.therapy.tools import search_clinical_trials, rerank_trials, format_trials_response
from triagent.config import settings

# Therapy Agent
therapy_agent = LlmAgent(
    name="therapy_agent",
    model=settings.gemini_pro_model,
    instruction=therapy_agent_prompt,
    description="You are an expert therapy agent.",
    tools=[search_clinical_trials, rerank_trials, format_trials_response],
    output_key="therapy_agent_response",  # Stores output in state['therapy_agent_response']
)
