from google.adk.agents import LlmAgent
from triagent.agents.tx_research.agent import root_agent as medical_research_agent
from triagent.agents.tx_emerging.agent import root_agent as emerging_treatment_agent
from triagent.agents.tx_verifier.agent import root_agent as fact_verifier_agent
from triagent.config import settings

root_agent = LlmAgent(
    name="medical_agent_orchestrator",
    model=settings.gemini_flash_model,
    instruction="""
    Route user requests. Instructions:
    - Use emerging_treatment_agent when user requests for emerging treatment recommendation.
    - Use medical_research_agent when user ask for any tasks related to drugs SMILES, toxicity, molecules, mutagenic, reactant, drug target interaction, etc.
    - Use fact_verifier_agent when user ask for fact verification.
    """,
    description="Medical Agent Orchestrator",
    sub_agents=[emerging_treatment_agent, medical_research_agent, fact_verifier_agent]
)
