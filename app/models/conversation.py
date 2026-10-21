from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


from app.core.database import Base

class Conversation(Base):
    __tablename__="conversations"
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(100),
        default="新会话",
    )