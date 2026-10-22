import asyncio

from app.core.config import ROOT_DIR
from app.services.knowledge_service import KnowledgeService


async def main():
    service = KnowledgeService()

    count = await service.load_file(
        ROOT_DIR / "data" / "机器人测试说明.txt"
    )
    print("已加载片段数：", count)

    results = await service.search(
        "ZS-T01出现E731错误怎么处理？"
    )

    for doc in results:
        print("\n来源：", doc.metadata["source"])
        print(doc.page_content)


if __name__ == "__main__":
    asyncio.run(main())