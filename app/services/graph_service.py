import asyncio
from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.services.ollama_service import OllamaService
from app.services.indexing_service import IndexingService
from tools.definitions import SEARCH_TOOL, ORDER_SUPPLIER_TOOL,GRAPH_QUERY_TOOL
from langgraph.config import get_stream_writer
import json

from app.services.neo4j_service import Neo4jService

class State(TypedDict):
    messages: list[dict]
    index_id: str
    image: bytes | None

chat=OllamaService()
indexes=IndexingService()
# tools = [{"type": "function", "function": SEARCH_TOOL}]
neo4j_service = Neo4jService()

tools = [
    {"type": "function", "function": SEARCH_TOOL},
    {"type": "function", "function": ORDER_SUPPLIER_TOOL},
    {"type": "function", "function": GRAPH_QUERY_TOOL},
]



# 节点一：请求模型，保留它的回复或工具请求。
async def model_node(state: State) -> dict:
    print("执行：模型节点")
    # message = await chat.generate_with_tools(state["messages"], tools)
    # return {"messages": state["messages"] + [message]}
    writer=get_stream_writer()

    message={
        "role": "assistant",
        "content": "",
        "tool_calls": [],
    }
    async for part in chat.generate_with_tools_stream(
        state["messages"],
        tools,
    ):
        content=part.get("content", "")

        if content:
            message["content"] += content
            writer(content)

        if part.get("tool_calls"):
            message["tool_calls"].extend(part["tool_calls"])

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
    # knowledge=indexes.get_index(state["index_id"])

    # if knowledge is None:
    #     raise ValueError("找不到知识库，请检查 index_id")

    for call in messages[-1]["tool_calls"]:
        function=call["function"]
        name = function["name"]
        arguments = function["arguments"]

        print("执行工具：", name, arguments)

        if name =="search_knowledge":
            knowledge=indexes.get_index(state["index_id"])

            if knowledge is None:
                raise ValueError("找不到知识库，请检查 index_id")
            docs = await knowledge.search(arguments["query"])            
            context = "\n\n".join(
                f"来源：{doc.metadata.get('source')}\n内容：{doc.page_content}"
                f"内容：{doc.page_content}"
                for doc in docs
            )

        elif name== "query_order_supplier":
            rows=await neo4j_service.get_order_supplier(
                arguments["order_id"]
            )
            context=json.dumps(rows,ensure_ascii=False)

        elif  name== "query_graph":
            query = await neo4j_service.generate_cypher(
                arguments["question"]
            )
            query = query.strip()
            print("生成的 Cypher：", query)

            if query=="UNSUPPORTED":
                context = "当前图数据库结构不支持这个问题，请明确说明无法查询。"
            else:
                rows = await neo4j_service.execute_cypher(query)
                context = json.dumps(rows, ensure_ascii=False)

        else:
            raise ValueError(f"不支持的工具：{name}")
        messages.append({
            "role": "tool",
            "tool_name": function["name"],
            "content": context,
        })
    return {"messages": messages}


async def image_node(state: State) -> dict:
    print("执行：图片节点")

    question = state["messages"][-1]["content"]
    answer = await chat.generate_with_image(
        question,
        state["image"],
    )

    writer = get_stream_writer()
    writer(answer)

    return {
        "messages": state["messages"] + [
            {"role": "assistant", "content": answer}
        ]
    }


def route_entry(state: State) -> str:
    if state.get("image"):
        return "image"

    return "model"


builder = StateGraph(State)
builder.add_node("model", model_node)
builder.add_node("tools", tool_node)

# builder.add_edge(START, "model")

builder.add_node("image", image_node)

builder.add_conditional_edges(
    START,
    route_entry,
    {
        "image": "image",
        "model": "model",
    },
)

builder.add_edge("image", END)

builder.add_conditional_edges(
    "model", next_step, {"tools": "tools", "end": END}
)
builder.add_edge("tools", "model")

graph = builder.compile()

# async def graph_answer(question:str,index_id:str)->str:
#     result=await graph.ainvoke({
#         "messages": [
#             {
#                 "role": "system",
#                 "content": (
#                     "你是机器人客服。具体故障问题先检索知识库。"
#                     "拿到资料后，资料足够就直接回答，不要重复检索；"
#                     "资料不足时明确说明。不要添加资料未支持的操作。"
#                 ),
#             },
#             {
#                 "role": "user",
#                 "content": question,
#             },
#         ],
#         "index_id": index_id,
#     })
#     return result["messages"][-1]["content"]

# async def graph_answer(
#     question: str,
#     history: list[dict] | None = None,
# ) -> list[dict]:
def build_messages(
    question: str,
    history: list[dict] | None = None,
) -> list[dict]:
    messages = [
        {
            "role": "system",
            "content": (
                "你是机器人客服。先结合聊天历史判断信息是否足够。"
                "如果用户只说机器人坏了、不能用了等，没有明确故障现象或错误代码，"
                "且历史也未提供这些信息，只追问一个最关键的缺失信息，"
                "例如“具体出现了什么现象，或显示了什么错误代码？”；"
                "此时不调用检索工具，不提供充电、重启等排查步骤。"
                "如果当前问题或历史已提供错误代码或明确现象，直接据此检索，"
                "不要因缺少非必要信息反复追问。"
                "针对信息明确的产品故障、参数和维护问题，必须先调用知识库工具。"
                "只有检索资料明确支持的内容才能作为产品事实回答，不能使用常识猜测。"
                "用户问某个故障代码时，核对资料是否明确包含同一个代码及其说明；"
                "其他代码的资料不能用于解释当前代码。"
                "如果资料未说明，直接回答“当前知识库没有该问题的明确说明，无法确认”，"
                "不要编造原因、数值或处理步骤，也不要为同一问题反复检索。"
                "普通问候直接回答；用户昵称等个人信息根据聊天历史回答。"
                "查询订单包含的商品及其供应商时，必须调用 query_order_supplier。"
                "缺少订单号时先询问；查询无记录时明确说明未查到，不编造订单信息。"
                "查询供应商提供哪些商品、商品关联哪些订单等其他图谱关系时，调用 query_graph。"
                "图查询返回空列表时，说明本次未查到匹配记录，不编造结果。"
                "用户已经给出的供应商名称应完整保留并作为查询条件，包括名称中的“示例”字样；"
                "不要因名称看似示例而要求再次提供。"
            ),
        },
    ]

    # 先放历史，再放当前问题。
    messages.extend(history or [])
    messages.append({
        "role": "user",
        "content": question,
    })
    # result = await graph.ainvoke({
    #     "messages": messages,
    #     "index_id": index_id,
    # })

    # return result["messages"][-1]["content"]
    return messages


async def graph_answer(
    question: str,
    index_id: str,
    history: list[dict] | None = None,
    image: bytes | None = None,
) -> str:
    result = await graph.ainvoke({
        "messages": build_messages(question, history),
        "index_id": index_id,
        "image": image,
    })
    return result["messages"][-1]["content"]


async def graph_answer_stream(
    question: str,
    index_id: str,
    history: list[dict] | None = None,
    image: bytes | None = None,
):
    async for text in graph.astream(
        {
            "messages": build_messages(question, history),
            "index_id": index_id,
            "image": image,
        },
        stream_mode="custom",
    ):
        yield text