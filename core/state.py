import hashlib
import json
from pathlib import Path
from typing import Any

from config import Settings


class IndexState:
    """
    Persists indexing state so unchanged files are not re-indexed.

    The source_id includes:
    - file content hash
    - index version
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.index_state_path
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"files": {}}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"files": {}}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2),
            encoding="utf-8",
        )

    def file_hash(self, path: Path) -> str:
        hasher = hashlib.sha256()

        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(block)

        return hasher.hexdigest()

    def source_id_for(self, path: Path) -> str:
        content_hash = self.file_hash(path)
        raw = f"{content_hash}:{self.settings.index_version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_current(self, path: Path, source_id: str) -> bool:
        key = str(path.resolve())
        record = self.data["files"].get(key)
        return bool(record and record.get("source_id") == source_id)

    def update(self, path: Path, source_id: str, chunks_added: int) -> None:
        key = str(path.resolve())

        self.data["files"][key] = {
            "file_name": path.name,
            "source_path": key,
            "source_id": source_id,
            "index_version": self.settings.index_version,
            "chunks_added": chunks_added,
        }

        self.save()

    def list_files(self) -> list[dict[str, Any]]:
        return list(self.data.get("files", {}).values())