"""The Main Orchestrator for the Contract Advisor"""

import logging
from google.adk.agents import SequentialAgent, LlmAgent
from google.genai import types
from .config import config
from . import prompts
from .sub_agents import (
    ingestion_agent,
    term_extractor_agent,
    risk_evaluator_agent,
    critic_agent
)

logger = logging.getLogger(__name__)

def extract_attachments_callback(callback_context, **kwargs):
    """Scans the user's message for attachments and records them in state."""
    session = callback_context._invocation_context.session
    # Access state safely
    state = callback_context.state
    uploaded_files = list(state.get("uploaded_files", []))
    
    # Check all events in the session to find attachments
    for event in session.events:
        if event.author == "user" and event.content and event.content.parts:
            for part in event.content.parts:
                filename = None
                if part.file_data:
                    filename = part.file_data.file_uri
                elif part.inline_data:
                    # If it's inline, we could generate a name or handle it here
                    pass
                
                if filename and filename not in uploaded_files:
                    uploaded_files.append(filename)
    
    if uploaded_files:
        state["uploaded_files"] = uploaded_files
        logger.info(f"Recorded UI attachments in state: {uploaded_files}")

# 1. The Sequential Pipeline (The Back Office)
contract_pipeline = SequentialAgent(
    name="ContractReviewPipeline",
    description="Run this to fetch, extract, evaluate, and summarize a legal contract from GCS.",
    sub_agents=[
        ingestion_agent,       # Step 1: Fetch the doc
        term_extractor_agent,  # Step 2: Pull the metadata
        risk_evaluator_agent,  # Step 3: Evaluate against the playbook
        critic_agent           # Step 4: Format and deliver the final report
    ]
)

# 2. The Conversational Router (The Front Desk)
root_agent = LlmAgent(
    model=config.model_name,
    name="LeadContractAdvisor",
    description="Handles conversational greetings and routes contract review requests to the strict deterministic pipeline.",
    instruction=prompts.FRONT_DESK_PROMPT,
    sub_agents=[contract_pipeline], 
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
    ),
    before_agent_callback=extract_attachments_callback,
)
