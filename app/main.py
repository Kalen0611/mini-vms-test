from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="MiniVMS API",
    description="智能视频设备管理与告警平台测试项目",
    version="0.1.0",
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名不能为空")
    password: str = Field(min_length=1, description="密码不能为空")


USERS = {
    "admin": {
        "password": "admin123",
        "role": "管理员",
    },
    "operator": {
        "password": "operator123",
        "role": "操作员",
    },
    "visitor": {
        "password": "visitor123",
        "role": "访客",
    },
}


@app.get("/")
def read_root():
    return {
        "application": "MiniVMS",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


@app.post("/api/login")
def login(login_data: LoginRequest):
    user = USERS.get(login_data.username)

    if user is None or user["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    return {
        "success": True,
        "username": login_data.username,
        "role": user["role"],
        "message": "登录成功",
    }