# # from typing import TypedDict

# # from langgraph.graph import StateGraph, START, END


# # class State(TypedDict):
# #     question: str
# #     answer: str


# # def fault_node(state: State) -> dict:
# #     print("进入故障节点")
# #     return {"answer": "这个问题需要查询机器人故障资料。"}


# # def chat_node(state: State) -> dict:
# #     print("进入聊天节点")
# #     return {"answer": "您好，我是机器人客服。"}


# # def route_question(state: State) -> str:
# #     if "E731" in state["question"]:
# #         return "fault"

# #     return "chat"


# # builder = StateGraph(State)

# # builder.add_node("fault", fault_node)
# # builder.add_node("chat", chat_node)

# # builder.add_conditional_edges(
# #     START,
# #     route_question,
# #     {
# #         "fault": "fault",
# #         "chat": "chat",
# #     },
# # )

# # builder.add_edge("fault", END)
# # builder.add_edge("chat", END)

# # graph = builder.compile()


# # if __name__ == "__main__":
# #     result = graph.invoke({
# #         "question": "ZS-T01出现E731错误怎么处理？",
# #         "answer": "",
# #     })

# #     print("最终状态：", result)


# import asyncio
# from typing import TypedDict

# from langgraph.graph import StateGraph, START, END

# from app.services.ollama_service import OllamaService
# from app.services.indexing_service import IndexingService
# from tools.definitions import SEARCH_TOOL

# # 一、状态：节点之间传递的数据
# class State(TypedDict):
#     messages: list[dict]  # 完整对话，包含工具请求和工具结果
#     index_id: str        # 要使用的知识库 ID
#     answer: str          # 最终回答


# chat_service = OllamaService()
# indexing_service = IndexingService()

# tools = [
#     {
#         "type": "function",
#         "function": SEARCH_TOOL,
#     }
# ]

# # 二、模型节点：让模型回答或提出工具请求
# async def model_node(state: State) -> dict:
#     print("进入模型节点")

#     message = await chat_service.generate_with_tools(
#         state["messages"],
#         tools,
#     )

#     return {
#         "messages": state["messages"] + [message],
#         "answer": message.get("content", ""),
#     }
# # 三、路由：根据模型是否请求工具，选择下一步
# def route_after_model(state: State) -> str:
#     message=state["messages"][-1]

#     if message.get("tool_calls"):
#         return "tools"
#     return "end"

# # 四、工具节点：执行知识库检索
# async def tool_node(state:State)->dict:
#     print("进入知识检索节点")
#     messages=state["messages"].copy()
#     tool_calls=messages[-1]["tool_calls"]

#     knowledge=indexing_service.get_index(state["index_id"])

#     if knowledge is None:
#         raise ValueError("找不到知识库，请检查 index_id")
#     for tool_call in tool_calls:
#         function=tool_call["function"]
#         name = function["name"]

#         if name!="search_knowledge":
#             raise ValueError(f"不支持的工具：{name}")
#         query = function["arguments"]["query"]
#         docs = await knowledge.search(query)

#         context = "\n\n".join(
#             f"来源：{doc.metadata.get('source')}\n"
#             f"内容：{doc.page_content}"
#             for doc in docs
#         )

#         messages.append({
#             "role": "tool",
#             "tool_name": name,
#             "content": context,
#         })
#     return {"messages": messages}

# async def answer_node(state:State)->dict:
#     print("进入最终回答节点")
#     answer=await chat_service.generate(state["messages"])
#     return {"answer": answer}

# # 六、建图：登记节点，连接执行路线
# builder = StateGraph(State)
# builder.add_node("model",model_node)
# builder.add_node("tools",tool_node)
# builder.add_node("answer",answer_node)

# # 开始后先执行模型节点
# builder.add_edge(START, "model")

# # 模型节点之后，根据工具请求选择路线
# builder.add_conditional_edges(
#     "model",
#     route_after_model,
#     {
#         "tools": "tools",
#         "end": END,
#     }
# )

# # 检索后生成回答，回答后结束
# builder.add_edge("tools", "answer")
# builder.add_edge("answer", END)

# graph=builder.compile()

