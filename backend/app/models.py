import json
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sessions: Mapped[list["TestSession"]] = relationship(back_populates="user")


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # in_progress / completed / abandoned
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    final_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="session", order_by="Question.order_num"
    )
    dimension_states: Mapped[list["DimensionState"]] = relationship(back_populates="session")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("test_sessions.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(2))
    order_num: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    # JSON: [{"text": "...", "lean": -2}, ...]；lean 仅服务端可见，不下发给前端
    options: Mapped[str] = mapped_column(Text)

    session: Mapped[TestSession] = relationship(back_populates="questions")
    answer: Mapped["Answer | None"] = relationship(back_populates="question", uselist=False)

    @property
    def option_list(self) -> list[dict]:
        return json.loads(self.options)

    @property
    def option_texts(self) -> list[str]:
        return [opt["text"] for opt in self.option_list]


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("test_sessions.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    evidence: Mapped[float] = mapped_column(Float)
    confidence_delta: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    question: Mapped[Question] = relationship(back_populates="answer")


class DimensionState(Base):
    __tablename__ = "dimension_states"
    __table_args__ = (UniqueConstraint("session_id", "dimension", name="uq_session_dimension"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("test_sessions.id"), index=True)
    dimension: Mapped[str] = mapped_column(String(2))
    score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped[TestSession] = relationship(back_populates="dimension_states")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("test_sessions.id"), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mbti_type: Mapped[str] = mapped_column(String(4))
    type_name: Mapped[str] = mapped_column(String(50))
    portrait: Mapped[str] = mapped_column(Text)
    # 以下字段均存 JSON 数组/对象字符串
    strengths: Mapped[str] = mapped_column(Text)
    weaknesses: Mapped[str] = mapped_column(Text)
    careers: Mapped[str] = mapped_column(Text)
    famous: Mapped[str] = mapped_column(Text)
    advice: Mapped[str] = mapped_column(Text)
    dimensions: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


def report_to_dict(report: Report, question_count: int | None = None) -> dict:
    return {
        "id": report.id,
        "session_id": report.session_id,
        "mbti_type": report.mbti_type,
        "type_name": report.type_name,
        "portrait": report.portrait,
        "strengths": json.loads(report.strengths),
        "weaknesses": json.loads(report.weaknesses),
        "careers": json.loads(report.careers),
        "famous": json.loads(report.famous),
        "advice": report.advice,
        "dimensions": json.loads(report.dimensions),
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "question_count": question_count,
    }
