import os
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# 환경 변수에서 MySQL 데이터베이스 연결 정보를 가져옵니다.
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

# 데이터베이스 URL 생성
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# 데이터베이스 엔진 및 세션 초기화
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    """
    사용자를 나타내는 User 모델 정의.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    full_name = Column(String(100))
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    disabled = Column(Integer, default=0)
    approved = Column(Integer, default=0)
    role = Column(String(50), default="user")
    tokens = relationship("APIToken", back_populates="owner")

class APIToken(Base):
    """
    API 토큰을 나타내는 APIToken 모델 정의.
    """
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    owner = relationship("User", back_populates="tokens")

def create_database():
    """
    데이터베이스 테이블을 생성합니다.
    """
    Base.metadata.create_all(bind=engine)

def get_or_create_user(db: Session, user_data: dict):
    """
    사용자 정보를 바탕으로 사용자 객체를 가져오거나 새로 생성합니다.
    첫 번째 사용자일 경우, 관리자 역할을 부여합니다.
    """
    user = db.query(User).filter(User.username == user_data["login"]).first()
    if user is None:
        # 첫 번째 사용자 여부 확인
        is_first_user = db.query(User).count() == 0
        user = User(
            username=user_data["login"],
            full_name=user_data["name"],
            email=user_data["email"],
            role="admin" if is_first_user else "user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
