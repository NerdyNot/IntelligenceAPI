from typing import AsyncIterator, Iterator
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document

class CustomDocumentLoader(BaseLoader):
    """텍스트 파일을 한 줄씩 읽어들이는 커스텀 로더"""

    def __init__(self, file_path: str) -> None:
        """파일 경로를 초기화합니다.

        Args:
            file_path: 로드할 파일의 경로.
        """
        self.file_path = file_path

    def lazy_load(self) -> Iterator[Document]:
        """파일을 한 줄씩 읽어들이는 제너레이터"""
        with open(self.file_path, encoding="utf-8") as f:
            line_number = 0
            for line in f:
                yield Document(
                    page_content=line.strip(),
                    metadata={"line_number": line_number, "source": self.file_path},
                )
                line_number += 1

    async def alazy_load(self) -> AsyncIterator[Document]:
        """파일을 비동기로 한 줄씩 읽어들이는 제너레이터"""
        import aiofiles

        async with aiofiles.open(self.file_path, encoding="utf-8") as f:
            line_number = 0
            async for line in f:
                yield Document(
                    page_content=line.strip(),
                    metadata={"line_number": line_number, "source": self.file_path},
                )
                line_number += 1
