from typing import Protocol


class LLMProvider(Protocol):
    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        ...
