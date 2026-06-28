import httpx
from fastapi import HTTPException

from app.config import get_settings


class DeepSeekProvider:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def chat(self, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
        if not self.settings.deepseek_api_key:
            raise HTTPException(status_code=500, detail="DEEPSEEK_API_KEY is not configured.")

        url = f"{self.settings.deepseek_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.deepseek_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"DeepSeek API error: {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Failed to call DeepSeek API.") from exc

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HTTPException(status_code=502, detail="DeepSeek API returned an unexpected response.") from exc
