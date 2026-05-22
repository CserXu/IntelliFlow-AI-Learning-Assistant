from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.core.llm import OpenAIClient
from app.models.rag import RagSource
from app.services.document_loader import DocumentLoader
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import RetrievedChunk, VectorStore


NO_RELEVANT_INFO = "\u77e5\u8bc6\u5e93\u4e2d\u6ca1\u6709\u627e\u5230\u76f8\u5173\u4fe1\u606f"
MAX_CONTEXT_CHARS = 12000


class RagService:
    def __init__(
        self,
        document_loader: DocumentLoader | None = None,
        embedding_service: EmbeddingService | None = None,
        vector_store: VectorStore | None = None,
        llm_client: OpenAIClient | None = None,
    ) -> None:
        self.document_loader = document_loader or DocumentLoader()
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStore()
        self.llm_client = llm_client or OpenAIClient()
        self.max_distance = float(os.getenv("RAG_MAX_DISTANCE", "0.75"))

    def ingest_file(self, path: Path, original_filename: str | None = None) -> int:
        chunks = self.document_loader.load_chunks(path)
        if not chunks:
            raise ValueError("No readable text was found in the uploaded file.")

        file_hash = self._file_hash(path)
        filename = original_filename or self._display_filename(path)
        documents = [chunk.content for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(documents)
        ids = [f"{file_hash[:16]}-{chunk.chunk_index}" for chunk in chunks]
        metadatas = [
            {
                "filename": filename,
                "chunk_index": chunk.chunk_index,
                "source_path": str(path).replace("\\", "/"),
                "file_hash": file_hash,
            }
            for chunk in chunks
        ]

        return self.vector_store.add_chunks(ids, documents, embeddings, metadatas)

    def answer_question(self, question: str, top_k: int = 5) -> tuple[str, list[RagSource]]:
        question = question.strip()
        if not question:
            raise ValueError("Question cannot be empty.")

        safe_top_k = max(1, min(top_k, 20))
        query_embedding = self.embedding_service.embed_text(question)
        retrieved = self.vector_store.query(query_embedding, top_k=safe_top_k)
        relevant = self._filter_relevant(retrieved)

        if not relevant:
            return NO_RELEVANT_INFO, []

        context = self._build_context(relevant)
        answer = self._generate_answer(question, context)
        if answer == NO_RELEVANT_INFO:
            return NO_RELEVANT_INFO, []

        sources = [
            RagSource(
                filename=str(chunk.metadata.get("filename", "")),
                chunk_id=chunk.chunk_id,
                content_preview=self._preview(chunk.content),
            )
            for chunk in relevant
        ]
        return answer, sources

    def revise_plan_with_knowledge(
        self,
        original_plan: str,
        instruction: str,
        top_k: int = 5,
    ) -> tuple[str, list[RagSource]]:
        original_plan = original_plan.strip()
        instruction = instruction.strip()
        if not original_plan:
            raise ValueError("Original plan cannot be empty.")
        if not instruction:
            raise ValueError("Instruction cannot be empty.")

        safe_top_k = max(1, min(top_k, 20))
        query_embedding = self.embedding_service.embed_text(instruction)
        retrieved = self.vector_store.query(query_embedding, top_k=safe_top_k)
        relevant = self._filter_relevant(retrieved)

        if not relevant:
            return original_plan, []

        context = self._build_context(relevant)
        revised_plan = self._generate_revised_plan(original_plan, instruction, context)
        sources = [
            RagSource(
                filename=str(chunk.metadata.get("filename", "")),
                chunk_id=chunk.chunk_id,
                content_preview=self._preview(chunk.content),
            )
            for chunk in relevant
        ]
        return revised_plan, sources

    def _filter_relevant(self, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        relevant = [
            chunk
            for chunk in chunks
            if chunk.content.strip()
            and (chunk.distance is None or chunk.distance <= self.max_distance)
        ]
        return relevant

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        parts: list[str] = []
        total = 0
        for chunk in chunks:
            filename = chunk.metadata.get("filename", "")
            chunk_index = chunk.metadata.get("chunk_index", "")
            header = f"[source: {filename} | chunk: {chunk_index} | id: {chunk.chunk_id}]"
            block = f"{header}\n{chunk.content.strip()}"
            if total + len(block) > MAX_CONTEXT_CHARS:
                break
            parts.append(block)
            total += len(block)
        return "\n\n---\n\n".join(parts)

    def _generate_answer(self, question: str, context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are IntelliFlow's retrieval augmented QA assistant. "
                    "Answer only from the retrieved knowledge base context. "
                    "If the context does not contain enough information, answer exactly: "
                    f"{NO_RELEVANT_INFO}. "
                    "Do not invent facts. Reply in the user's language."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Retrieved context:\n{context}\n\n"
                    "Use only the retrieved context above. Include concise source references "
                    "by filename and chunk number when useful."
                ),
            },
        ]
        answer = self.llm_client.create_chat_completion(messages, temperature=0.2)
        answer = answer.strip()
        if not answer or NO_RELEVANT_INFO in answer:
            return NO_RELEVANT_INFO
        return answer

    def _generate_revised_plan(self, original_plan: str, instruction: str, context: str) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are IntelliFlow's learning plan reviser. "
                    "Revise the original Markdown learning plan using only the supplied knowledge base context "
                    "and the user's instruction. Preserve useful existing structure, improve it where the context "
                    "supports changes, and do not invent facts that are not in the original plan or retrieved context. "
                    "Return only the revised Markdown plan."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Original Markdown learning plan:\n{original_plan}\n\n"
                    f"User instruction:\n{instruction}\n\n"
                    f"Retrieved knowledge base context:\n{context}\n\n"
                    "Please produce an updated Markdown learning plan. When adding knowledge-base details, "
                    "keep them grounded in the retrieved context."
                ),
            },
        ]
        revised_plan = self.llm_client.create_chat_completion_strict(messages, temperature=0.25).strip()
        if self._looks_like_prompt_leak(revised_plan):
            raise RuntimeError("OpenAI chat completion returned prompt text instead of a revised plan.")
        return revised_plan

    def _looks_like_prompt_leak(self, text: str) -> bool:
        prompt_markers = (
            "You are IntelliFlow's learning plan reviser",
            "Original Markdown learning plan:",
            "Retrieved knowledge base context:",
            "[妯℃嫙杈撳嚭]",
            "[模拟输出]",
        )
        return any(marker in text for marker in prompt_markers)

    def _file_hash(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _display_filename(self, path: Path) -> str:
        parts = path.name.split("_", 2)
        if len(parts) == 3 and parts[0].isdigit():
            return parts[2]
        return path.name

    def _preview(self, content: str, limit: int = 220) -> str:
        preview = " ".join(content.split())
        if len(preview) <= limit:
            return preview
        return preview[:limit].rstrip() + "..."
