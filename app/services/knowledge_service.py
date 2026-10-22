from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

import asyncio
from pypdf import PdfReader

class KnowledgeService:
    def __init__(self):
        self.embedding=OllamaEmbeddings(
            model="qwen3-embedding:4b",
            base_url=settings.OLLAMA_BASE_URL,
            client_kwargs={"trust_env":False},
        )

        self.spliter=RecursiveCharacterTextSplitter(
            chunk_size=100,
            chunk_overlap=20,
            separators=["\n\n", "\n", "。", ""],
        )

        self.vector_store=None

    async def load_file(
            self,
            filepath:Path,
            source_name:str|None=None,
            )->int:
        documents = await asyncio.to_thread(
            self._read_documents,
            filepath,
            source_name,
        )
        chunks=self.spliter.split_documents(documents)

        new_store=InMemoryVectorStore(
            embedding=self.embedding
        )
        await new_store.aadd_documents(chunks)
        self.vector_store = new_store
        return len(chunks)

    async def search(self, query: str, k: int = 2) -> list[Document]:
        if self.vector_store is None:
            raise RuntimeError("请先加载知识文件")

        return await self.vector_store.asimilarity_search(
            query,
            k=k,
        )
    def _read_documents(
            self,
            filepath: Path,
            source_name: str | None,
    )-> list[Document]:
        source=source_name or filepath.name
        suffix=filepath.suffix.lower()

        if suffix==".txt":
            text = filepath.read_text(encoding="utf-8-sig")
            if not text.strip():
                raise ValueError("TXT 文件内容为空")
            return [
                Document(
                    page_content=text,
                    metadata={"source": source},
                )
            ]
        if suffix==".pdf":
            reader=PdfReader(filepath)
            documents=[]

            for page_number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""

                if text.strip():
                    documents.append(
                        Document(
                            page_content=text,
                            metadata={
                                "source": source,
                                "page": page_number,
                            },
                        )
                    )

            if not documents:
                raise ValueError("PDF 未提取到文字，扫描版需要先进行 OCR")
            return documents
        raise ValueError("只支持 TXT 或 PDF")

