import pytest
from fastapi.testclient import TestClient

from app.main import DEVICES, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_device_store():
    """每条测试执行前后清空设备数据。"""
    DEVICES.clear()
    yield
    DEVICES.clear()


def valid_device(
    name="实验室摄像机01",
    ip_address="192.168.1.101",
    port=8000,
    device_type="网络摄像机",
):
    return {
        "name": name,
        "ip_address": ip_address,
        "port": port,
        "device_type": device_type,
    }


def test_create_device_success():
    response = client.post(
        "/api/devices",
        json=valid_device(),
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "name": "实验室摄像机01",
        "ip_address": "192.168.1.101",
        "port": 8000,
        "device_type": "网络摄像机",
        "status": "离线",
    }


def test_list_devices():
    client.post(
        "/api/devices",
        json=valid_device(),
    )
    client.post(
        "/api/devices",
        json=valid_device(
            name="实验室摄像机02",
            ip_address="192.168.1.102",
            port=8000,
        ),
    )

    response = client.get("/api/devices")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 2


def test_get_existing_device():
    create_response = client.post(
        "/api/devices",
        json=valid_device(),
    )
    device_id = create_response.json()["id"]

    response = client.get(f"/api/devices/{device_id}")

    assert response.status_code == 200
    assert response.json()["id"] == device_id
    assert response.json()["name"] == "实验室摄像机01"


def test_get_missing_device():
    response = client.get("/api/devices/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "设备不存在"


def test_reject_duplicate_ip_and_port():
    device = valid_device()

    first_response = client.post(
        "/api/devices",
        json=device,
    )
    second_response = client.post(
        "/api/devices",
        json=device,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert (
        second_response.json()["detail"]
        == "相同IP地址和端口的设备已存在"
    )


def test_allow_same_ip_with_different_port():
    first_response = client.post(
        "/api/devices",
        json=valid_device(port=8000),
    )
    second_response = client.post(
        "/api/devices",
        json=valid_device(
            name="实验室摄像机02",
            port=8001,
        ),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


@pytest.mark.parametrize(
    "invalid_port",
    [
        0,
        -1,
        65536,
        "abc",
    ],
)
def test_reject_invalid_port(invalid_port):
    device = valid_device()
    device["port"] = invalid_port

    response = client.post(
        "/api/devices",
        json=device,
    )

    assert response.status_code == 422


def test_reject_missing_port():
    device = valid_device()
    del device["port"]

    response = client.post(
        "/api/devices",
        json=device,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "invalid_ip",
    [
        "192.168.1",
        "256.1.1.1",
        "abc.def.com",
        "",
    ],
)
def test_reject_invalid_ip(invalid_ip):
    device = valid_device()
    device["ip_address"] = invalid_ip

    response = client.post(
        "/api/devices",
        json=device,
    )

    assert response.status_code == 422


def test_reject_empty_device_name():
    device = valid_device()
    device["name"] = ""

    response = client.post(
        "/api/devices",
        json=device,
    )

    assert response.status_code == 422


def test_use_default_device_type():
    device = valid_device()
    del device["device_type"]

    response = client.post(
        "/api/devices",
        json=device,
    )

    assert response.status_code == 201
    assert response.json()["device_type"] == "网络摄像机"