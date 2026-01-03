import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Depends
from fastapi_users import FastAPIUsers, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.manager import BaseUserManager, UUIDIDMixin
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User


SECRET = os.getenv("SECRET", "CHANGE_ME")


class UserRead(schemas.BaseUser[uuid.UUID]):
    full_name: str
    created_at: Optional[datetime] = None


class UserCreate(schemas.BaseUserCreate):
    full_name: str


class UserUpdate(schemas.BaseUserUpdate):
    full_name: Optional[str] = None


cookie_transport = CookieTransport(
    cookie_name="client_template_auth",
    cookie_max_age=60 * 60 * 24 * 7,  # 1 Woche
    cookie_secure=False,
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=60 * 60 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
optional_current_user = fastapi_users.current_user(optional=True)
