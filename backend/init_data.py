#!/usr/bin/env python3
"""初始化数据：创建管理员账号"""
import sys
from app.database import init_db, get_session
from app.crud import create_user, get_user_by_username
from app.models import UserCreate, UserRole

def main():
    init_db()
    db = next(get_session())
    if not get_user_by_username(db, "admin"):
        create_user(db, UserCreate(
            username="admin",
            password="admin123",
            display_name="系统管理员",
            role=UserRole.ADMIN,
        ))
        print("管理员账号已创建: admin / admin123")
    else:
        print("管理员账号已存在")

    # 示例员工
    for u in [
        {"username":"zhangsan","password":"123456","display_name":"张三","department":"研发部"},
        {"username":"lisi","password":"123456","display_name":"李四","department":"研发部"},
        {"username":"wangwu","password":"123456","display_name":"王五","department":"测试部"},
    ]:
        if not get_user_by_username(db, u["username"]):
            create_user(db, UserCreate(
                username=u["username"],
                password=u["password"],
                display_name=u["display_name"],
                role=UserRole.USER,
                department=u["department"],
            ))
            print(f"员工账号已创建: {u['username']} / {u['password']}")
        else:
            print(f"员工账号已存在: {u['username']}")

if __name__ == "__main__":
    main()