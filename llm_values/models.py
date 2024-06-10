import os
from datetime import datetime
from typing import List
from typing import Optional

from decouple import config
from sqlalchemy import ForeignKey, String, create_engine, Float, Boolean, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def update(self, data):
        for attr, value in data.items():
            setattr(self, attr, value)

    def dict(self):
        return {
            key: attr for key, attr in self.__dict__.items() if not key.startswith("_")
        }


class Topic(Base):
    __tablename__ = "topic"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String)

    questions: Mapped[List["Question"]] = relationship(back_populates="topic", cascade="all, delete-orphan")
    answers: Mapped[List["Answer"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Topic(id={self.id!r}, name={self.name})"


class Question(Base):
    __tablename__ = "question"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String())
    description: Mapped[str] = mapped_column(String())
    mode: Mapped[str] = mapped_column(String, nullable=True)
    question: Mapped[str] = mapped_column(String())
    translations: Mapped[dict] = mapped_column(JSON, nullable=True, default={})
    re_translations: Mapped[dict] = mapped_column(JSON, nullable=True, default={})

    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id"))
    topic: Mapped["Topic"] = relationship(back_populates="questions")

    answers: Mapped[List["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Question(id={self.id!r}, question={self.question[:100]})"


class Answer(Base):
    __tablename__ = "answer"
    id: Mapped[int] = mapped_column(primary_key=True)
    prompts: Mapped[dict] = mapped_column(JSON, nullable=True)
    prefixes: Mapped[dict] = mapped_column(JSON, nullable=True)
    formats: Mapped[dict] = mapped_column(JSON, nullable=True)
    prefixes_retranslated: Mapped[dict] = mapped_column(JSON, nullable=True)
    formats_retranslated: Mapped[dict] = mapped_column(JSON, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(index=True, default=datetime.utcnow)

    model: Mapped[str] = mapped_column(String())
    temperature: Mapped[float] = mapped_column(Float(), default=0.0)
    max_tokens: Mapped[int] = mapped_column(Integer())
    rating_last: Mapped[bool] = mapped_column(Boolean(), default=False)
    answer_english: Mapped[bool] = mapped_column(Boolean(), default=False)
    question_english: Mapped[bool] = mapped_column(Boolean(), default=False)

    answers: Mapped[dict] = mapped_column(JSON, nullable=True)
    translations: Mapped[dict] = mapped_column(JSON, nullable=True)
    ratings: Mapped[dict] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, nullable=True)

    question_id: Mapped[int] = mapped_column(ForeignKey("question.id"))
    question: Mapped["Question"] = relationship(back_populates="answers")

    topic_id: Mapped[int] = mapped_column(ForeignKey("topic.id"))
    topic: Mapped["Topic"] = relationship(back_populates="answers")

    def __repr__(self) -> str:
        return f"Answer(id={self.id!r}, answer={self.answers['English'][:50]} ... {self.answers['English'][-50:]})"


engine = create_engine(config("DATABASE_URL", os.getenv("DATABASE_URL")))
Base.metadata.create_all(engine)
