import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..llm import LLMError, llm_client
from ..mbti import (
    CONFIDENCE_TARGET,
    DIMENSIONS,
    DIMENSION_INFO,
    FREETEXT_CONFIDENCE_DELTA,
    MAX_QUESTIONS,
    OPTION_CONFIDENCE_DELTA,
    SCORE_MAX,
    build_report_dimensions,
    compute_type,
    is_converged,
    pick_next_dimension,
)
from ..models import Answer, DimensionState, Question, Report, TestSession, report_to_dict
from ..schemas import AnswerRequest
from .deps import get_current_user

router = APIRouter()

OPTION_LETTERS = "ABCD"


def _get_in_progress_session(db: Session, user_id: int) -> TestSession | None:
    return (
        db.query(TestSession)
        .filter_by(user_id=user_id, status="in_progress")
        .order_by(TestSession.id.desc())
        .first()
    )


def _states_map(session: TestSession) -> dict[str, DimensionState]:
    return {st.dimension: st for st in session.dimension_states}


def _question_dict(q: Question) -> dict:
    return {
        "id": q.id,
        "dimension": q.dimension,
        "dimension_name": DIMENSION_INFO[q.dimension]["name"],
        "order_num": q.order_num,
        "content": q.content,
        "options": q.option_texts,
    }


def _progress(states: dict[str, DimensionState]) -> dict:
    return {
        d: {
            "name": DIMENSION_INFO[d]["name"],
            "score": round(st.score, 1),
            "confidence": round(st.confidence, 1),
            "confidence_percent": min(100, int(st.confidence / CONFIDENCE_TARGET * 100)),
            "converged": st.confidence >= CONFIDENCE_TARGET,
        }
        for d, st in states.items()
    }


def _transcript(session: TestSession) -> list[dict]:
    items = []
    for q in session.questions:
        if q.answer is None:
            continue
        items.append({
            "question": _question_dict(q),
            "answer": q.answer.content,
        })
    return items


def _create_next_question(db: Session, session: TestSession) -> Question:
    """选维度、调用 LLM 出题、落库，返回新题目。"""
    states = _states_map(session)
    asked = [q for q in session.questions]
    last_dimension = asked[-1].dimension if asked else None

    dimension = pick_next_dimension(
        {d: {"score": st.score, "confidence": st.confidence} for d, st in states.items()},
        last_dimension,
    )
    if dimension is None:
        raise HTTPException(status_code=500, detail="所有维度已收敛但会话未正确结束")

    asked_for_dim = [q.content for q in asked if q.dimension == dimension]
    try:
        qdata = llm_client.generate_question(dimension, asked_for_dim)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"AI 出题失败：{e}")

    question = Question(
        session_id=session.id,
        dimension=dimension,
        order_num=session.question_count + 1,
        content=qdata["question"],
        options=json.dumps(qdata["options"], ensure_ascii=False),
    )
    db.add(question)
    session.question_count += 1
    db.commit()
    db.refresh(question)
    return question


def _question_response(session: TestSession, question: Question) -> dict:
    return {
        "status": "question",
        "session_id": session.id,
        "question_num": question.order_num,
        "max_questions": MAX_QUESTIONS,
        "question": _question_dict(question),
        "progress": _progress(_states_map(session)),
    }


