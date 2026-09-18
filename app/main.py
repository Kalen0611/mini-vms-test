from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, IPvAnyAddress
from app.database import (
    DuplicateDeviceError,
    create_device_record,
    delete_device_record,
    get_device_record,
    init_database,
    list_device_records,
    update_device_record,
    update_device_status_record,
    AlarmDeviceNotFoundError,
    create_alarm_record,
    get_alarm_record,
    list_alarm_records,
    update_alarm_status_record,
)

init_database()

app = FastAPI(
    title="MiniVMS API",
    description="智能视频设备管理与告警平台测试项目",
    version="0.3.0",
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


def require_admin(x_user_role: str = Header(...)):
    if x_user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可以执行此操作",
        )

    return x_user_role

@app.get("/")
def read_root():
    return {
        "application": "MiniVMS",
        "version": "0.3.0",
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

class DeviceUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    ip_address: IPvAnyAddress | None = None
    port: int | None = Field(
        default=None,
        ge=1,
        le=65535,
    )
    device_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
    )

AlarmStatus = Literal[
    "新产生",
    "已确认",
    "处理中",
    "已关闭",
]


class AlarmCreate(BaseModel):
    device_id: int = Field(
        gt=0,
        description="产生告警的设备编号",
    )
    alarm_type: str = Field(
        min_length=1,
        max_length=50,
        description="告警类型",
    )

class AlarmStatusUpdate(BaseModel):
    status: AlarmStatus
    handling_note: str | None = Field(
        default=None,
        max_length=500,
        description="处理说明",
    )


ALARM_STATUS_TRANSITIONS = {
    "新产生": "已确认",
    "已确认": "处理中",
    "处理中": "已关闭",
}


def require_alarm_handler(x_user_role: str = Header(...)):
    if x_user_role not in {"admin", "operator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员或操作员可以处理告警",
        )

    return x_user_role

@app.post(
    "/api/devices",
    status_code=status.HTTP_201_CREATED,
)
def create_device(device: DeviceCreate):
    device_data = device.model_dump(mode="json")

    try:
        return create_device_record(device_data)
    except DuplicateDeviceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="相同IP地址和端口的设备已存在",
        )


@app.get("/api/devices")
def list_devices(device_status: DeviceStatus | None = None):
    devices = list_device_records(device_status)

    return {
        "total": len(devices),
        "items": devices,
    }


@app.patch("/api/devices/{device_id}/status")
def update_device_status(
    device_id: int,
    status_update: DeviceStatusUpdate,
):
    device = update_device_status_record(
        device_id,
        status_update.status,
    )

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在",
        )

    return device


@app.patch("/api/devices/{device_id}")
def update_device(
    device_id: int,
    update_data: DeviceUpdate,
    admin_role: str = Depends(require_admin),
):
    if get_device_record(device_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在",
        )

    updates = update_data.model_dump(
        mode="json",
        exclude_unset=True,
        exclude_none=True,
    )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少提供一个需要修改的字段",
        )

    try:
        return update_device_record(device_id, updates)
    except DuplicateDeviceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="相同IP地址和端口的设备已存在",
        )


@app.delete("/api/devices/{device_id}")
def delete_device(
    device_id: int,
    admin_role: str = Depends(require_admin),
):
    deleted_device = delete_device_record(device_id)

    if deleted_device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在",
        )

    return {
        "success": True,
        "message": "设备删除成功",
        "device": deleted_device,
    }


@app.get("/api/devices/{device_id}")
def get_device(device_id: int):
    device = get_device_record(device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在",
        )

    return device

@app.post(
    "/api/alarms",
    status_code=status.HTTP_201_CREATED,
)
def create_alarm(alarm: AlarmCreate):
    alarm_data = alarm.model_dump()

    try:
        return create_alarm_record(alarm_data)
    except AlarmDeviceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在",
        )


@app.get("/api/alarms")
def list_alarms(alarm_status: AlarmStatus | None = None):
    alarms = list_alarm_records(alarm_status)

    return {
        "total": len(alarms),
        "items": alarms,
    }

@app.patch("/api/alarms/{alarm_id}/status")
def update_alarm_status(
    alarm_id: int,
    status_update: AlarmStatusUpdate,
    user_role: str = Depends(require_alarm_handler),
):
    alarm = get_alarm_record(alarm_id)

    if alarm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警不存在",
        )

    expected_status = ALARM_STATUS_TRANSITIONS.get(
        alarm["status"]
    )

    if status_update.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"告警不能从{alarm['status']}"
                f"直接变为{status_update.status}"
            ),
        )

    if (
        status_update.status == "已关闭"
        and (
            status_update.handling_note is None
            or not status_update.handling_note.strip()
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="关闭告警前必须填写处理说明",
        )

    return update_alarm_status_record(
        alarm_id,
        status_update.status,
        status_update.handling_note,
    )


@app.get("/api/alarms/{alarm_id}")
def get_alarm(alarm_id: int):
    alarm = get_alarm_record(alarm_id)

    if alarm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="告警不存在",
        )

    return alarm