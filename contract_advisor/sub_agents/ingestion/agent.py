"""Ingestion Agent Implementation"""

from google.adk.agents import LlmAgent
from google.genai import types

from ...config import config
from ...tools.gcs_connector import fetch_contract_from_gcs, upload_file_to_gcs
from . import prompts

ingestion_agent = LlmAgent(
    model=config.model_name,
    name="IngestionAgent",
    description="Fetches legal documents from Google Cloud Storage or uploads them from local storage.",
    instruction=prompts.INGESTION_PROMPT,
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    tools=[fetch_contract_from_gcs, upload_file_to_gcs],
)
