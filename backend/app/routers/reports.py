import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Report, TestSession, report_to_dict
from .deps import get_current_user

router = APIRouter()


@router.get("")
def list_reports(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户的历史报告列表。"""
    rows = (
        db.query(Report, TestSession)
        .join(TestSession, Report.session_id == TestSession.id)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return [
        {
            "id": report.id,
            "mbti_type": report.mbti_type,
            "type_name": report.type_name,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "question_count": session.question_count,
        }
        for report, session in rows
    ]


@router.get("/trend")
def trend(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """按时间排列的各维度得分，用于绘制性格变化曲线。"""
    reports = (
        db.query(Report)
        .filter(Report.user_id == user.id)
        .order_by(Report.created_at.asc())
        .all()
    )
    points = []
    for report in reports:
        dims = json.loads(report.dimensions)
        points.append({
            "date": report.created_at.isoformat() if report.created_at else None,
            "mbti_type": report.mbti_type,
            "scores": {d: dims[d]["score"] for d in dims},
        })
    return points


@router.get("/{report_id}")
def get_report(report_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(status_code=404, detail="报告不存在")
    session = db.get(TestSession, report.session_id)
    return report_to_dict(report, session.question_count if session else None)
