"""Botmartz VORTEX Omni-RAG Engine with Native VeriFAI™ Grounding."""

from .verifai import VeriFAIEngine, VeriFAIResponse, VeriFAIClaim, VeriFAICitation, VeriFAIVerdict

__version__ = "0.1.0"
__all__ = [
    "VeriFAIEngine",
    "VeriFAIResponse",
    "VeriFAIClaim",
    "VeriFAICitation",
    "VeriFAIVerdict",
]
