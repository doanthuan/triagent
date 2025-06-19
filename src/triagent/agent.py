from google.adk.agents import LlmAgent
from triagent.agents.med_research.agents import research_agent
from triagent.agents.therapy.agents import therapy_agent
from triagent.config import settings

root_agent = LlmAgent(
    name="Router",
    model=settings.gemini_flash_model,
    instruction="""
    Route user requests. Instructions:s
    - Use research agent for drug toxicity prediction   
    - Use therapy agent for clinical trial search or treatment recommendation.
    """,
    description="Main router.",
    sub_agents=[therapy_agent, research_agent]
)
