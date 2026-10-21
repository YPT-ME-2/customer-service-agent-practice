# class ConversationService:
#     def __init__(self):
#         self.histories:dict[str,list[dict[str,str]]]={}

#     def get_history(self,conversation_id:str)->list[dict[str,str]]:
#         messages=self.histories.get(conversation_id,[])
#         return [message.copy() for message in messages]

#     def save_turn(
#         self,
#         conversation_id:str,
#         question:str,
#         answer:str
#     ):
#         if conversation_id not in self.histories:
#             self.histories[conversation_id]=[]

#         self.histories[conversation_id].extend([
#             {"role": "user", "content": question},
#             {"role": "assistant", "content": answer},
#         ])
        
from sqlalchemy import select,delete

from app.core.database import AsyncSessionLocal
from app.models.message import Message
#这里不再需要 __init__() 和 self.histories，因为存储工作交给数据库了。

from uuid import uuid4
from app.models.conversation import Conversation

class ConversationService:
    async def get_history(
        self,
        conversation_id: str,
    ) -> list[dict[str, str]]:
        async with AsyncSessionLocal() as db:
            statement = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.id)
            )

            result = await db.execute(statement)
            messages = result.scalars().all()

            return [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ]

    async def save_turn(
        self,
        conversation_id: str,
        question: str,
        answer: str,
    ):
        async with AsyncSessionLocal() as db:
            db.add_all([
                Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=question,
                ),
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                ),
            ])

            await db.commit()

    async def clear_history(self,conversation_id:str):
        async with AsyncSessionLocal() as db:
            statement=delete(Message).where(
                Message.conversation_id==conversation_id
            )
            await db.execute(statement)
            await db.commit()

    # async def list_conversations(self)->list[str]:
    #     async with AsyncSessionLocal() as db:
    #         statement=(
    #             select(Message.conversation_id).distinct().order_by(Message.conversation_id)
    #         )
    #         result=await db.execute(statement)
    #         return result.scalars().all()
    async def list_conversations(self) -> list[dict[str, str]]:
        async with AsyncSessionLocal() as db:
            statement = select(Conversation).order_by(Conversation.id)

            result = await db.execute(statement)
            conversations = result.scalars().all()

            return [
                {
                    "id": conversation.id,
                    "title": conversation.title,
                }
                for conversation in conversations
            ]

    async def create_conversation(self,title:str)->dict[str,str]:
        async with AsyncSessionLocal() as db:
            conversation=Conversation(
                id=uuid4().hex,#uuid4().hex 自动生成一个随机会话编号
                title=title,
            )
            db.add(conversation)
            await db.commit()
            return{
                "id": conversation.id,
                "title": conversation.title,
            }

    async def rename_conversation(self,conversation_id: str,title: str,) -> bool:
        async with AsyncSessionLocal() as db:
            conversation = await db.get(
                Conversation,
                conversation_id,
            )

            if conversation is None:
                return False

            conversation.title = title
            await db.commit()

            return True