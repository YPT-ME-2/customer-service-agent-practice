from pathlib import Path
from uuid import uuid4

from app.core.config import ROOT_DIR
from app.services.knowledge_service import KnowledgeService

class IndexingService:
    def __init__(self):
        self.indexes:dict[str, KnowledgeService] = {}
        self.index_dir = ROOT_DIR / "indexes"

    async def create_index(
            self,
            filepath:Path,
            source_name: str | None = None,
    )->dict:
        knowledge=KnowledgeService()

        count=await knowledge.load_file(
            filepath,
            source_name=source_name,
        )

        index_id=uuid4().hex
        knowledge.save_index(self.index_dir / index_id)
        self.indexes[index_id]=knowledge

        return {
            "index_id": index_id,
            "source": source_name or filepath.name,
            "chunk_count": count,
        }

    def get_index(self,index_id: str)->KnowledgeService| None:
        # index_id 来自接口，只允许本项目生成的 UUID 格式，避免越界读文件。
        if len(index_id) != 32 or any(c not in "0123456789abcdef" for c in index_id):
            return None
        if index_id not in self.indexes:
            folder = self.index_dir / index_id
            if not folder.is_dir():
                return None
            knowledge = KnowledgeService()
            knowledge.load_index(folder)
            self.indexes[index_id] = knowledge
        return self.indexes.get(index_id)
