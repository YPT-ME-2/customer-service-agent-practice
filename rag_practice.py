from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import ROOT_DIR,settings

# 1. 读取文件内容
filepath = ROOT_DIR/"data"/"机器人测试说明.txt"
text=filepath.read_text(encoding="utf-8")

# 2. 把正文和来源放进 Document
document=Document(
    page_content=text,
    metadata={"source":filepath.name},
)

# 3. 切成较短的片段
splitter=RecursiveCharacterTextSplitter(
    chunk_size=100,
    chunk_overlap=20,
    separators=["\n\n", "\n", "。", ""],
)
chunks=splitter.split_documents([document])

print("文档片段数：", len(chunks))

# 4. 准备嵌入模型客户端
embedding = OllamaEmbeddings(
    model="qwen3-embedding:4b",
    base_url=settings.OLLAMA_BASE_URL,
    client_kwargs={"trust_env":False},
)

# 5. 将片段向量化，存入内存向量库
vector_store=InMemoryVectorStore(embedding=embedding)
vector_store.add_documents(chunks)

# 6. 根据问题检索两个相关片段
query="ZS-T01出现E731错误怎么处理？"
results=vector_store.similarity_search(query,k=2)

for index,doc in enumerate(results,start=1):
    print(f"\n【检索结果{index}】")
    print("来源：", doc.metadata["source"])
    print(doc.page_content)