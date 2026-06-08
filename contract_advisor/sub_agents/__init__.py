# CHANGED: Import from the new .ingestion.agent path
from .ingestion.agent import ingestion_agent
from .term_extractor.agent import term_extractor_agent
from .risk_evaluator.agent import risk_evaluator_agent
from .critic.agent import critic_agent

__all__ = [
    "ingestion_agent",
    "term_extractor_agent",
    "risk_evaluator_agent",
    "critic_agent",
]