import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from app import logic
from app.db import engine, get_db
from app.models import Base


app = FastAPI(title="Luki Memes")


APP_PASSWORD = os.getenv("APP_PASSWORD", "2102")
APP_MASTER_PASSWORD = os.getenv("APP_MASTER_PASSWORD", "vWs%h!fw17X41^RF")
APP_SECRET = os.getenv("APP_SECRET", "CHANGE_ME")
NAME_COOKIE = "lm_name"
AUTH_COOKIE = "lm_auth"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_ROOT = BASE_DIR / "static" / "uploads"
TEMPLATE_DIR = UPLOAD_ROOT / "templates"
MEME_DIR = UPLOAD_ROOT / "memes"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
try:
    templates.env.globals["asset_version"] = int(
        (BASE_DIR / "static" / "styles.css").stat().st_mtime
    )
except FileNotFoundError:
    templates.env.globals["asset_version"] = 1


def build_auth_token(name: str) -> str:
    digest = hmac.new(
        APP_SECRET.encode("utf-8"),
        name.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def get_current_user(request: Request) -> Optional[str]:
    raw_name = request.cookies.get(NAME_COOKIE)
    token = request.cookies.get(AUTH_COOKIE)
    if not raw_name or not token:
        return None
    name = unquote(raw_name)
    if not name:
        return None
    if not hmac.compare_digest(token, build_auth_token(name)):
        return None
    return name


def ensure_upload_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def validate_upload_file(upload: UploadFile) -> Optional[str]:
    if not upload or not upload.filename:
        return "Bitte waehle eine Datei aus."
    extension = os.path.splitext(upload.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return "Bitte nur Bilddateien (jpg, png, gif, webp) hochladen."
    return None


async def save_upload_file(
    upload: UploadFile, destination: Path
) -> tuple[str, Optional[str]]:
    ensure_upload_dir(destination)
    original_name = upload.filename or None
    extension = os.path.splitext(original_name or "")[1].lower()
    filename = f"{hashlib.sha256(os.urandom(16)).hexdigest()}{extension}"
    file_path = destination / filename
    contents = await upload.read()
    with open(file_path, "wb") as handle:
        handle.write(contents)
    return f"uploads/{destination.name}/{filename}", original_name


@app.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    current_user = get_current_user(request)
    if current_user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "name": "",
            "current_user": None,
            "show_header": False,
            "full_bleed": True,
            "title": "Login",
        },
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    name: str = Form(...),
    password: str = Form(...),
):
    clean_name = name.strip()
    if not clean_name:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Bitte gib deinen Namen ein.",
                "name": name,
                "current_user": None,
                "show_header": False,
                "full_bleed": True,
                "title": "Login",
            },
        )
    if password != APP_PASSWORD:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Das Passwort ist falsch.",
                "name": clean_name,
                "current_user": None,
                "show_header": False,
                "full_bleed": True,
                "title": "Login",
            },
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        NAME_COOKIE,
        quote(clean_name),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        AUTH_COOKIE,
        build_auth_token(clean_name),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(NAME_COOKIE)
    response.delete_cookie(AUTH_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse, name="home")
async def home(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    stats = await logic.get_meme_stats(db)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats,
        },
    )


@app.get("/templates", response_class=HTMLResponse, name="templates_list")
async def templates_list(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    templates_list = await logic.list_templates(db)
    items = [
        {
            "id": item.id,
            "title": item.title,
            "uploaded_by": item.uploaded_by,
            "file_url": f"/static/{item.file_path}",
        }
        for item in templates_list
    ]
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Meme Templates",
            "subtitle": "Alle Vorlagen, bereit für neue Ideen.",
            "items": items,
            "is_memes": False,
            "upload_url": "/templates/upload",
            "detail_prefix": "/templates/",
            "empty_hint": "Noch keine Templates hochgeladen.",
        },
    )


