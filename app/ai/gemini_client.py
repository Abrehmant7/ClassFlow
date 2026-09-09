from typing import Any

from fastapi import status
from google import genai
from google.genai import types

from app.core.config import settings
from app.core.exceptions import ClassFlowError


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        embedding_model: str | None = None,
        generation_model: str | None = None,
        embedding_dimensions: int | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.embedding_model = embedding_model or settings.GEMINI_EMBEDDING_MODEL
        self.generation_model = generation_model or settings.GEMINI_GENERATION_MODEL
        self.embedding_dimensions = embedding_dimensions or settings.RAG_EMBEDDING_DIMENSIONS
        self._client = client

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self._embed([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0]

    async def embed_documents(self, texts: list[str], title: str | None = None) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        batch_size = settings.RAG_EMBEDDING_BATCH_SIZE
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            all_embeddings.extend(
                await self._embed(batch, task_type="RETRIEVAL_DOCUMENT", title=title)
            )
        return all_embeddings

    async def generate_answer(self, question: str, contexts: list[str]) -> str:
        numbered_context = "\n\n".join(
            f"[{index}] {context}" for index, context in enumerate(contexts, start=1)
        )
        prompt = (
            f"Question:\n{question}\n\n"
            f"ClassFlow sources:\n{numbered_context}\n\n"
            "Answer using only the ClassFlow sources. Cite supporting source numbers "
            "in square brackets, for example [1]. Cite only sources that directly "
            "support claims in the answer, and do not cite merely related sources. "
            "Every factual claim must have a citation. Multiple sources may be cited "
            "as [1, 2]."
        )

        try:
            response = await self._get_client().aio.models.generate_content(
                model=self.generation_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are the ClassFlow class assistant. Do not use outside knowledge. "
                        "If the supplied sources do not answer the question, say that the "
                        "information is not available in the class materials."
                    ),
                    temperature=0.1,
                    max_output_tokens=settings.RAG_MAX_OUTPUT_TOKENS,
                ),
            )
        except ClassFlowError:
            raise
        except Exception as exc:
            raise ClassFlowError(
                "The AI answer service is unavailable",
                "RAG_GENERATION_UNAVAILABLE",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        answer = (response.text or "").strip()
        if not answer:
            raise ClassFlowError(
                "The AI answer service returned an empty response",
                "RAG_EMPTY_GENERATION",
                status.HTTP_502_BAD_GATEWAY,
            )
        return answer

    async def _embed(
        self,
        texts: list[str],
        task_type: str,
        title: str | None = None,
    ) -> list[list[float]]:
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.embedding_dimensions,
        )
        if title is not None and task_type == "RETRIEVAL_DOCUMENT":
            config.title = title

        try:
            response = await self._get_client().aio.models.embed_content(
                model=self.embedding_model,
                contents=texts,
                config=config,
            )
        except ClassFlowError:
            raise
        except Exception as exc:
            raise ClassFlowError(
                "The AI embedding service is unavailable",
                "RAG_EMBEDDING_UNAVAILABLE",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc

        embeddings = response.embeddings or []
        values = [embedding.values or [] for embedding in embeddings]
        if len(values) != len(texts) or any(
            len(embedding) != self.embedding_dimensions for embedding in values
        ):
            raise ClassFlowError(
                "The AI embedding service returned an invalid response",
                "RAG_INVALID_EMBEDDING",
                status.HTTP_502_BAD_GATEWAY,
            )
        return values

    def _get_client(self) -> genai.Client:
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ClassFlowError(
                "Gemini API key is not configured",
                "RAG_NOT_CONFIGURED",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        self._client = genai.Client(api_key=self.api_key)
        return self._client
