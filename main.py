from typing import Literal

from fastapi import FastAPI, HTTPException

from pydantic import BaseModel, Field

# from app.services.ollama_service import OllamaService
from app.services.llm_factory import LLMFactory

from app.core.config import settings
from fastapi.responses import StreamingResponse
from app.core.logger import get_logger
from app.services.conversation_service import ConversationService

logger=get_logger("api")

app=FastAPI(title="客服 Agent 练习")
# chat_service=OllamaService()
chat_service=LLMFactory.create_chat_service()

conversation_service = ConversationService()

logger.info(
    "聊天服务已创建：%s",
    type(chat_service).__name__,
)
class ChatMessage(BaseModel):
    role:Literal["system","user","assistant"]
    content:str=Field(min_length=1)

class ChatRequest(BaseModel):
    messages:list[ChatMessage]=Field(min_length=1)

@app.get("/health")
def health_check():
    return {"status":"ok"}

@app.post("/api/chat")
async def chat(request:ChatRequest):
    messages=[
        message.model_dump()#model_dump() 是 Pydantic 中的方法，用来将一个 BaseModel 对象转换成 Python 字典（dict）
        for message in request.messages
    ]
    logger.info("收到聊天请求，消息数：%s", len(messages))
    try:
        answer=await chat_service.generate(messages)
    except Exception as e:
        # print(f"调用模型失败：{e}")
        logger.exception("普通聊天调用失败")
        raise HTTPException(
            status_code=502,
            # detail="模型服务调用失败，请检查 Ollama 状态",
            detail="模型服务调用失败，请检查服务状态",
        )
    logger.info("聊天完成，回答字符数：%s", len(answer))
    return {"answer":answer}

@app.post("/api/chat/stream")
async def chat_stream(request:ChatRequest):
    messages=[
        message.model_dump()
        for message in request.messages
    ]
    return StreamingResponse(
        chat_service.generate_stream(messages),
        media_type="text/plain; charset=utf-8",
    )


class ConversationChatRequest(BaseModel):
    conversation_id:str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    question:str=Field(min_length=1, max_length=2000)

@app.post("/api/conversations/chat")
async def conversation_chat(request:ConversationChatRequest):
    question=request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="问题不能只包含空白"
        )

    messages=conversation_service.get_history(
        request.conversation_id
    )

    messages.append({
        "role": "user",
        "content": question,
    })

    logger.info(
        "会话聊天：%s，发送消息数：%s",
        request.conversation_id,
        len(messages),
    )

    try:
        answer=await chat_service.generate(messages)
    except Exception:
        logger.exception("会话聊天调用失败")
        raise HTTPException(
            status_code=502,
            detail="模型服务调用失败",
        )

    if not answer.strip():
        raise HTTPException(
            status_code=502,
            detail="模型未返回有效回答",
        )

    conversation_service.save_turn(
        request.conversation_id,
        question,
        answer,
    )
    return {
        "conversation_id": request.conversation_id,
        "answer": answer,
    }