from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from app import logic
from app.db import engine, get_db
from app.models import Base
from app.users import (
    UserCreate,
    UserRead,
    UserUpdate,
    auth_backend,
    current_active_user,
    fastapi_users,
    optional_current_user,
)


app = FastAPI(title="Client App Template mit FastAPI Users")


@app.on_event("startup")
async def on_startup() -> None:
    # Tabellen anlegen ohne extra Migrations-Tooling
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Static & Templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API-Router von fastapi-users
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
)


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(optional_current_user),
):
    users = await logic.list_users(db)
    stats = await logic.get_portal_stats(db)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "users": users, "stats": stats, "user": user},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(current_active_user),
):
    users = await logic.list_users(db, limit=12)
    stats = await logic.get_portal_stats(db)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "users": users,
            "stats": stats,
            "user": user,
            "show_dashboard": True,
        },
    )
