"""Online query serving: classify → retrieve/refuse → generate → validate."""

from src.serve.pipeline import answer_question

__all__ = ["answer_question"]
