import hashlib
import math
import struct
from collections.abc import Sequence

from app.config import Settings, get_settings


class EmbeddingUnavailable(RuntimeError):
    pass


def normalize_vector(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(float(value) ** 2 for value in values))
    if not norm:
        raise ValueError("Embedding vector has zero magnitude.")
    return [float(value) / norm for value in values]


def encode_vector(values: Sequence[float]) -> bytes:
    normalized = normalize_vector(values)
    return struct.pack(f"<{len(normalized)}f", *normalized)


def decode_vector(value: bytes, dimensions: int) -> tuple[float, ...]:
    if dimensions <= 0 or len(value) != dimensions * 4:
        raise ValueError("Stored embedding dimensions do not match its byte length.")
    return struct.unpack(f"<{dimensions}f", value)


def vector_fingerprint(model: str, text: str) -> str:
    return hashlib.sha256(f"{model}\0{text}".encode("utf-8")).hexdigest()


class EmbeddingService:
    def __init__(self, settings: Settings | None = None, client=None):
        self.settings = settings or get_settings()
        self._client = client

    @property
    def model(self) -> str:
        return self.settings.gemini_embedding_model

    @property
    def dimensions(self) -> int:
        return self.settings.gemini_embedding_dimensions

    def _get_client(self):
        if not self.settings.gemini_api_key:
            raise EmbeddingUnavailable("GEMINI_API_KEY is not configured for semantic retrieval.")
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.settings.gemini_api_key)
        return self._client

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        if not texts:
            return []
        try:
            from google.genai import types

            result = self._get_client().models.embed_content(
                model=self.model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=self.dimensions,
                ),
            )
            vectors = [normalize_vector(item.values or []) for item in (result.embeddings or [])]
        except EmbeddingUnavailable:
            raise
        except Exception as exc:
            raise EmbeddingUnavailable(f"Embedding provider failed ({type(exc).__name__}).") from exc
        if len(vectors) != len(texts) or any(len(vector) != self.dimensions for vector in vectors):
            raise EmbeddingUnavailable("Embedding provider returned an unexpected vector shape.")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]
