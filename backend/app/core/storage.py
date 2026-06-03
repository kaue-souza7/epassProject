from abc import ABC, abstractmethod
from pathlib import Path


class FileStorage(ABC):
    @abstractmethod
    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        ...

    @abstractmethod
    async def download(self, path: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, path: str) -> None:
        ...

    @abstractmethod
    def get_url(self, path: str) -> str:
        ...


class LocalStorage(FileStorage):
    def __init__(self, base_path: Path = Path("./storage")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)
        return str(full_path)

    async def download(self, path: str) -> bytes:
        return (self.base_path / path).read_bytes()

    async def delete(self, path: str) -> None:
        (self.base_path / path).unlink(missing_ok=True)

    def get_url(self, path: str) -> str:
        return f"/storage/{path}"
