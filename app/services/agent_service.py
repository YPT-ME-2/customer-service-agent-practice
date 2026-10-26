from app.services.ollama_service import OllamaService
from app.services.indexing_service import IndexingService
from tools.definitions import SEARCH_TOOL


class AgentService:
    def __init__(self, indexing_service: IndexingService):
        self.indexing_service = indexing_service
        self.chat_service = OllamaService()

        self.tools = [
            {
                "type": "function",
                "function": SEARCH_TOOL,
            }
        ]

    async def answer(self, question: str, index_id: str) -> str:
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
                "content": question,
            },
        ]

        # 第一次调用：让模型决定是否需要工具。
        message = await self.chat_service.generate_with_tools(
            messages,
            self.tools,
        )

        tool_calls = message.get("tool_calls", [])

        # 不需要工具时，直接返回模型的回答。
        if not tool_calls:
            return message.get("content", "")

        messages.append(message)

        for tool_call in tool_calls:
            function = tool_call["function"]
            name = function["name"]
            arguments = function["arguments"]

            if name != "search_knowledge":
                raise ValueError(f"不支持的工具：{name}")

            knowledge = self.indexing_service.get_index(index_id)

            if knowledge is None:
                raise ValueError("找不到这个知识库，请检查 index_id")

            docs = await knowledge.search(arguments["query"])

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

        # 第二次调用：让模型根据工具结果回答。
        return await self.chat_service.generate(messages)