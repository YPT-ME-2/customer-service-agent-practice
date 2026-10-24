from pathlib import Path
from uuid import uuid4

from app.services.knowledge_service import KnowledgeService

class IndexingService:
    def __init__(self):
        self.indexes:dict[str, KnowledgeService] = {}

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
        self.indexes[index_id]=knowledge

        return {
            "index_id": index_id,
            "source": source_name or filepath.name,
            "chunk_count": count,
        }

    def get_index(self,index_id: str)->KnowledgeService| None:
        return self.indexes.get(index_id)