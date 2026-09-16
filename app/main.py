from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, IPvAnyAddress


app = FastAPI(
    title="MiniVMS API",
    description="智能视频设备管理与告警平台测试项目",
    version="0.1.1",
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
DEVICES: list[dict] = []


@app.get("/")
def read_root():
    return {
        "application": "MiniVMS",
        "version": "0.1.1",
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
DeviceStatus = Literal["在线", "离线", "故障"]
class DeviceCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
        description="设备名称",
    )
    ip_address: IPvAnyAddress
    port: int = Field(
        ge=1,
        le=65535,
        description="设备端口",
    )
    device_type: str = Field(
        default="网络摄像机",
        min_length=1,
        max_length=30,
        description="设备类型",
    )
class DeviceStatusUpdate(BaseModel):
    status: DeviceStatus

@app.post(
    "/api/devices",
    status_code=status.HTTP_201_CREATED,
)
def create_device(device: DeviceCreate):
    device_data = device.model_dump(mode="json")

    duplicate_device = any(
    existing_device["ip_address"] == device_data["ip_address"]
    and existing_device["port"] == device_data["port"]
    for existing_device in DEVICES
)

    if duplicate_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="相同IP地址和端口的设备已存在",
        )

    new_device = {
    "id": len(DEVICES) + 1,
    "name": device_data["name"],
    "ip_address": device_data["ip_address"],
    "port": device_data["port"],
    "device_type": device_data["device_type"],
    "status": "离线",
}

    DEVICES.append(new_device)
    return new_device


@app.get("/api/devices")
def list_devices(device_status: DeviceStatus | None = None):
    if device_status is None:
        filtered_devices = DEVICES
    else:
        filtered_devices = [
            device
            for device in DEVICES
            if device["status"] == device_status
        ]

    return {
        "total": len(filtered_devices),
        "items": filtered_devices,
    }

@app.patch("/api/devices/{device_id}/status")
def update_device_status(
    device_id: int,
    status_update: DeviceStatusUpdate,
):
    for device in DEVICES:
        if device["id"] == device_id:
            device["status"] = status_update.status
            return device

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="设备不存在",
    )

@app.get("/api/devices/{device_id}")
def get_device(device_id: int):
    for device in DEVICES:
        if device["id"] == device_id:
            return device

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="设备不存在",
    )