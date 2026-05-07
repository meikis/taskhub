from sqlmodel import Session, select, desc
from typing import Optional, List
from app.models import User, UserCreate, Task, TaskCreate, TaskUpdate, TaskLog, TaskStatus
from app.core.security import get_password_hash

# ========== 用户 CRUD ==========
def create_user(db: Session, user: UserCreate) -> User:
    db_user = User(
        username=user.username,
        hashed_password=get_password_hash(user.password),
        display_name=user.display_name,
        role=user.role,
        skills=user.skills,
        department=user.department,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.exec(select(User).where(User.username == username)).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.exec(select(User).where(User.id == user_id)).first()

def list_users(db: Session) -> List[User]:
    return db.exec(select(User).where(User.disabled == False)).all()

# ========== 任务 CRUD ==========
def create_task(db: Session, task: TaskCreate, creator_id: int) -> Task:
    db_task = Task(
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        priority=task.priority,
        status=TaskStatus.DRAFT if task.status is None else task.status,
        department=task.department,
        estimated_hours=task.estimated_hours,
        tags=task.tags,
        deadline=task.deadline,
        parent_id=task.parent_id,
        creator_id=creator_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.exec(select(Task).where(Task.id == task_id)).first()

def list_tasks(
    db: Session,
    status: Optional[TaskStatus] = None,
    assignee_id: Optional[int] = None,
    creator_id: Optional[int] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[Task]:
    query = select(Task)
    if status:
        query = query.where(Task.status == status)
    if assignee_id is not None:
        query = query.where(Task.assignee_id == assignee_id)
    if creator_id is not None:
        query = query.where(Task.creator_id == creator_id)
    if priority:
        query = query.where(Task.priority == priority)
    if task_type:
        query = query.where(Task.task_type == task_type)
    if keyword:
        query = query.where(Task.title.contains(keyword))
    query = query.order_by(desc(Task.created_at))
    return db.exec(query).all()

def update_task(db: Session, db_task: Task, update: TaskUpdate) -> Task:
    data = update.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(db_task, key, value)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

# ========== 日志 CRUD ==========
def create_task_log(
    db: Session,
    task_id: int,
    user_id: int,
    action: str,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    comment: Optional[str] = None,
) -> TaskLog:
    log = TaskLog(
        task_id=task_id,
        user_id=user_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

# ========== 反馈 CRUD ==========
def create_feedback(db: Session, feedback: "FeedbackCreate", submitter_id: int) -> "Feedback":
    from app.models import Feedback
    db_fb = Feedback(
        title=feedback.title,
        description=feedback.description,
        category=feedback.category,
        submitter_id=submitter_id,
    )
    db.add(db_fb)
    db.commit()
    db.refresh(db_fb)
    return db_fb

def get_feedback(db: Session, feedback_id: int) -> Optional["Feedback"]:
    from app.models import Feedback
    return db.exec(select(Feedback).where(Feedback.id == feedback_id)).first()

def list_feedbacks(
    db: Session,
    status: Optional[str] = None,
    category: Optional[str] = None,
    submitter_id: Optional[int] = None,
) -> List["Feedback"]:
    from app.models import Feedback
    query = select(Feedback)
    if status:
        query = query.where(Feedback.status == status)
    if category:
        query = query.where(Feedback.category == category)
    if submitter_id is not None:
        query = query.where(Feedback.submitter_id == submitter_id)
    query = query.order_by(desc(Feedback.created_at))
    return db.exec(query).all()

def review_feedback(
    db: Session,
    db_fb: "Feedback",
    reviewer_id: int,
    status: str,
    priority: Optional[str],
    review_comment: Optional[str],
) -> "Feedback":
    from datetime import datetime
    db_fb.status = status
    db_fb.reviewer_id = reviewer_id
    db_fb.review_at = datetime.utcnow()
    if priority is not None:
        db_fb.priority = priority
    if review_comment is not None:
        db_fb.review_comment = review_comment
    db.add(db_fb)
    db.commit()
    db.refresh(db_fb)
    return db_fb

def list_task_logs(db: Session, task_id: int) -> List[TaskLog]:
    return db.exec(
        select(TaskLog).where(TaskLog.task_id == task_id).order_by(desc(TaskLog.created_at))
    ).all()