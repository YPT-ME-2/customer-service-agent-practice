import asyncio
import aiohttp
from app.services.ollama_service import OllamaService
from app.core.config import settings
from tools.definitions import SEARCH_TOOL
from app.services.indexing_service import IndexingService
async def main():
    tools = [
        {
            "type": "function",
            "function": SEARCH_TOOL,
        }
    ]
    messages = [
        {
            "role": "system",
            "content": (
                "你是机器人客服。涉及机器人具体故障和维护信息时，"
                "请先使用知识库检索工具。"
                "回答中的故障原因、操作步骤和服务时间必须有检索资料支持。"
                "不要自行添加重启、复位、硬件故障等资料未说明的内容。"
                "资料不足时明确说明，服务时间按原文表述。"
            ),
        },
        {
            "role": "user",
            "content": "ZS-T01出现E731错误怎么处理？",
        },
    ]

    # async with aiohttp.ClientSession(
    #     timeout=aiohttp.ClientTimeout(total=300),
    #     trust_env=False,
    # ) as session:
    #     async with session.post(
    #         f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat",
    #         json={
    #             "model": settings.OLLAMA_CHAT_MODEL,
    #             # "messages": [
    #             #     {
    #             #         "role": "system",
    #             #         "content": (
    #             #             "你是机器人客服。涉及机器人具体故障和维护信息时，"
    #             #             "请先使用知识库检索工具，不要猜测。"
    #             #         ),
    #             #     },
    #             #     {
    #             #         "role": "user",
    #             #         "content": "ZS-T01出现E731错误怎么处理？",
    #             #     },
    #             # ],
    #             "messages":messages,
    #             "tools": tools,
    #             "stream": False,
    #             "think": False,
    #         },
    #     ) as response:
    #         response.raise_for_status()
    #         result=await response.json()
    chat_service = OllamaService()

    message = await chat_service.generate_with_tools(
        messages,
        tools,
    )

    print("回答文字：", message.get("content"))
    print("工具调用：", message.get("tool_calls"))

    tool_calls = message.get("tool_calls", [])
    messages.append(message)

    # print("回答文字：", result["message"].get("content"))
    # print("工具调用：", result["message"].get("tool_calls"))
    # tool_calls = result["message"].get("tool_calls", [])
    # messages.append(result["message"])
    for tool_call in tool_calls:
        function = tool_call["function"]
        name = function["name"]
        arguments = function["arguments"]

        print("准备执行的工具：", name)
        print("工具参数：", arguments)

        if name == "search_knowledge":
            query = arguments["query"]

            indexing_service = IndexingService()

            # 使用之前已保存到硬盘的知识库。
            knowledge = indexing_service.get_index(
                "f1dedcdfe013418bbb3f8369edff44e5"
            )

            if knowledge is None:
                raise RuntimeError("找不到这个索引，请换成已保存的 index_id")

            docs = await knowledge.search(query)

            for doc in docs:
                print("来源：", doc.metadata.get("source"))
                print("内容：", doc.page_content)
                print()
            context = "\n\n".join(
                f"来源：{doc.metadata.get('source')}\n"
                f"内容：{doc.page_content}"
                for doc in docs
            )

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": context,
            })

    # if tool_calls:
    #     chat_service = OllamaService()
    #     answer = await chat_service.generate(messages)
    #     print("最终回答：", answer)
    if tool_calls:
        answer = await chat_service.generate(messages)
        print("最终回答：", answer)

if __name__ == "__main__":
    asyncio.run(main())
