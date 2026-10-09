from typing import Optional
from fastapi import Request, Response, HTTPException, Depends
from sqlmodel import Session, select
from app.db import get_session
from app.models import User, Passport

SESSION_COOKIE_NAME = "urfeast_user_id"

def get_current_user(request: Request, session: Session = Depends(get_session)) -> Optional[User]:
    user_id_str = request.cookies.get(SESSION_COOKIE_NAME)
    if not user_id_str:
        return None

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        return None

    user = session.get(User, user_id)
    if not user:
        return None
    return user

def require_role(roles: list[str]):
    def role_checker(user: Optional[User] = Depends(get_current_user)):
        if not user or user.role not in roles:
            raise HTTPException(status_code=403, detail="Unauthorized access for this role.")
        return user
    return role_checker

def set_user_cookie(response: Response, user_id: int):
    response.set_cookie(key=SESSION_COOKIE_NAME, value=str(user_id), httponly=True, max_age=86400 * 30)