@app.get("/templates/upload", response_class=HTMLResponse, name="templates_upload")
async def templates_upload_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Template hochladen",
            "subtitle": "Dein Name wird automatisch gespeichert.",
            "action_url": "/templates/upload",
            "error": None,
        },
    )


@app.post("/templates/upload", response_class=HTMLResponse)
async def templates_upload_submit(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    clean_title = title.strip()
    if not clean_title:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Template hochladen",
                "subtitle": "Dein Name wird automatisch gespeichert.",
                "action_url": "/templates/upload",
                "error": "Bitte gib einen Titel an.",
            },
        )
    upload_error = validate_upload_file(file)
    if upload_error:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Template hochladen",
                "subtitle": "Dein Name wird automatisch gespeichert.",
                "action_url": "/templates/upload",
                "error": upload_error,
            },
        )
    file_path, original_name = await save_upload_file(file, TEMPLATE_DIR)
    await logic.create_template(
        db, clean_title, file_path, original_name, current_user
    )
    return RedirectResponse("/templates", status_code=303)


@app.get("/templates/{template_id}", response_class=HTMLResponse, name="template_detail")
async def template_detail(
    request: Request,
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    item = await logic.get_template(db, template_id)
    if not item:
        return RedirectResponse("/templates", status_code=303)
    context = await build_template_detail_context(
        request, current_user, item, delete_error=None
    )
    return templates.TemplateResponse("detail.html", context)


async def build_template_detail_context(
    request: Request,
    current_user: str,
    item,
    delete_error: Optional[str],
) -> dict:
    return {
        "request": request,
        "current_user": current_user,
        "title": item.title,
        "file_url": f"/static/{item.file_path}",
        "uploaded_by": item.uploaded_by,
        "back_url": "/templates",
        "download_url": f"/static/{item.file_path}",
        "show_reactions": False,
        "show_delete": True,
        "delete_action": f"/templates/{item.id}/delete",
        "delete_error": delete_error,
    }


@app.get("/memes", response_class=HTMLResponse, name="memes_list")
async def memes_list(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    memes_list = await logic.list_memes(db)
    meme_ids = [item.id for item in memes_list]
    reaction_counts = await logic.get_reaction_counts(db, meme_ids)
    user_reactions = await logic.get_user_reactions(db, meme_ids, current_user)
    items = [
        {
            "id": item.id,
            "title": item.title,
            "uploaded_by": item.uploaded_by,
            "file_url": f"/static/{item.file_path}",
            "likes": reaction_counts.get(item.id, {}).get("like", 0),
            "dislikes": reaction_counts.get(item.id, {}).get("dislike", 0),
            "user_reaction": user_reactions.get(item.id),
        }
        for item in memes_list
    ]
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Memes",
            "subtitle": "Hier landen die fertigen Memes.",
            "items": items,
            "is_memes": True,
            "upload_url": "/memes/upload",
            "detail_prefix": "/memes/",
            "empty_hint": "Noch keine Memes hochgeladen.",
        },
    )


@app.get("/memes/upload", response_class=HTMLResponse, name="memes_upload")
async def memes_upload_page(request: Request):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "current_user": current_user,
            "title": "Meme hochladen",
            "subtitle": "Dein Name wird automatisch gespeichert.",
            "action_url": "/memes/upload",
            "error": None,
        },
    )


@app.post("/memes/upload", response_class=HTMLResponse)
async def memes_upload_submit(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    clean_title = title.strip()
    if not clean_title:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Meme hochladen",
                "subtitle": "Dein Name wird automatisch gespeichert.",
                "action_url": "/memes/upload",
                "error": "Bitte gib einen Titel an.",
            },
        )
    upload_error = validate_upload_file(file)
    if upload_error:
        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Meme hochladen",
                "subtitle": "Dein Name wird automatisch gespeichert.",
                "action_url": "/memes/upload",
                "error": upload_error,
            },
        )
    file_path, original_name = await save_upload_file(file, MEME_DIR)
    await logic.create_meme(db, clean_title, file_path, original_name, current_user)
    return RedirectResponse("/memes", status_code=303)


