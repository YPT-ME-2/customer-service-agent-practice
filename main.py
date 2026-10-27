from typing import Literal

from fastapi import FastAPI, HTTPException,Path,UploadFile,File

from pydantic import BaseModel, Field

# from app.services.ollama_service import OllamaService
from app.services.llm_factory import LLMFactory

from app.core.config import settings
from fastapi.responses import StreamingResponse
from app.core.logger import get_logger
from app.services.conversation_service import ConversationService

from contextlib import asynccontextmanager
from app.core.database import Base, engine
from app.models.conversation import Conversation

from app.core.config import ROOT_DIR
# from app.services.knowledge_service import KnowledgeService
from app.services.indexing_service import IndexingService
# from app.services.agent_service import AgentService
from app.services.graph_service import graph_answer
from app.services.rag_service import RagService
from uuid import uuid4
import asyncio

logger=get_logger("api")

@asynccontextmanager
async def lifespan(app:FastAPI):
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        logger.info("数据库表已准备好")

        yield
    finally:
        # 关闭时：释放数据库连接资源
        await engine.dispose()

# app=FastAPI(title="客服 Agent 练习")
app=FastAPI(
    title="客服 Agent 练习",
    lifespan=lifespan,
)
# chat_service=OllamaService()
chat_service=LLMFactory.create_chat_service()

conversation_service = ConversationService()

# knowledge_service = KnowledgeService()
# rag_service = RagService(knowledge_service)
indexing_service=IndexingService()

# agent_service=AgentService(indexing_service)

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

    messages=await conversation_service.get_history(
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

    await conversation_service.save_turn(
        request.conversation_id,
        question,
        answer,
    )
    return {
        "conversation_id": request.conversation_id,
        "answer": answer,
    }

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id:str=Path(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
):
    messages=await conversation_service.get_history(
        conversation_id,
    )
    return {
        "conversation_id": conversation_id,
        "messages": messages,
    }

@app.delete("/api/conversations/{conversation_id}/messages")
async def clear_conversation_messages(
    conversation_id:str=Path(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
):
    await conversation_service.clear_history(conversation_id)
    return {
        "conversation_id": conversation_id,
        "message": "该会话的消息已清空",
    }

# @app.get("/api/conversations")
# async def list_conversations():
#     conversation_ids=await conversation_service.list_conversations()
#     return {
#         "conversation_ids":conversation_ids,
#     }

@app.get("/api/conversations")
async def list_conversations():
    conversations = await conversation_service.list_conversations()

    return {"conversations": conversations}

class CreateConversationRequest(BaseModel):
    title:str=Field(default="新会话", min_length=1, max_length=100)

@app.post("/api/conversations")
async def create_conversation(request:CreateConversationRequest):
    title=request.title.strip()
    if not title:
        raise HTTPException(
            status_code=422,
            detail="标题不能只包含空白",
        )
    return await conversation_service.create_conversation(title)


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)

@app.patch("/api/conversations/{conversation_id}/title")
async def rename_conversation(
    request:RenameConversationRequest,
    conversation_id:str=Path(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
):
    title=request.title.strip()
    if not title:
        raise HTTPException(
            status_code=422,
            detail="标题不能只包含空白",
        )
    updated=await conversation_service.rename_conversation(
        conversation_id,
        title,
    )
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="会话不存在",
        )
    return {
        "id": conversation_id,
        "title": title,
    }

# @app.post("/api/knowledge/load")
# async def load_knowledge():
#     filepath=ROOT_DIR/"data"/"机器人测试说明.txt"
#     try:
#         count=await knowledge_service.load_file(filepath)
#     except Exception:
#         logger.exception("知识文件加载失败")
#         raise HTTPException(
#             status_code=500,
#             detail="知识文件加载失败，请查看服务日志",
#         )
#     return {
#         "message": "知识文件加载完成",
#         "source": filepath.name,
#         "chunk_count": count,
#     }

@app.post("/api/knowledge/load")
async def load_knowledge():
    filepath=ROOT_DIR / "data" / "机器人测试说明.txt"
    try:
        index_info=await indexing_service.create_index(filepath)
    except Exception:
        logger.exception("知识文件加载失败")
        raise HTTPException(
            status_code=500,
            detail="知识文件加载失败，请查看服务日志",
        )

    return index_info
#{
#   "index_id": "生成的编号",
#   "source": "机器人测试说明.txt",
#   "chunk_count": 2
# }

class RagChatRequest(BaseModel):
    index_id:str=Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)


