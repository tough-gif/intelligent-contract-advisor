"""Term Extractor Agent Implementation"""

from google.adk.agents import LlmAgent
from google.genai import types
from ...config import config
from . import prompts


def ensure_contract_text(callback_context, **kwargs):
    """Fallback in case the main orchestrator triggers this without fetching a contract."""
    state = callback_context.state
    if "current_contract_text" not in state:
        state["current_contract_text"] = "[NO CONTRACT LOADED IN CONTEXT]"

term_extractor_agent = LlmAgent(
    model=config.model_name,
    name="TermExtractorAgent",
    description="Extracts factual metadata, dates, parties, and financial terms directly from the contract text.",
    instruction=prompts.TERM_EXTRACTOR_PROMPT,
    generate_content_config=types.GenerateContentConfig(
        temperature=config.temperature,
        top_p=config.top_p,
    ),
    before_agent_callback=ensure_contract_text,
    output_key="extracted_terms", 
)