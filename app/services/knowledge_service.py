from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

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
        text=filepath.read_text(encoding="utf-8")

        if not text.strip():
            raise ValueError("知识文件内容为空")
        document=Document(
            page_content=text,
            # metadata={"source": filepath.name},
            metadata={"source": source_name or filepath.name}
        )
        chunks=self.spliter.split_documents([document])

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