@app.post("/api/rag/chat")
async def rag_chat(request: RagChatRequest):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="问题不能只包含空白",
        )
    knowledge=indexing_service.get_index(request.index_id)
    
    if knowledge is None:
        raise HTTPException(
            status_code=503,
            detail="知识库尚未准备好，请先加载资料",
        )
    rag=RagService(knowledge)
    try:
        return await rag.answer(question)
    except Exception:
        logger.exception("RAG 问答失败")
        raise HTTPException(
            status_code=502,
            detail="RAG 问答失败，请查看服务日志",
        )

class AgentChatRequest(BaseModel):
    index_id:str=Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)

@app.post("/api/agent/chat")
async def agent_chat(request: AgentChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=422,
            detail="问题不能只包含空白",
        )
    try:
        # answer=await agent_service.answer(
        #     question=question,
        #     index_id=request.index_id,
        # )
        answer=await graph_answer(
            question=question,
            index_id=request.index_id,
        )

    except Exception:
        logger.exception("Agent 问答失败")
        raise HTTPException(
            status_code=502,
            detail="Agent 问答失败，请查看服务日志",
        )
    return {"answer": answer}

@app.post("/api/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(..., json_schema_extra={"format": "binary"}),
):
    filename = file.filename or ""
    # 最多读取 2MB 加一个字节，用来判断是否超限
    lower_name=filename.lower()
    if lower_name.endswith(".txt"):
        suffidx=".txt"
    elif lower_name.endswith(".pdf"):
        suffidx=".pdf"
    else:
        await file.close()
        raise HTTPException(
            status_code=422,
            detail="当前只支持 TXT 和 PDF",
        )

    max_size = 10 * 1024 * 1024
    try:
        content=await file.read(max_size+1)
    finally:
        await file.close()

    # if not filename.lower().endswith(".txt"):
    #     raise HTTPException(
    #         status_code=422,
    #         detail="当前只支持 TXT 文件",
    #     )
    if len(content)>max_size:
        raise HTTPException(
            status_code=413,
            detail="文件不能超过 10MB",
        )
    if not content:
        raise HTTPException(
            status_code=422,
            detail="文件不能为空",
        )

    # try:
    #     text=content.decode("utf-8-sig")
    # except UnicodeDecodeError:
    #     raise HTTPException(
    #         status_code=422,
    #         detail="请将文件保存为 UTF-8 编码后上传",
    #     )

    # if not text.strip():
    #     raise HTTPException(
    #         status_code=422,
    #         detail="文件内容不能为空",
    #     )

    upload_dir=ROOT_DIR/"uploads"
    upload_dir.mkdir(exist_ok=True)
    # 使用服务器生成的文件名，避免同名覆盖
    # filepath=upload_dir / f"{uuid4().hex}.txt"
    filepath=upload_dir/f"{uuid4().hex}{suffidx}"

    try:
        # filepath.write_text(text,encoding="utf-8")
        await asyncio.to_thread(filepath.write_bytes, content)
        # count = await knowledge_service.load_file(
        #     filepath,
        #     source_name=filename,
        # )
        index_info=await indexing_service.create_index(
            filepath,
            source_name=filename,
        )

    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except Exception:
        logger.exception("上传资料建库失败")
        raise HTTPException(
            status_code=500,
            detail="资料处理失败，请查看服务日志",
        )
    # return {
    #     "message": "上传并建立知识库成功",
    #     "source": filename,
    #     "chunk_count": count,
    # }
    return index_info
