import os
import io
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, Request, Response, Form, Depends, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.config import settings
from app.db import init_db, get_session
from app.models import User, Passport, Post, Reply, Community, LabelProduct
from app.auth import get_current_user, set_user_cookie, require_role, SESSION_COOKIE_NAME
from seed.seed import run_seed

from app.ai.analyze import analyze_post
from app.ai.audit import audit_reply
from app.ai.summarize import synthesize_final_plan
from app.speech.stt import transcribe_audio
from app.speech.tts import speak

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    run_seed()
    yield

app = FastAPI(title="URFeast", version="1.0.0", lifespan=lifespan)

# Mount upload, static, and tts_cache directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TTS_CACHE_DIR, exist_ok=True)
os.makedirs("app/static", exist_ok=True)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.mount("/tts_cache", StaticFiles(directory=settings.TTS_CACHE_DIR), name="tts_cache")

templates = Jinja2Templates(directory="app/templates")


def _escapejs(value) -> str:
    """Escape text for safe use inside JavaScript single-quoted strings."""
    if value is None:
        return ""
    s = str(value)
    return (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


templates.env.filters["escapejs"] = _escapejs

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "URFeast", "model": settings.GEMMA_MODEL}

# --- AUTH & DEMO LOGIN ---

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    users = session.exec(select(User)).all()
    return templates.TemplateResponse(request, "login.html", {
        "users": users,
        "current_user": current_user
    })

