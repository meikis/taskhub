from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from app.database import get_session
from app.models import TaskCreate, TaskRead, TaskUpdate, TaskStatus, UserRead, TaskLogRead
from app.crud import create_task, get_task, list_tasks, update_task, create_task_log, list_task_logs, get_user_by_id
from app.api.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("", response_model=TaskRead)
def new_task(data: TaskCreate, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    task = create_task(db, data, current_user.id)
    create_task_log(db, task.id, current_user.id, "创建任务", comment="任务初始化")
    return enrich_task(db, task)

@router.get("", response_model=List[TaskRead])
def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    assignee_id: Optional[int] = None,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_session),
    current_user: UserRead = Depends(get_current_user),
):
    tasks = list_tasks(db, status=status, priority=priority, task_type=task_type, keyword=keyword, assignee_id=assignee_id, creator_id=creator_id)
    return [enrich_task(db, t) for t in tasks]

@router.get("/{task_id}", response_model=TaskRead)
def get_task_detail(task_id: int, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return enrich_task(db, task)

@router.post("/{task_id}/claim", response_model=TaskRead)
def claim_task(task_id: int, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.OPEN and task.status != TaskStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Task not claimable")
    task.assignee_id = current_user.id
    task.status = TaskStatus.IN_PROGRESS
    task.claimed_at = __import__("datetime").datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    create_task_log(db, task.id, current_user.id, "认领任务", from_status="open", to_status="in_progress")
    return enrich_task(db, task)

@router.patch("/{task_id}", response_model=TaskRead)
def patch_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    old_status = task.status
    task = update_task(db, task, data)
    if data.status and data.status != old_status:
        create_task_log(db, task.id, current_user.id, "更新状态", from_status=old_status, to_status=data.status)
    return enrich_task(db, task)

@router.get("/{task_id}/logs", response_model=List[TaskLogRead])
def get_logs(task_id: int, db: Session = Depends(get_session)):
    logs = list_task_logs(db, task_id)
    result = []
    for log in logs:
        lr = TaskLogRead.model_validate(log)
        lr.user = UserRead.model_validate(get_user_by_id(db, log.user_id)) if get_user_by_id(db, log.user_id) else None
        result.append(lr)
    return result

def enrich_task(db: Session, task):
    tr = TaskRead.model_validate(task)
    tr.creator = UserRead.model_validate(get_user_by_id(db, task.creator_id)) if get_user_by_id(db, task.creator_id) else None
    tr.assignee = UserRead.model_validate(get_user_by_id(db, task.assignee_id)) if task.assignee_id and get_user_by_id(db, task.assignee_id) else None
    return tr