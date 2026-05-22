from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader


UPLOAD_DIR = Path("data/uploads")
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class DocumentChunk:
    content: str
    chunk_index: int


class DocumentLoader:
    def __init__(
        self,
        upload_dir: Path = UPLOAD_DIR,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        self.upload_dir = upload_dir
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload_file: UploadFile) -> Path:
        original_name = Path(upload_file.filename or "uploaded.txt").name
        safe_name = self._safe_filename(original_name)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported file type: {suffix}. Supported: {supported}")

        saved_name = f"{int(time.time())}_{uuid4().hex[:8]}_{safe_name}"
        target_path = self.upload_dir / saved_name
        content = await upload_file.read()
        if not content:
            raise ValueError("Uploaded file is empty.")
        target_path.write_bytes(content)
        return target_path

    def load_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            return self._load_pdf(path)
        raise ValueError(f"Unsupported file type: {suffix}")

    def load_chunks(self, path: Path) -> list[DocumentChunk]:
        text = self.load_text(path)
        return self.split_text(text)

    def split_text(self, text: str) -> list[DocumentChunk]:
        normalized = self._normalize_text(text)
        if not normalized:
            return []

        chunks: list[DocumentChunk] = []
        start = 0
        text_length = len(normalized)
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            if end < text_length:
                boundary = normalized.rfind("\n", start, end)
                if boundary > start + int(self.chunk_size * 0.55):
                    end = boundary

            content = normalized[start:end].strip()
            if content:
                chunks.append(DocumentChunk(content=content, chunk_index=len(chunks)))

            if end >= text_length:
                break
            start = max(end - self.chunk_overlap, start + 1)

        return chunks

    def _load_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages)

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _safe_filename(self, filename: str) -> str:
        filename = re.sub(r'[\\/:*?"<>|]+', "_", filename).strip()
        filename = filename.strip(". ")
        return filename or "uploaded.txt"
