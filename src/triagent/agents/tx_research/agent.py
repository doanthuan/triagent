"""
Agent classes for the research system using Google ADK.
Implements the multi-agent architecture for research.
"""
import sys
sys.path.append("../../")

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool

from triagent.agents.tx_research.prompts import research_agent_prompt, google_search_prompt
from triagent.agents.tx_research.tools import pubmed_search, predict_drug_toxicity, predict_mutagenic_effect, predict_reactant_SMILES, predict_drug_synergy, predict_drug_target_interaction
from triagent.config import settings

search_agent = LlmAgent(
    name="search_agent",
    model=settings.gemini_pro_model,
    instruction=google_search_prompt,
    description="You are a Google Search Agent",
    tools=[google_search],
    output_key="search_agent_response",  # Stores output in state['search_agent_response']
)

# Research Agent
root_agent = LlmAgent(
    name="medical_research_agent",
    model=settings.gemini_pro_model,
    instruction=research_agent_prompt,
    description="You are a Medical Deep Research Agent. Your role is to perform thorough and accurate research on complex medical topics.",
    tools=[AgentTool(agent=search_agent), pubmed_search, predict_drug_toxicity, predict_mutagenic_effect, predict_reactant_SMILES, predict_drug_synergy, predict_drug_target_interaction],
    output_key="medical_research_agent_response",  # Stores output in state['medical_research_agent_response']
)

