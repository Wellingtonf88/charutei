"""Conversational Assistant: cache → KG → RAG (Sonnet) com citações, gating de Opus."""

from charutei_assistant.assistant import CAPABILITY, SYSTEM, Assistant, default_spec
from charutei_assistant.kg_resolver import KGAssistantResolver
from charutei_assistant.rag import DOCS_KIND, Document, DocumentStore, RagGenerator

__all__ = [
    "Assistant",
    "CAPABILITY",
    "SYSTEM",
    "default_spec",
    "KGAssistantResolver",
    "DocumentStore",
    "Document",
    "RagGenerator",
    "DOCS_KIND",
]