async def build_meme_detail_context(
    request: Request,
    current_user: str,
    item,
    db: AsyncSession,
    delete_error: Optional[str],
) -> dict:
    reaction_counts = await logic.get_reaction_counts(db, [item.id])
    user_reactions = await logic.get_user_reactions(db, [item.id], current_user)
    meme_counts = reaction_counts.get(item.id, {"like": 0, "dislike": 0})
    return {
        "request": request,
        "current_user": current_user,
        "title": item.title,
        "file_url": f"/static/{item.file_path}",
        "uploaded_by": item.uploaded_by,
        "back_url": "/memes",
        "download_url": f"/static/{item.file_path}",
        "show_reactions": True,
        "meme_id": item.id,
        "likes": meme_counts.get("like", 0),
        "dislikes": meme_counts.get("dislike", 0),
        "user_reaction": user_reactions.get(item.id),
        "show_delete": True,
        "delete_action": f"/memes/{item.id}/delete",
        "delete_error": delete_error,
    }


@app.get("/memes/{meme_id}", response_class=HTMLResponse, name="meme_detail")
async def meme_detail(
    request: Request,
    meme_id: int,
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    item = await logic.get_meme(db, meme_id)
    if not item:
        return RedirectResponse("/memes", status_code=303)
    context = await build_meme_detail_context(
        request, current_user, item, db, delete_error=None
    )
    return templates.TemplateResponse("detail.html", context)


@app.post("/memes/{meme_id}/react")
async def meme_react(
    request: Request,
    meme_id: int,
    reaction: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    if reaction not in {"like", "dislike"}:
        return RedirectResponse(f"/memes/{meme_id}", status_code=303)
    item = await logic.get_meme(db, meme_id)
    if not item:
        return RedirectResponse("/memes", status_code=303)
    await logic.set_reaction(db, meme_id, current_user, reaction)
    redirect_target = request.headers.get("referer") or f"/memes/{meme_id}"
    return RedirectResponse(redirect_target, status_code=303)


@app.post("/memes/{meme_id}/delete")
async def meme_delete(
    request: Request,
    meme_id: int,
    master_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    item = await logic.get_meme(db, meme_id)
    if not item:
        return RedirectResponse("/memes", status_code=303)
    if master_password != APP_MASTER_PASSWORD:
        context = await build_meme_detail_context(
            request,
            current_user,
            item,
            db,
            delete_error="Masterpasswort ist falsch.",
        )
        return templates.TemplateResponse("detail.html", context)
    file_path = BASE_DIR / "static" / item.file_path
    await logic.delete_meme(db, meme_id)
    try:
        file_path.unlink()
    except FileNotFoundError:
        pass
    return RedirectResponse("/memes", status_code=303)


@app.post("/templates/{template_id}/delete")
async def template_delete(
    request: Request,
    template_id: int,
    master_password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    item = await logic.get_template(db, template_id)
    if not item:
        return RedirectResponse("/templates", status_code=303)
    if master_password != APP_MASTER_PASSWORD:
        context = await build_template_detail_context(
            request,
            current_user,
            item,
            delete_error="Masterpasswort ist falsch.",
        )
        return templates.TemplateResponse("detail.html", context)
    file_path = BASE_DIR / "static" / item.file_path
    await logic.delete_template(db, template_id)
    try:
        file_path.unlink()
    except FileNotFoundError:
        pass
    return RedirectResponse("/templates", status_code=303)


@app.get("/slideshow", response_class=HTMLResponse, name="slideshow")
async def slideshow(request: Request, db: AsyncSession = Depends(get_db)):
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=303)
    memes_list = await logic.list_memes(db)
    entries = [
        {
            "url": f"/static/{item.file_path}",
            "title": item.title,
            "uploaded_by": item.uploaded_by,
        }
        for item in memes_list
    ]
    return templates.TemplateResponse(
        "slideshow.html",
        {
            "request": request,
            "current_user": current_user,
            "memes_json": json.dumps(entries),
        },
    )
