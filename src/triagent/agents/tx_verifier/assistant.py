import json
import time
import uuid
from typing import Dict, List, Optional

from google.adk.events.event import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from triagent.agents.tx_verifier.agent import FactVerifierOrchestrator
from triagent.agents.tx_verifier.entity import FactVerifierResponse
from triagent.agents.tx_verifier.utils import parse_final_response
from triagent.logging import logger


class FactVerifierAssistant:
    """
    Service class for fact verifier using AI agents.
    Provides methods to verify facts and claims using a conversational AI agent.
    """

    APP_NAME = "fact_verifier_assistant"

    def __init__(self):
        # Initialize session service and runner
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            agent=FactVerifierOrchestrator(),
            app_name=self.APP_NAME,
            session_service=self.session_service,
        )

    async def verify_text(
        self,
        fact_text: str,
        fact_context: Optional[dict] = None,
    ) -> List[FactVerifierResponse]:
        """
        Run fact checking on the provided prompt using the AI agent.

        Args:
            fact_text (str): The text containing claims to be fact checked
            context (Optional[dict]): The context of the fact checking

        Returns:
            Optional[Any]: The parsed fact checking results, or None if there was an error
        """
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        # Create a new session
        session = self.session_service.create_session(
            app_name=self.APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if fact_context is None:
            fact_context = {
                "disease": "",
                "patient_summary": "",
            }
        logger.info(f"Setting fact context: {fact_context}")
        context_event = Event(
            invocation_id="init_context",
            author="system",  # Or 'agent', 'tool' etc.
            actions=EventActions(state_delta=fact_context),
            timestamp=time.time(),
        )
        self.session_service.append_event(session, context_event)

        query = f"""
        ## MEDICAL INFORMATION TO FACT-CHECK
        {json.dumps(fact_text, indent=2) if isinstance(fact_text, dict) else fact_text}
        """

        # Prepare and send the content
        content = types.Content(role="user", parts=[types.Part(text=query)])
        events = self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )

        # Process events
        async for event in events:
            if event.is_final_response():
                logger.info(
                    f"Final event: {event.model_dump_json(indent=2, exclude_none=True)}",
                )

        # Get final session state
        session = self.session_service.get_session(
            app_name=self.APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        logger.info(f"Final state: {session.state}")

        if "final_results" not in session.state:
            logger.error("Error running fact check")
            return []

        # Parse and return results
        fv_results = parse_final_response(session.state["final_results"])
        logger.info(f"Fact verifier final results: {fv_results}")
        return fv_results
