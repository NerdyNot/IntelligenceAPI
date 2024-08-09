import os
import httpx
import logging
from fastapi import FastAPI, Depends, HTTPException, Query, Request, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.utils.jwt import create_access_token, verify_jwt_token
from app.utils.db import create_database, SessionLocal, User, APIToken, get_or_create_user
from pydantic import BaseModel
from datetime import timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

app = FastAPI(
    title="Intelligence Auth API",
    description="This API provides IntelligenceAPI authentication services.",
    version="0.1.0",
    openapi_version="3.0.0"
)

security = HTTPBearer()

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    """
    데이터베이스 세션을 생성하고 반환합니다.
    요청이 완료되면 세션을 닫습니다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def on_startup():
    """
    애플리케이션 시작 시 데이터베이스를 생성합니다.
    """
    create_database()

@app.get("/")
async def read_root():
    """
    루트 엔드포인트, 환영 메시지를 반환합니다.
    """
    return {"message": "Welcome to the Auth Service, please login with GitHub. /auth/login"}

@app.get("/login")
async def login_with_github():
    """
    GitHub로 리디렉션하여 로그인합니다.
    """
    return RedirectResponse(url=f"{GITHUB_OAUTH_URL}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=read:user")

@app.get("/callback")
async def github_callback(request: Request, code: str = Query(None), db: Session = Depends(get_db)):
    """
    GitHub OAuth 콜백 엔드포인트.
    GitHub로부터 받은 인증 코드를 이용하여 액세스 토큰을 요청하고, 사용자 정보를 받아 JWT 토큰을 생성합니다.
    """
    logger.info(f"Received code: {code}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code parameter")

    async with httpx.AsyncClient() as client:
        response = await client.post(GITHUB_TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI
        }, headers={"Accept": "application/json"})

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail=f"Failed to retrieve access token: {token_data}")

        user_response = await client.get(GITHUB_USER_URL, headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        })

        user_data = user_response.json()

        if not user_data:
            raise HTTPException(status_code=400, detail=f"Failed to retrieve user information: {user_response.text}")

        user = get_or_create_user(db, user_data)
        jwt_token = create_access_token(data={"sub": user.username})
        logger.info(f"Generated JWT Token: {jwt_token}")
        
        response = RedirectResponse(url=f"/auth/welcome")
        response.set_cookie(key="access_token", value=jwt_token, httponly=True)
        return response

@app.get("/welcome", response_class=HTMLResponse)
async def welcome_page(request: Request, access_token: str = Cookie(None), db: Session = Depends(get_db)):
    """
    환영 페이지를 표시하고, 사용자가 관리자일 경우 사용자 관리 기능을 제공합니다.
    """
    try:
        if not access_token:
            raise HTTPException(status_code=403, detail="Not authenticated")
        
        payload = verify_jwt_token(access_token)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.username == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        is_admin_user = is_admin(user)
        users_rows = ""
        if is_admin_user:
            users = db.query(User).all()
            users_rows = ''.join([
                f"<tr><td>{u.username}</td><td>{u.full_name}</td><td>{u.email}</td>"
                f"<td><select onchange='updateApproval(this, \"{u.username}\")'>"
                f"<option value='0' {'selected' if u.approved == 0 else ''}>No</option>"
                f"<option value='1' {'selected' if u.approved == 1 else ''}>Yes</option>"
                f"</select></td>"
                f"<td><select onchange='updateDisable(this, \"{u.username}\")'>"
                f"<option value='0' {'selected' if u.disabled == 0 else ''}>No</option>"
                f"<option value='1' {'selected' if u.disabled == 1 else ''}>Yes</option>"
                f"</select></td>"
                f"<td><select onchange='changeRole(this, \"{u.username}\")'>"
                f"<option value='user' {'selected' if u.role == 'user' else ''}>User</option>"
                f"<option value='admin' {'selected' if u.role == 'admin' else ''}>Admin</option>"
                f"</select></td></tr>"
                for u in users
            ])

        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Welcome</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background-color: #f4f4f4;
                }}
                .container {{
                    text-align: center;
                    background: white;
                    padding: 2em;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }}
                .token {{
                    font-family: monospace;
                    color: #333;
                    background: #eee;
                    padding: 0.5em;
                    border-radius: 5px;
                    display: inline-block;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 2em;
                }}
                th, td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                }}
                th {{
                    background-color: #f4f4f4;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome, {user.full_name}</h1>
                <p>Username: {user.username}</p>
                <p>Email: {user.email}</p>
                <label for="expires_in">Token Expiration Time (minutes):</label>
                <input type="number" id="expires_in" name="expires_in" min="1">
                <button onclick="confirmGenerateToken()">Generate API Token</button>
                <p class="token" id="token"></p>
                <p id="message"></p>
                <p>Copy and use this token for API requests.</p>
                {"<h2>Admin User Management</h2><table><thead><tr><th>Username</th><th>Full Name</th><th>Email</th><th>Approved</th><th>Disabled</th><th>Role</th></tr></thead><tbody>" + users_rows + "</tbody></table>" if is_admin_user else ""}
            </div>
            <script>
                function confirmGenerateToken() {{
                    const confirmed = confirm("Existing tokens will be deleted and a new token will be issued. Do you want to proceed?");
                    if (confirmed) {{
                        generateToken();
                    }}
                }}
                
                async function generateToken() {{
                    const expires_in = document.getElementById('expires_in').value;
                    const url = expires_in ? `/auth/generate_token?expires_in=${{expires_in}}` : '/auth/generate_token';
                    const response = await fetch(url, {{
                        method: 'GET',
                        headers: {{
                            'Authorization': 'Bearer {access_token}'
                        }}
                    }});
                    const data = await response.json();
                    if (data.access_token) {{
                        document.getElementById('token').textContent = data.access_token;
                    }} else {{
                        document.getElementById('token').textContent = '';
                        document.getElementById('message').textContent = data.detail || 'Failed to generate token';
                    }}
                }}
                async function updateApproval(select, username) {{
                    const approved = select.value;
                    const response = await fetch(`/auth/admin/approve_user?username=${{username}}&approved=${{approved}}`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer {access_token}'
                        }}
                    }});
                    if (!response.ok) {{
                        alert('Failed to update approval status');
                    }}
                }}
                async function updateDisable(select, username) {{
                    const disabled = select.value;
                    const response = await fetch(`/auth/admin/disable_user?username=${{username}}&disabled=${{disabled}}`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer {access_token}'
                        }}
                    }});
                    if (!response.ok) {{
                        alert('Failed to update disabled status');
                    }}
                }}
                async function changeRole(select, username) {{
                    const role = select.value;
                    const response = await fetch(`/auth/admin/change_role?username=${{username}}&role=${{role}}`, {{
                        method: 'POST',
                        headers: {{
                            'Authorization': 'Bearer {access_token}'
                        }}
                    }});
                    if (!response.ok) {{
                        alert('Failed to change user role');
                    }}
                }}
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error in /auth/welcome: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/generate_token", response_model=Token)
async def generate_token(
    expires_in: Optional[int] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    사용자에게 새로운 API 토큰을 생성하여 반환합니다.
    """
    try:
        token = credentials.credentials
        payload = verify_jwt_token(token)
        user_id = payload.get("sub")

        user = db.query(User).filter(User.username == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.disabled == 1:
            raise HTTPException(status_code=403, detail="User is disabled")

        if user.approved == 0:
            raise HTTPException(status_code=403, detail="User is not approved. Please contact the administrator.")

        existing_tokens = db.query(APIToken).filter(APIToken.user_id == user.id).all()
        for existing_token in existing_tokens:
            db.delete(existing_token)
        db.commit()

        expires_delta = None
        if expires_in:
            expires_delta = timedelta(minutes=expires_in)

        api_token = create_access_token(data={"sub": user.username}, expires_delta=expires_delta)

        while db.query(APIToken).filter(APIToken.token == api_token).first() is not None:
            api_token = create_access_token(data={"sub": user.username}, expires_delta=expires_delta)

        db_token = APIToken(token=api_token, owner=user)
        db.add(db_token)
        db.commit()
        db.refresh(db_token)

        return {"access_token": api_token, "token_type": "bearer"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in /generate_token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    JWT 토큰을 검증합니다.
    """
    token = credentials.credentials
    try:
        verify_jwt_token(token)
        return {"detail": "Token is valid"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

def is_admin(user: User) -> bool:
    """
    사용자가 관리자인지 확인합니다.
    """
    return user.role == "admin"

@app.post("/admin/approve_user")
async def approve_user(username: str, approved: int, db: Session = Depends(get_db), access_token: str = Cookie(None)):
    """
    사용자의 승인 상태를 업데이트합니다.
    """
    try:
        if not access_token:
            raise HTTPException(status_code=403, detail="Not authenticated")

        payload = verify_jwt_token(access_token)
        admin_user_id = payload.get("sub")

        admin_user = db.query(User).filter(User.username == admin_user_id).first()
        if not admin_user or not is_admin(admin_user):
            raise HTTPException(status_code=403, detail="Access forbidden")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.approved = approved
        db.commit()
        return {"detail": "User approval status updated"}
    except Exception as e:
        logger.error(f"Error in /admin/approve_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/admin/disable_user")
async def disable_user(username: str, disabled: int, db: Session = Depends(get_db), access_token: str = Cookie(None)):
    """
    사용자의 비활성화 상태를 업데이트합니다.
    """
    try:
        if not access_token:
            raise HTTPException(status_code=403, detail="Not authenticated")

        payload = verify_jwt_token(access_token)
        admin_user_id = payload.get("sub")

        admin_user = db.query(User).filter(User.username == admin_user_id).first()
        if not admin_user or not is_admin(admin_user):
            raise HTTPException(status_code=403, detail="Access forbidden")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.disabled = disabled
        db.commit()
        return {"detail": "User disabled status updated"}
    except Exception as e:
        logger.error(f"Error in /admin/disable_user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
@app.post("/admin/change_role")
async def change_role(username: str, role: str, db: Session = Depends(get_db), access_token: str = Cookie(None)):
    """
    사용자의 역할을 변경합니다.
    """
    try:
        if not access_token:
            raise HTTPException(status_code=403, detail="Not authenticated")

        payload = verify_jwt_token(access_token)
        admin_user_id = payload.get("sub")

        admin_user = db.query(User).filter(User.username == admin_user_id).first()
        if not admin_user or not is_admin(admin_user):
            raise HTTPException(status_code=403, detail="Access forbidden")

        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")

        user.role = role
        db.commit()
        return {"detail": "User role updated"}
    except Exception as e:
        logger.error(f"Error in /admin/change_role: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
