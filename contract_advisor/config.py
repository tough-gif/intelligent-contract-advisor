"""Config module for the Contract Advisor agent."""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google.genai import types

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

logger = logging.getLogger(__name__)

class AgentConfig:
    """Configuration for the Contract Agent."""

    # GCP project id and location
    project_id: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    # Storage
    contract_bucket_name: str = os.getenv("CONTRACT_BUCKET_NAME", "")
    rulebook_bucket_name: str = os.getenv("RULEBOOK_BUCKET_NAME", "")

    # Gemini model config
    model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    temperature: float = float(os.getenv("GEMINI_MODEL_TEMPERATURE") or 0.1)
    top_p: float = float(os.getenv("GEMINI_MODEL_TOP_P") or 0.95)

config = AgentConfig()