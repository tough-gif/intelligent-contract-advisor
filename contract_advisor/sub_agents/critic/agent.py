"""Critic Agent Implementation"""

from google.adk.agents import LlmAgent
from google.genai import types
from ...config import config
from . import prompts


critic_agent = LlmAgent(
    model=config.model_name,
    name="CriticAgent",
    description="Synthesizes the extracted terms and risk evaluation into a final formatted report.",
    instruction=prompts.CRITIC_PROMPT,
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)