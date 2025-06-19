"""
Agent classes for the research system using Google ADK.
Implements the multi-agent architecture for research.
"""

from google.adk.agents import LlmAgent

from triagent.agents.med_research.prompts import research_agent_prompt
from triagent.agents.med_research.tools import predict_drug_toxicity, pubmed_search
from triagent.config import settings

# Research Agent
research_agent = LlmAgent(
    name="research_agent",
    model=settings.gemini_pro_model,
    instruction=research_agent_prompt,
    description="You are an expert therapeutic agent. You answer accurately and thoroughly.",
    tools=[predict_drug_toxicity, pubmed_search],
    output_key="research_agent_response",  # Stores output in state['research_agent_response']
)
