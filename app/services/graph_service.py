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

async def graph_answer(question:str,index_id:str)->str:
    result=await graph.ainvoke({
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
                "content": question,
            },
        ],
        "index_id": index_id,
    })
    return result["messages"][-1]["content"]