def _finalize_session(db: Session, session: TestSession) -> Report:
    """收敛后：算类型、生成报告、关闭会话。"""
    states = _states_map(session)
    scores = {d: st.score for d, st in states.items()}
    mbti_type = compute_type(scores)
    try:
        report_data = llm_client.generate_report(mbti_type, scores)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"AI 报告生成失败：{e}")

    dimensions = build_report_dimensions(scores, report_data["dimensions"])
    report = Report(
        session_id=session.id,
        user_id=session.user_id,
        mbti_type=mbti_type,
        type_name=report_data["type_name"],
        portrait=report_data["portrait"],
        strengths=json.dumps(report_data["strengths"], ensure_ascii=False),
        weaknesses=json.dumps(report_data["weaknesses"], ensure_ascii=False),
        careers=json.dumps(report_data["careers"], ensure_ascii=False),
        famous=json.dumps(report_data["famous"], ensure_ascii=False),
        advice=report_data["advice"],
        dimensions=json.dumps(dimensions, ensure_ascii=False),
    )
    session.status = "completed"
    session.final_type = mbti_type
    session.completed_at = datetime.now()
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("")
def start_test(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """开始新测试：放弃进行中的旧会话，初始化四维度状态并出第一题。"""
    db.query(TestSession).filter_by(user_id=user.id, status="in_progress").update(
        {"status": "abandoned"}
    )
    session = TestSession(user_id=user.id)
    db.add(session)
    db.flush()
    for d in DIMENSIONS:
        db.add(DimensionState(session_id=session.id, dimension=d, score=0.0, confidence=0.0))
    db.commit()
    db.refresh(session)
    question = _create_next_question(db, session)
    return _question_response(session, question)


@router.get("/current")
def current_test(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """恢复进行中的测试（刷新页面后还原对话与进度）。"""
    session = _get_in_progress_session(db, user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="没有进行中的测试")

    current = next((q for q in session.questions if q.answer is None), None)
    if current is None:
        # 异常中断恢复：全部已答但会话未结束时，直接收敛出报告或补出下一题
        snapshot = {
            d: {"score": st.score, "confidence": st.confidence}
            for d, st in _states_map(session).items()
        }
        if is_converged(snapshot) or session.question_count >= MAX_QUESTIONS:
            report = _finalize_session(db, session)
            return {
                "status": "completed",
                "report": report_to_dict(report, session.question_count),
            }
        current = _create_next_question(db, session)
    return {**_question_response(session, current), "transcript": _transcript(session)}


@router.post("/current/answer")
def submit_answer(
    body: AnswerRequest, user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """提交回答：更新维度状态，返回下一题或最终报告。"""
    session = _get_in_progress_session(db, user.id)
    if session is None:
        raise HTTPException(status_code=404, detail="没有进行中的测试")

    question = db.get(Question, body.question_id)
    if question is None or question.session_id != session.id:
        raise HTTPException(status_code=400, detail="题目不存在或不属于当前测试")
    if question.answer is not None:
        raise HTTPException(status_code=400, detail="该题目已作答")

    content = body.content.strip()
    if len(content) == 1 and content.upper() in OPTION_LETTERS:
        content = content.upper()
    states = _states_map(session)

    if content in OPTION_LETTERS and len(content) == 1:
        idx = OPTION_LETTERS.index(content)
        evidence = question.option_list[idx]["lean"]
        confidence_delta = OPTION_CONFIDENCE_DELTA
        reasoning = None
        display = f"{content}. {question.option_texts[idx]}"
    else:
        try:
            result = llm_client.score_free_text(question.dimension, question.content, content)
        except LLMError as e:
            raise HTTPException(status_code=502, detail=f"AI 评分失败：{e}")
        evidence = result["evidence"]
        confidence_delta = FREETEXT_CONFIDENCE_DELTA
        reasoning = result["reasoning"]
        display = content

    state = states[question.dimension]
    state.score = max(-SCORE_MAX, min(SCORE_MAX, state.score + evidence))
    state.confidence += confidence_delta

    db.add(Answer(
        question_id=question.id,
        session_id=session.id,
        content=display,
        evidence=evidence,
        confidence_delta=confidence_delta,
        reasoning=reasoning,
    ))
    db.flush()

    state_snapshot = {d: {"score": st.score, "confidence": st.confidence} for d, st in states.items()}
    if is_converged(state_snapshot) or session.question_count >= MAX_QUESTIONS:
        report = _finalize_session(db, session)
        return {
            "status": "completed",
            "report": report_to_dict(report, session.question_count),
        }

    next_question = _create_next_question(db, session)
    return {
        **_question_response(session, next_question),
        "last_reasoning": reasoning,
    }