@app.post("/login")
def login_action(response: Response, user_id: int = Form(...), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    redirect = RedirectResponse(url="/", status_code=303)
    set_user_cookie(redirect, user.id)
    return redirect

# --- FEED ---

@app.get("/", response_class=HTMLResponse)
def feed_page(
    request: Request,
    community_id: Optional[int] = None,
    session: Session = Depends(get_session)
):
    current_user = get_current_user(request, session)
    communities = session.exec(select(Community)).all()
    
    query = select(Post).order_by(Post.created_at.desc())
    if community_id:
        query = query.where(Post.community_id == community_id)
    
    posts = session.exec(query).all()
    
    return templates.TemplateResponse(request, "feed.html", {
        "current_user": current_user,
        "communities": communities,
        "posts": posts,
        "active_community_id": community_id
    })

# --- PASSPORT ---

@app.get("/passport", response_class=HTMLResponse)
def passport_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    passport = current_user.passport
    if not passport:
        passport = Passport(user_id=current_user.id)
        session.add(passport)
        session.commit()
        session.refresh(passport)

    return templates.TemplateResponse(request, "passport.html", {
        "current_user": current_user,
        "passport": passport
    })

@app.post("/passport")
def update_passport(
    request: Request,
    diet_type: str = Form("veg"),
    allergies: List[str] = Form(default_factory=list),
    avoid_list_str: str = Form(""),
    goals: List[str] = Form(default_factory=list),
    language: str = Form("en"),
    conditions_note: Optional[str] = Form(None),
    budget_note: Optional[str] = Form(None),
    session: Session = Depends(get_session)
):
    current_user = get_current_user(request, session)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    passport = current_user.passport
    if not passport:
        passport = Passport(user_id=current_user.id)
        session.add(passport)
    
    passport.diet_type = diet_type
    passport.allergies = allergies
    passport.avoid_list = [item.strip().lower() for item in avoid_list_str.split(",") if item.strip()]
    passport.goals = goals
    passport.language = "en"
    passport.conditions_note = conditions_note
    passport.budget_note = budget_note
    
    current_user.language = "en"
    
    session.add(passport)
    session.add(current_user)
    session.commit()
    
    return RedirectResponse(url="/passport", status_code=303)

# --- POST CREATION & DETAIL ---

@app.get("/post/new", response_class=HTMLResponse)
def new_post_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    communities = session.exec(select(Community)).all()
    passport = current_user.passport or Passport(user_id=current_user.id)
    
    return templates.TemplateResponse(request, "post_new.html", {
        "current_user": current_user,
        "communities": communities,
        "passport": passport
    })

@app.post("/post/new")
async def create_post_action(
    request: Request,
    question_text: str = Form(...),
    image_kind: str = Form("meal"),
    community_id: Optional[int] = Form(None),
    voice_transcript: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session)
):
    current_user = get_current_user(request, session)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    image_path = None
    if image and image.filename:
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        unique_name = f"scan_{uuid.uuid4().hex[:8]}{ext}"
        saved_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        content = await image.read()
        with open(saved_path, "wb") as f:
            f.write(content)
        image_path = saved_path

    passport = current_user.passport or Passport(user_id=current_user.id)
    passport_dict = passport.to_dict()

    # Call Gemma 4 Analysis
    analysis_res = analyze_post(
        image_path=image_path,
        question_text=question_text,
        passport_dict=passport_dict,
        language=current_user.language
    )
    analysis_dict = analysis_res.model_dump()

    # Handle Label Library indexing if label photo
    label_prod_id = None
    if analysis_res.label_data and analysis_res.label_data.product_name:
        prod_name = analysis_res.label_data.product_name
        existing_label = session.exec(
            select(LabelProduct).where(LabelProduct.name_guess.ilike(f"%{prod_name}%"))
        ).first()
        
        if existing_label:
            existing_label.scan_count += 1
            session.add(existing_label)
            session.commit()
            label_prod_id = existing_label.id
        else:
            new_prod = LabelProduct(
                name_guess=prod_name,
                label_json_raw=json.dumps(analysis_res.label_data.model_dump()),
                image_path=image_path,
                scanned_by=current_user.id,
                scan_count=1
            )
            session.add(new_prod)
            session.commit()
            session.refresh(new_prod)
            label_prod_id = new_prod.id

    post = Post(
        author_id=current_user.id,
        image_path=image_path,
        image_kind=image_kind,
        question_text=question_text,
        voice_transcript=voice_transcript,
        created_at=datetime.now(timezone.utc),
        community_id=community_id,
        status="answered",
        analysis_json_raw=json.dumps(analysis_dict),
        label_product_id=label_prod_id
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    return RedirectResponse(url=f"/post/{post.id}", status_code=303)

@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail_page(post_id: int, request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return templates.TemplateResponse(request, "post.html", {
        "current_user": current_user,
        "post": post
    })

# --- REPLIES & HYBRID AUDIT ---

@app.post("/post/{post_id}/reply", response_class=HTMLResponse)
def add_reply(
    post_id: int,
    request: Request,
    body: str = Form(...),
    session: Session = Depends(get_session)
):
    current_user = get_current_user(request, session)
    if not current_user:
        raise HTTPException(status_code=401, detail="Must be logged in to reply")
    
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    poster = post.author
    poster_passport = poster.passport.to_dict() if poster and poster.passport else {}
    poster_lang = poster.language if poster else "en"

    # Run Hybrid Safety Audit
    audit_res = audit_reply(
        reply_body=body,
        poster_passport_dict=poster_passport,
        author_role=current_user.role,
        language=poster_lang
    )
    audit_dict = audit_res.model_dump()

    reply = Reply(
        post_id=post.id,
        author_id=current_user.id,
        author_type=current_user.role if current_user.role in ["peer", "dietitian"] else "peer",
        body=body,
        created_at=datetime.now(timezone.utc),
        audit_json_raw=json.dumps(audit_dict),
        audit_status=audit_res.status,
        helpful_votes=0
    )
    session.add(reply)
    session.commit()
    session.refresh(reply)

    return templates.TemplateResponse(request, "partials/reply_item.html", {
        "reply": reply,
        "post": post
    })

@app.post("/post/{post_id}/approve")
def approve_plan(post_id: int, request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    if not current_user or current_user.role not in ["dietitian", "admin"]:
        raise HTTPException(status_code=403, detail="Dietitian permission required")
    
    post = session.get(Post, post_id)
    if post:
        post.status = "dietitian_approved"
        session.add(post)
        session.commit()
    return RedirectResponse(url=f"/post/{post_id}", status_code=303)

@app.post("/post/{post_id}/final_plan", response_class=HTMLResponse)
def generate_final_plan_route(post_id: int, request: Request, session: Session = Depends(get_session)):
    post = session.get(Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    poster = post.author
    passport_dict = poster.passport.to_dict() if poster and poster.passport else {}
    language = poster.language if poster else "en"

    replies_data = []
    for r in post.replies:
        replies_data.append({
            "author_type": r.author_type,
            "body": r.body,
            "audit_status": r.audit_status
        })

    plan_res = synthesize_final_plan(
        question_text=post.question_text,
        passport_dict=passport_dict,
        replies=replies_data,
        language=language
    )

    post.final_plan_json_raw = json.dumps(plan_res.model_dump())
    session.add(post)
    session.commit()

    return templates.TemplateResponse(request, "partials/final_plan_card.html", {
        "post": post
    })

@app.post("/reply/{reply_id}/vote")
def vote_reply(reply_id: int, session: Session = Depends(get_session)):
    reply = session.get(Reply, reply_id)
    if reply:
        reply.helpful_votes += 1
        session.add(reply)
        session.commit()
        return HTMLResponse(content=str(reply.helpful_votes))
    return HTMLResponse(content="0")

# --- LABEL LIBRARY ---

@app.get("/library", response_class=HTMLResponse)
def library_page(request: Request, q: Optional[str] = None, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    query = select(LabelProduct).order_by(LabelProduct.scan_count.desc())
    if q and q.strip():
        query = query.where(LabelProduct.name_guess.ilike(f"%{q.strip()}%"))
    
    products = session.exec(query).all()
    return templates.TemplateResponse(request, "library.html", {
        "current_user": current_user,
        "products": products,
        "query": q
    })

# --- DIETITIAN QUEUE & ADMIN VERIFY ---

@app.get("/dietitian/queue", response_class=HTMLResponse)
def dietitian_queue_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    if not current_user or current_user.role not in ["dietitian", "admin"]:
        return RedirectResponse(url="/login", status_code=303)
    
    posts = session.exec(
        select(Post).where(Post.status != "dietitian_approved").order_by(Post.created_at.desc())
    ).all()

    return templates.TemplateResponse(request, "queue.html", {
        "current_user": current_user,
        "posts": posts
    })

@app.get("/admin/verify", response_class=HTMLResponse)
def admin_verify_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    if not current_user or current_user.role != "admin":
        return RedirectResponse(url="/login", status_code=303)
    
    users = session.exec(select(User)).all()
    return templates.TemplateResponse(request, "verify.html", {
        "current_user": current_user,
        "users": users
    })

@app.post("/admin/verify/toggle")
def toggle_verify_badge(user_id: int = Form(...), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if user:
        user.is_verified = not user.is_verified
        session.add(user)
        session.commit()
    return RedirectResponse(url="/admin/verify", status_code=303)

# --- ABOUT ---

@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request, session: Session = Depends(get_session)):
    current_user = get_current_user(request, session)
    return templates.TemplateResponse(request, "about.html", {
        "current_user": current_user
    })

# --- SPEECH API ENDPOINTS ---

@app.post("/api/stt")
async def speech_to_text_endpoint(audio: UploadFile = File(...)):
    temp_path = os.path.join(settings.UPLOAD_DIR, f"temp_{uuid.uuid4().hex[:8]}.webm")
    content = await audio.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    
    res = transcribe_audio(temp_path)
    
    # Cleanup temp file
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass

    return res

@app.get("/api/tts")
def text_to_speech_endpoint(text: str, lang: str = "en"):
    audio_url = speak(text, lang)
    return {"audio_url": audio_url}
