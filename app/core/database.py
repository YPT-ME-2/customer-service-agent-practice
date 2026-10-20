import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import ROOT_DIR

# 数据文件的位置
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_FILE=DATA_DIR / "chat.sqlite3"

## 告诉 SQLAlchemy：使用 aiosqlite 驱动访问这个 SQLite 文件
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE.as_posix()}"

# 数据库引擎：负责连接数据库
engine = create_async_engine(DATABASE_URL)

# 数据库会话工厂：每次调用，获得一次数据库操作所用的会话
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# 后续描述数据表的类，都继承它
class Base(DeclarativeBase):
    pass

async def test_connection():
    try:
        async with engine.connect() as connection:
            result=await connection.execute(text("SELECT 1"))
            print("数据库连接成功：", result.scalar())
    finally:
        await engine.dispose()

if __name__=="__main__":
    asyncio.run(test_connection())