# # 七、入口：提供初始状态，执行整个图
# async def main():
#     result = await graph.ainvoke({
#         "messages": [
#             {
#                 "role": "system",
#                 "content": (
#                     "你是机器人客服。涉及机器人具体故障和维护信息时，"
#                     "请先使用知识库检索工具。"
#                     "回答中的故障原因、操作步骤和服务时间必须有检索资料支持。"
#                     "不要自行添加重启、复位、硬件故障等资料未说明的内容。"
#                     "资料不足时明确说明，服务时间按原文表述。"
#                 ),
#             },
#             {
#                 "role": "user",
#                 "content": "ZS-T01出现E731错误怎么处理？",
#             },
#         ],
#         "index_id": "f1dedcdfe013418bbb3f8369edff44e5",
#         "answer": "",
#     })
#     print("最终回答：", result["answer"])

# if __name__ == "__main__":
#     asyncio.run(main())

# import asyncio
# from typing import TypedDict

# from langgraph.graph import StateGraph, START, END

# from app.services.agent_service import AgentService
# from app.services.indexing_service import IndexingService


# class State(TypedDict):
#     question: str
#     index_id: str
#     answer: str


# agent = AgentService(IndexingService())


# # 复用已经跑通的 Agent，不再复制内部代码。
# async def agent_node(state: State) -> dict:
#     answer = await agent.answer(
#         question=state["question"],
#         index_id=state["index_id"],
#     )
#     return {"answer": answer}


# builder = StateGraph(State)
# builder.add_node("agent", agent_node)
# builder.add_edge(START, "agent")
# builder.add_edge("agent", END)

# graph = builder.compile()


# async def main():
#     result = await graph.ainvoke({
#         "question": "ZS-T01出现E731错误怎么处理？",
#         "index_id": "f1dedcdfe013418bbb3f8369edff44e5",
#         "answer": "",
#     })
#     print(result["answer"])


# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.ollama_service import OllamaService
from app.services.indexing_service import IndexingService
from tools.definitions import SEARCH_TOOL


class State(TypedDict):
    messages: list[dict]
    index_id: str

chat=OllamaService()
indexes=IndexingService()
tools = [{"type": "function", "function": SEARCH_TOOL}]

# 节点一：请求模型，保留它的回复或工具请求。
async def model_node(state: State) -> dict:
    print("执行：模型节点")
    message = await chat.generate_with_tools(state["messages"], tools)
    return {"messages": state["messages"] + [message]}

# 路由：模型请求工具就继续，否则结束。
def next_step(state: State) -> str:
    if state["messages"][-1].get("tool_calls"):
        return "tools"
    return "end"

# 节点二：执行检索，把工具结果加入对话。
async def tool_node(state: State) -> dict:
    print("执行：检索节点")
    messages = state["messages"].copy()
    knowledge=indexes.get_index(state["index_id"])

    if knowledge is None:
        raise ValueError("找不到知识库，请检查 index_id")

    for call in messages[-1]["tool_calls"]:
        function=call["function"]
        if function["name"] != "search_knowledge":
            raise ValueError("不支持的工具")

        docs = await knowledge.search(function["arguments"]["query"])
        context = "\n\n".join(
            f"来源：{doc.metadata.get('source')}\n内容：{doc.page_content}"
            for doc in docs
        )
        messages.append({
            "role": "tool",
            "tool_name": function["name"],
            "content": context,
        })
    return {"messages": messages}

builder = StateGraph(State)
builder.add_node("model", model_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "model")
builder.add_conditional_edges(
    "model", next_step, {"tools": "tools", "end": END}
)
builder.add_edge("tools", "model")

graph = builder.compile()

async def main():
    result = await graph.ainvoke({
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是机器人客服。具体故障问题先检索知识库。"
                    "拿到资料后，资料足够就直接回答，不要重复检索；"
                    "资料不足时明确说明。不要添加资料未支持的操作。"
                ),
            },
            {
                "role": "user",
                "content": "ZS-T01出现E731错误怎么处理？",
            },
        ],
        "index_id": "f1dedcdfe013418bbb3f8369edff44e5",
    })

    print("最终回答：", result["messages"][-1]["content"])

if __name__ == "__main__":
    asyncio.run(main())