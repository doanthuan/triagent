from google.adk.agents import LlmAgent
from triagent.agents.research.agents import research_agent
from triagent.agents.treatment.agents import clinical_trial_agent
from triagent.config import settings

root_agent = LlmAgent(
    name="Router",
    model=settings.gemini_flash_model,
    instruction="""
    Route user requests. Instructions:s
    - Use research agent for drug toxicity prediction
    - Use clinical trial agent for clinical trial search or treatment recommendation.
    """,
    description="Main router.",
    sub_agents=[clinical_trial_agent, research_agent]
)
