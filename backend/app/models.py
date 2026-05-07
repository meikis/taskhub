from __future__ import annotations
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum
from typing import Optional, List

class TaskStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    DONE = "done"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"
    REJECTED = "rejected"

class TaskType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TECH_DEBT = "tech_debt"
    RESEARCH = "research"
    OTHER = "other"

class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    OBSERVER = "observer"

class FeedbackCategory(str, Enum):
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    BUG = "bug"
    EXPERIENCE = "experience"
    OTHER = "other"

class FeedbackStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"

# ========== 用户 ==========
class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    display_name: str
    role: UserRole = Field(default=UserRole.USER)
    skills: Optional[str] = Field(default=None)  # JSON array string
    department: Optional[str] = Field(default=None)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disabled: bool = Field(default=False)

class UserCreate(SQLModel):
    username: str
    password: str
    display_name: str
    role: UserRole = UserRole.USER
    skills: Optional[str] = None
    department: Optional[str] = None

class UserRead(UserBase):
    id: int
    created_at: datetime

class UserLogin(SQLModel):
    username: str
    password: str

# ========== 任务 ==========
class TaskBase(SQLModel):
    title: str
    description: Optional[str] = Field(default=None)
    task_type: TaskType = Field(default=TaskType.OTHER)
    priority: Priority = Field(default=Priority.P2)
    status: TaskStatus = Field(default=TaskStatus.OPEN)
    department: Optional[str] = Field(default=None)
    estimated_hours: Optional[int] = Field(default=None)
    tags: Optional[str] = Field(default=None)  # JSON array string
    deadline: Optional[datetime] = Field(default=None)

class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    creator_id: int = Field(foreign_key="user.id")
    assignee_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    claimed_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

class TaskCreate(SQLModel):
    title: str
    description: Optional[str] = None
    task_type: TaskType = TaskType.OTHER
    priority: Priority = Priority.P2
    status: Optional[TaskStatus] = None
    department: Optional[str] = None
    estimated_hours: Optional[int] = None
    tags: Optional[str] = None
    deadline: Optional[datetime] = None

class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[Priority] = None
    status: Optional[TaskStatus] = None
    assignee_id: Optional[int] = None
    estimated_hours: Optional[int] = None
    tags: Optional[str] = None
    deadline: Optional[datetime] = None

class TaskRead(TaskBase):
    id: int
    creator_id: int
    assignee_id: Optional[int]
    created_at: datetime
    claimed_at: Optional[datetime]
    completed_at: Optional[datetime]
    creator: Optional[UserRead] = None
    assignee: Optional[UserRead] = None

# ========== 操作日志 ==========
class TaskLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    user_id: int = Field(foreign_key="user.id")
    action: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskLogRead(SQLModel):
    id: int
    task_id: int
    user_id: int
    action: str
    from_status: Optional[str]
    to_status: Optional[str]
    comment: Optional[str]
    created_at: datetime
    user: Optional[UserRead] = None

# ========== 反馈建议 ==========
class FeedbackBase(SQLModel):
    title: str
    description: Optional[str] = Field(default=None)
    category: FeedbackCategory = Field(default=FeedbackCategory.OTHER)
    priority: Optional[Priority] = Field(default=None)
    status: FeedbackStatus = Field(default=FeedbackStatus.PENDING)

class Feedback(FeedbackBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    submitter_id: int = Field(foreign_key="user.id")
    reviewer_id: Optional[int] = Field(default=None, foreign_key="user.id")
    review_comment: Optional[str] = Field(default=None)
    review_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FeedbackCreate(SQLModel):
    title: str
    description: Optional[str] = None
    category: FeedbackCategory = FeedbackCategory.OTHER

class FeedbackReview(SQLModel):
    status: FeedbackStatus
    priority: Optional[Priority] = None
    review_comment: Optional[str] = None

class FeedbackRead(FeedbackBase):
    id: int
    submitter_id: int
    reviewer_id: Optional[int]
    review_comment: Optional[str]
    review_at: Optional[datetime]
    created_at: datetime
    submitter: Optional[UserRead] = None
    reviewer: Optional[UserRead] = None