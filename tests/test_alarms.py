import pytest
from fastapi.testclient import TestClient

from app.database import (
    clear_alarm_records,
    clear_device_records,
)
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_test_data():
    """每条测试执行前后清空告警和设备数据。"""
    clear_alarm_records()
    clear_device_records()
    yield
    clear_alarm_records()
    clear_device_records()


def create_test_device():
    response = client.post(
        "/api/devices",
        json={
            "name": "告警测试摄像机",
            "ip_address": "192.168.1.150",
            "port": 8000,
            "device_type": "网络摄像机",
        },
    )
    return response.json()["id"]


def create_test_alarm(alarm_type="视频信号丢失"):
    device_id = create_test_device()

    return client.post(
        "/api/alarms",
        json={
            "device_id": device_id,
            "alarm_type": alarm_type,
        },
    )


def test_create_alarm_success():
    response = create_test_alarm()

    assert response.status_code == 201

    alarm = response.json()
    assert alarm["id"] == 1
    assert alarm["device_id"] == 1
    assert alarm["device_name"] == "告警测试摄像机"
    assert alarm["alarm_type"] == "视频信号丢失"
    assert alarm["status"] == "新产生"
    assert alarm["handling_note"] == ""
    assert alarm["alarm_time"]


def test_list_alarms():
    device_id = create_test_device()

    client.post(
        "/api/alarms",
        json={
            "device_id": device_id,
            "alarm_type": "视频信号丢失",
        },
    )
    client.post(
        "/api/alarms",
        json={
            "device_id": device_id,
            "alarm_type": "设备离线",
        },
    )

    response = client.get("/api/alarms")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2


def test_get_existing_alarm():
    create_response = create_test_alarm()
    alarm_id = create_response.json()["id"]

    response = client.get(f"/api/alarms/{alarm_id}")

    assert response.status_code == 200
    assert response.json()["id"] == alarm_id
    assert response.json()["alarm_type"] == "视频信号丢失"


def test_get_missing_alarm():
    response = client.get("/api/alarms/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "告警不存在"


def test_reject_alarm_for_missing_device():
    response = client.post(
        "/api/alarms",
        json={
            "device_id": 999,
            "alarm_type": "设备离线",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "设备不存在"


def test_reject_missing_device_id():
    response = client.post(
        "/api/alarms",
        json={
            "alarm_type": "设备离线",
        },
    )

    assert response.status_code == 422


def test_reject_invalid_device_id():
    response = client.post(
        "/api/alarms",
        json={
            "device_id": 0,
            "alarm_type": "设备离线",
        },
    )

    assert response.status_code == 422


def test_reject_empty_alarm_type():
    device_id = create_test_device()

    response = client.post(
        "/api/alarms",
        json={
            "device_id": device_id,
            "alarm_type": "",
        },
    )

    assert response.status_code == 422


def test_filter_alarms_by_status():
    create_test_alarm()

    response = client.get(
        "/api/alarms",
        params={"alarm_status": "新产生"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "新产生"


def test_reject_invalid_alarm_status_filter():
    response = client.get(
        "/api/alarms",
        params={"alarm_status": "未知状态"},
    )

    assert response.status_code == 422

def change_alarm_status(
    alarm_id,
    new_status,
    role="operator",
    handling_note=None,
):
    request_body = {"status": new_status}

    if handling_note is not None:
        request_body["handling_note"] = handling_note

    return client.patch(
        f"/api/alarms/{alarm_id}/status",
        headers={"X-User-Role": role},
        json=request_body,
    )


def test_admin_can_confirm_alarm():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "已确认",
        role="admin",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "已确认"


def test_operator_can_confirm_alarm():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "已确认",
        role="operator",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "已确认"


def test_confirmed_alarm_can_enter_processing():
    alarm_id = create_test_alarm().json()["id"]

    change_alarm_status(alarm_id, "已确认")
    response = change_alarm_status(alarm_id, "处理中")

    assert response.status_code == 200
    assert response.json()["status"] == "处理中"


def test_complete_alarm_lifecycle():
    alarm_id = create_test_alarm().json()["id"]

    change_alarm_status(alarm_id, "已确认")
    change_alarm_status(alarm_id, "处理中")

    response = change_alarm_status(
        alarm_id,
        "已关闭",
        handling_note="已检查网络连接并恢复设备",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "已关闭"
    assert (
        response.json()["handling_note"]
        == "已检查网络连接并恢复设备"
    )


def test_reject_new_alarm_entering_processing():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "处理中",
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "告警不能从新产生直接变为处理中"
    )


def test_reject_new_alarm_closing_directly():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "已关闭",
        handling_note="直接关闭",
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "告警不能从新产生直接变为已关闭"
    )


def test_reject_closing_without_handling_note():
    alarm_id = create_test_alarm().json()["id"]

    change_alarm_status(alarm_id, "已确认")
    change_alarm_status(alarm_id, "处理中")

    response = change_alarm_status(
        alarm_id,
        "已关闭",
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "关闭告警前必须填写处理说明"
    )


def test_reject_closing_with_blank_handling_note():
    alarm_id = create_test_alarm().json()["id"]

    change_alarm_status(alarm_id, "已确认")
    change_alarm_status(alarm_id, "处理中")

    response = change_alarm_status(
        alarm_id,
        "已关闭",
        handling_note="   ",
    )

    assert response.status_code == 400


def test_visitor_cannot_update_alarm():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "已确认",
        role="visitor",
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "仅管理员或操作员可以处理告警"
    )


def test_update_alarm_without_role_header():
    alarm_id = create_test_alarm().json()["id"]

    response = client.patch(
        f"/api/alarms/{alarm_id}/status",
        json={"status": "已确认"},
    )

    assert response.status_code == 422


def test_update_missing_alarm():
    response = change_alarm_status(
        999,
        "已确认",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "告警不存在"


def test_reject_invalid_alarm_status():
    alarm_id = create_test_alarm().json()["id"]

    response = change_alarm_status(
        alarm_id,
        "未知状态",
    )

    assert response.status_code == 422