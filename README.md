# 机器人知识库客服 Agent

以机器人说明资料为测试场景，实现支持知识检索、工具调用和多轮对话的客服后端。

## 功能

- 普通聊天与流式输出。
- SQLite 保存会话标题和聊天历史。
- 上传 TXT、可提取文字的 PDF，解析并切分资料。
- 使用 Ollama 生成向量，通过 FAISS 检索相关片段。
- 按 index_id 管理独立知识库，索引保存到磁盘。
- RAG 接口返回回答、参考片段和 PDF 页码。
- LangGraph Agent 根据模型工具请求执行检索，支持多轮对话。

## 技术栈

Python、FastAPI、aiohttp、SQLAlchemy、SQLite、
Ollama、LangChain、FAISS、LangGraph、pypdf。

当前验证环境为 Windows、Python 3.11.17。

聊天模型：qwen3.5:9b  
向量模型：qwen3-embedding:4b

当前聊天工厂固定使用 Ollama；DeepSeek 服务代码尚未接入工厂切换。

## 核心流程

```text
用户问题 + 会话 ID + 知识库 ID
    ↓
从 SQLite 读取聊天历史
    ↓
模型节点：直接回答，或提出工具调用请求
    ├─ 无工具请求 → 结束
    └─ 有工具请求
          ↓
       工具节点：FAISS 检索，结果加入消息列表
          ↓
       回到模型节点，继续处理
    ↓
保存本轮问答，返回回答
```

RAG 接口固定先检索；Agent 接口由模型决定是否请求检索工具。

## 主要文件

| 文件 | 作用 |
|---|---|
| main.py | FastAPI 路由和请求模型 |
| app/core/config.py | 配置读取 |
| app/core/database.py | 数据库连接和会话工厂 |
| app/models/ | 会话表、消息表定义 |
| app/services/ollama_service.py | 普通、流式及工具调用请求 |
| app/services/conversation_service.py | 会话与聊天历史读写 |
| app/services/knowledge_service.py | 文件解析、切分、FAISS 建库与检索 |
| app/services/indexing_service.py | 按 ID 创建和获取知识库 |
| app/services/rag_service.py | 固定检索后生成带来源的回答 |
| app/services/graph_service.py | LangGraph 节点、路由及工具循环 |
| tools/definitions.py | 模型可用的工具说明 |

agent_service.py 保留早期普通 Python 工具调用实现；
当前 Agent 接口使用 graph_service.py。

## 本地运行

需要安装并运行 Ollama，下载模型：

```powershell
ollama pull qwen3.5:9b
ollama pull qwen3-embedding:4b
```

在 Python 环境中安装依赖：

```powershell
python -m pip install fastapi "uvicorn[standard]" aiohttp pydantic-settings sqlalchemy aiosqlite langgraph langchain-core langchain-community langchain-ollama langchain-text-splitters faiss-cpu pypdf python-multipart
```

在项目根目录创建 `.env`：

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=qwen3.5:9b
```

向量模型名称目前在 knowledge_service.py 中配置。

在项目根目录启动：

```powershell
python -m uvicorn main:app --reload --port 8001
```

接口文档：http://127.0.0.1:8001/docs

启动时会自动创建缺少的数据库表。
上述依赖清单依据当前代码整理，尚未验证全新环境安装。

## 演示步骤

1. 调用 `POST /api/knowledge/load`，加载内置机器人测试资料，
   记录返回的 `index_id`。
   也可以通过 `POST /api/knowledge/upload` 上传 TXT/PDF。

2. 调用 `POST /api/conversations`：

```json
{"title": "机器人客服演示"}
```

记录返回的 `id`，作为 `conversation_id`。

3. 调用 `POST /api/agent/chat`：

```json
{
  "conversation_id": "替换成会话ID",
  "index_id": "替换成知识库ID",
  "question": "ZS-T01出现E731错误怎么处理？"
}
```

4. 保持会话 ID 不变继续提问，即可使用历史上下文。

5. 调用 `GET /api/conversations/{conversation_id}/messages`
   查看已保存的问答。

数据库位于 data/chat.sqlite3，上传文件位于 uploads/，
FAISS 索引位于 indexes/。这些运行数据不提交到 Git。

## 已完成的人工验证

| 场景 | 观察结果 |
|---|---|
| E731 故障处理 | 返回资料中的故障原因和四个步骤 |
| 滤网清洁周期 | 正确回答累计运行37小时 |
| 售后服务时间 | 正确回答工作日9:30至17:30 |
| 多轮上下文 | 能从前一轮消息找回机器人昵称“小绿” |
| 索引恢复 | 服务重启后，同一 index_id 可继续检索 |
| 未知故障码 E999 | 原先编造电池故障；加强资料依据要求后，观察到明确拒答 |

这些是少量人工验证结果，不代表系统准确率或稳定性统计。

## 当前不足

- 模型可能添加资料未支持的内容，提示词不能保证消除幻觉。
- 当前默认检索 top-2，没有相关性阈值和重排序。
- 不支持扫描版 PDF 的 OCR。
- 每轮读取完整聊天历史，尚未实现长对话裁剪。
- Agent 接口目前只返回回答；参考片段和页码由 RAG 接口返回。
- 尚未进行并发、性能和大规模效果评估。