import asyncio

from app.core.config import ROOT_DIR
from app.services.knowledge_service import KnowledgeService
from app.services.rag_service import RagService


async def main():
    knowledge = KnowledgeService()

    await knowledge.load_file(
        ROOT_DIR / "data" / "机器人测试说明.txt"
    )

    rag = RagService(knowledge)

    result = await rag.answer(
        "ZS-T01出现E731错误，应该怎么处理？"
    )

    print("【回答】")
    print(result["answer"])

    print("\n【检索到的参考片段】")
    for reference in result["references"]:
        print(
            f"\n资料{reference['number']}："
            f"{reference['source']}"
        )
        print(reference["content"])


if __name__ == "__main__":
    asyncio.run(main())