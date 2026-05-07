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
    old_data = {k: getattr(task, k) for k in ['title', 'description', 'priority', 'status', 'assignee_id', 'estimated_hours', 'tags', 'deadline', 'parent_id']}
    task = update_task(db, task, data)
    changes = []
    new_data = {k: getattr(task, k) for k in ['title', 'description', 'priority', 'status', 'assignee_id', 'estimated_hours', 'tags', 'deadline', 'parent_id']}
    field_names = {'title':'标题','description':'描述','priority':'优先级','status':'状态','assignee_id':'负责人','estimated_hours':'预估工时','tags':'标签','deadline':'截止日期','parent_id':'父任务'}
    for key in old_data:
        if old_data[key] != new_data[key]:
            old_val = str(old_data[key]) if old_data[key] is not None else '无'
            new_val = str(new_data[key]) if new_data[key] is not None else '无'
            changes.append(f"{field_names.get(key,key)}: {old_val} → {new_val}")
    if changes:
        create_task_log(db, task.id, current_user.id, "修改任务", comment="; ".join(changes))
    if data.status and data.status != old_data['status']:
        create_task_log(db, task.id, current_user.id, "更新状态", from_status=str(old_data['status']), to_status=str(data.status))
    return enrich_task(db, task)

@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    from app.models import Task
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.creator_id != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="只有创建者或管理员可以删除任务")
    from sqlmodel import select
    subtasks = db.exec(select(Task).where(Task.parent_id == task_id)).all()
    for st in subtasks:
        st.parent_id = None
        db.add(st)
    create_task_log(db, task.id, current_user.id, "删除任务", comment=f"删除了任务: {task.title}")
    db.delete(task)
    db.commit()
    return {"message": "任务删除成功"}

@router.get("/{task_id}/subtasks", response_model=List[TaskRead])
def get_subtasks(task_id: int, db: Session = Depends(get_session), current_user: UserRead = Depends(get_current_user)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    from sqlmodel import select
    subtasks = db.exec(select(Task).where(Task.parent_id == task_id)).all()
    return [enrich_task(db, st) for st in subtasks]

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
    from sqlmodel import select
    from app.models import Task
    creator = get_user_by_id(db, task.creator_id)
    assignee = get_user_by_id(db, task.assignee_id) if task.assignee_id else None
    subtasks = db.exec(select(Task).where(Task.parent_id == task.id)).all()
    subtask_list = []
    for st in subtasks:
        st_creator = get_user_by_id(db, st.creator_id)
        st_assignee = get_user_by_id(db, st.assignee_id) if st.assignee_id else None
        subtask_list.append(TaskRead(
            id=st.id,
            title=st.title,
            description=st.description,
            task_type=st.task_type,
            priority=st.priority,
            status=st.status,
            department=st.department,
            estimated_hours=st.estimated_hours,
            tags=st.tags,
            deadline=st.deadline,
            creator_id=st.creator_id,
            assignee_id=st.assignee_id,
            parent_id=st.parent_id,
            created_at=st.created_at,
            claimed_at=st.claimed_at,
            completed_at=st.completed_at,
            creator=UserRead.model_validate(st_creator) if st_creator else None,
            assignee=UserRead.model_validate(st_assignee) if st_assignee else None,
            subtasks=[],
        ))
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        priority=task.priority,
        status=task.status,
        department=task.department,
        estimated_hours=task.estimated_hours,
        tags=task.tags,
        deadline=task.deadline,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        parent_id=task.parent_id,
        created_at=task.created_at,
        claimed_at=task.claimed_at,
        completed_at=task.completed_at,
        creator=UserRead.model_validate(creator) if creator else None,
        assignee=UserRead.model_validate(assignee) if assignee else None,
        subtasks=subtask_list,
    )