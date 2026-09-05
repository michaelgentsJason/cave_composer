"""Optional language-adapter boundary; explicit unsupported semantics are retained."""
from typing import Protocol
from .spec import load_spec


class LanguageAdapter(Protocol):
    def to_spec(self,prompt:str)->dict: ...


def from_prompt(prompt:str,adapter:LanguageAdapter)->dict:
    """Plug in a local rule parser or LLM; all results still pass strict CaveSpec checks.

    No network/LLM calls, heuristic guesses, or credentials are hidden in the core.
    """
    return load_spec(adapter.to_spec(prompt))
