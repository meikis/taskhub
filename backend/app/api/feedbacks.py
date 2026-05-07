from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from app.database import get_session
from app.models import FeedbackCreate, FeedbackRead, FeedbackReview, FeedbackStatus, UserRead
from app.crud import create_feedback, get_feedback, list_feedbacks, review_feedback
from app.api.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])

@router.post("", response_model=FeedbackRead)
def submit_feedback(
    data: FeedbackCreate,
    db: Session = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
):
    return create_feedback(db, data, current_user.id)

@router.get("", response_model=List[FeedbackRead])
def get_feedbacks(
    status: Optional[str] = None,
    category: Optional[str] = None,
    mine_only: bool = False,
    db: Session = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
):
    submitter_id = current_user.id if mine_only else None
    # 普通用户只看自己的 + 已通过的；管理员看全部
    if current_user.role != "admin":
        from sqlalchemy import or_
        from app.models import Feedback
        query = db.query(Feedback)
        if status:
            query = query.where(Feedback.status == status)
        if category:
            query = query.where(Feedback.category == category)
        # 非管理员：只能看自己提交的，或者已 approved / implemented 的
        query = query.where(
            or_(Feedback.submitter_id == current_user.id,
                Feedback.status.in_(["approved", "implemented"]))
        )
        if submitter_id is not None:
            query = query.where(Feedback.submitter_id == submitter_id)
        return query.order_by(Feedback.created_at.desc()).all()
    return list_feedbacks(db, status=status, category=category, submitter_id=submitter_id)

@router.get("/{feedback_id}", response_model=FeedbackRead)
def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
):
    fb = get_feedback(db, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    # 权限检查
    if current_user.role != "admin" and fb.submitter_id != current_user.id and fb.status not in ["approved", "implemented"]:
        raise HTTPException(status_code=403, detail="Not allowed to view this feedback")
    return fb

@router.put("/{feedback_id}/review", response_model=FeedbackRead)
def review(
    feedback_id: int,
    data: FeedbackReview,
    db: Session = Depends(get_session),
    current_user: UserRead = Depends(get_current_admin),
):
    fb = get_feedback(db, feedback_id)
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return review_feedback(
        db, fb, current_user.id,
        status=data.status.value,
        priority=data.priority.value if data.priority else None,
        review_comment=data.review_comment,
    )

@router.get("/stats/summary")
def stats(
    db: Session = Depends(get_session),
    _=Depends(get_current_admin),
):
    from app.models import Feedback
    total = db.query(Feedback).count()
    pending = db.query(Feedback).where(Feedback.status == "pending").count()
    approved = db.query(Feedback).where(Feedback.status == "approved").count()
    rejected = db.query(Feedback).where(Feedback.status == "rejected").count()
    implemented = db.query(Feedback).where(Feedback.status == "implemented").count()
    return {"total": total, "pending": pending, "approved": approved, "rejected": rejected, "implemented": implemented}