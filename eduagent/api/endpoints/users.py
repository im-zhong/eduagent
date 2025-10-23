# TODO(YunX): define the user management endpoints and pydantic models

"""
User Management Endpoints

This module provides role-based authentication and user management endpoints:
- Separate login endpoints for students, teachers, and admins
- User registration and profile management
- Session management and token refresh
- Role-based authorization
"""

import uuid

from fastapi import APIRouter
from fastapi_users import FastAPIUsers

from eduagent.user.auth import auth_backend
from eduagent.user.manager import get_user_manager
from eduagent.user.models import User
from eduagent.user.schemas import UserCreate, UserRead, UserUpdate

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# 主路由
router = APIRouter()

# 认证路由 (登录, 登出)
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# 注册路由
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# 密码重置路由
router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)

# 邮箱验证路由
router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

# 用户管理路由
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
