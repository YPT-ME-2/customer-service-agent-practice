import asyncio

from app.core.database import Base, engine, AsyncSessionLocal
from app.models.message import Message

async def main():
    try:
        # 1. 根据模型定义，在数据库里创建尚不存在的表
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        print("消息表已准备好")

        # 2. 创建数据库会话，保存一条消息
        async with AsyncSessionLocal() as db:
            message = Message(
                conversation_id="db-practice",
                role="user",
                content="我的机器人叫小蓝",
            )

            db.add(message)
            await db.commit()

            message_id = message.id
            print("保存成功，消息编号：", message_id)

        # 3. 原来的会话已关闭，再创建一个会话读取
        async with AsyncSessionLocal() as db:
            saved_message = await db.get(Message, message_id)

            if saved_message is None:
                print("没有找到消息")
                return

            print("读取成功：")
            print("会话编号：", saved_message.conversation_id)
            print("消息角色：", saved_message.role)
            print("消息正文：", saved_message.content)

    finally:
        await engine.dispose()

if __name__=="__main__":
    asyncio.run(main())
                  