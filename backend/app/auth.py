import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import User

router = APIRouter(prefix="/auth")
settings = get_settings()
signer = URLSafeTimedSerializer(settings.session_secret)
COOKIE = "repolens_session"


def current_user(request: Request, db: Session = Depends(get_db)):
    try:
        user_id = signer.loads(request.cookies.get(COOKIE, ""), salt="session", max_age=604800)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Faça login para continuar.")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(401, "Sessão inválida.")
    return user


def login_response(user):
    response = RedirectResponse(settings.frontend_url, status_code=303)
    response.set_cookie(
        COOKIE,
        signer.dumps(user.id, salt="session"),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=604800,
    )
    return response


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "login": user.login, "avatar_url": user.avatar_url}


@router.post("/demo")
def demo(db: Session = Depends(get_db)):
    if not settings.allow_demo_login or settings.analysis_mode != "demo":
        raise HTTPException(403, "Login de demonstração desabilitado.")
    # Cada visitante recebe uma identidade isolada, sem conta de demonstração compartilhada.
    user = User(github_id="demo-" + secrets.token_hex(16), login="Visitante demo")
    db.add(user)
    db.commit()
    response = login_response(user)
    response.status_code = 200
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(settings.frontend_url, status_code=303)
    response.delete_cookie(COOKIE, secure=settings.cookie_secure, httponly=True, samesite="lax")
    response.status_code = 200
    return response


@router.get("/github")
def github():
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(503, "Configure o OAuth App do GitHub no servidor.")
    state = secrets.token_urlsafe(32)
    url = httpx.URL(
        "https://github.com/login/oauth/authorize",
        params={
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_callback_url,
            "state": state,
        },
    )
    response = RedirectResponse(str(url))
    response.set_cookie(
        "oauth_state",
        signer.dumps(state, salt="oauth"),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=600,
    )
    return response


@router.get("/github/callback")
def callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    try:
        expected = signer.loads(request.cookies.get("oauth_state", ""), salt="oauth", max_age=600)
    except (BadSignature, SignatureExpired):
        raise HTTPException(400, "Estado OAuth inválido ou expirado.")
    if not secrets.compare_digest(expected, state):
        raise HTTPException(400, "Estado OAuth inválido.")
    try:
        with httpx.Client(timeout=20) as client:
            token_response = client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                json={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_callback_url,
                },
            )
            token_response.raise_for_status()
            token = token_response.json().get("access_token")
            if not token:
                raise HTTPException(400, "GitHub recusou a autenticação.")
            profile = client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {token}"})
            profile.raise_for_status()
            data = profile.json()
    except httpx.HTTPError:
        raise HTTPException(502, "GitHub indisponível. Tente novamente.")
    user = db.scalar(select(User).where(User.github_id == str(data["id"])))
    if not user:
        user = User(github_id=str(data["id"]), login=data["login"], avatar_url=data.get("avatar_url", ""))
        db.add(user)
    db.commit()
    response = login_response(user)
    response.delete_cookie("oauth_state")
    return response
