import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent.parent / "minivms.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                port INTEGER NOT NULL CHECK (port BETWEEN 1 AND 65535),
                device_type TEXT NOT NULL DEFAULT '网络摄像机',
                status TEXT NOT NULL DEFAULT '离线'
                    CHECK (status IN ('在线', '离线', '故障')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (ip_address, port)
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

DEVICE_SELECT_SQL = """
    SELECT id, name, ip_address, port, device_type, status
    FROM devices
"""


class DuplicateDeviceError(Exception):
    """设备IP地址和端口重复。"""


def device_row_to_dict(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "ip_address": row["ip_address"],
        "port": row["port"],
        "device_type": row["device_type"],
        "status": row["status"],
    }


def create_device_record(device_data):
    connection = get_connection()

    try:
        try:
            cursor = connection.execute(
                """
                INSERT INTO devices (
                    name,
                    ip_address,
                    port,
                    device_type,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    device_data["name"],
                    device_data["ip_address"],
                    device_data["port"],
                    device_data["device_type"],
                    "离线",
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise DuplicateDeviceError from error

        row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return device_row_to_dict(row)
    finally:
        connection.close()


def list_device_records(device_status=None):
    connection = get_connection()

    try:
        if device_status is None:
            rows = connection.execute(
                DEVICE_SELECT_SQL + " ORDER BY id"
            ).fetchall()
        else:
            rows = connection.execute(
                DEVICE_SELECT_SQL
                + " WHERE status = ? ORDER BY id",
                (device_status,),
            ).fetchall()

        return [device_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def get_device_record(device_id):
    connection = get_connection()

    try:
        row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (device_id,),
        ).fetchone()

        return device_row_to_dict(row)
    finally:
        connection.close()


def clear_device_records():
    """仅供自动化测试清空设备数据。"""
    connection = get_connection()

    try:
        connection.execute("DELETE FROM devices")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'devices'"
        )
        connection.commit()
    finally:
        connection.close()

def update_device_status_record(device_id, new_status):
    connection = get_connection()

    try:
        cursor = connection.execute(
            """
            UPDATE devices
            SET status = ?
            WHERE id = ?
            """,
            (new_status, device_id),
        )

        if cursor.rowcount == 0:
            return None

        connection.commit()

        row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (device_id,),
        ).fetchone()

        return device_row_to_dict(row)
    finally:
        connection.close()


def update_device_record(device_id, updates):
    connection = get_connection()

    try:
        current_row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (device_id,),
        ).fetchone()

        if current_row is None:
            return None

        allowed_fields = (
            "name",
            "ip_address",
            "port",
            "device_type",
        )

        filtered_updates = {
            field: updates[field]
            for field in allowed_fields
            if field in updates
        }

        assignments = ", ".join(
            f"{field} = ?"
            for field in filtered_updates
        )
        values = list(filtered_updates.values())
        values.append(device_id)

        try:
            connection.execute(
                f"""
                UPDATE devices
                SET {assignments}
                WHERE id = ?
                """,
                values,
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            raise DuplicateDeviceError from error

        updated_row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (device_id,),
        ).fetchone()

        return device_row_to_dict(updated_row)
    finally:
        connection.close()


def delete_device_record(device_id):
    connection = get_connection()

    try:
        row = connection.execute(
            DEVICE_SELECT_SQL + " WHERE id = ?",
            (device_id,),
        ).fetchone()

        if row is None:
            return None

        deleted_device = device_row_to_dict(row)

        connection.execute(
            "DELETE FROM devices WHERE id = ?",
            (device_id,),
        )
        connection.commit()

        return deleted_device
    finally:
        connection.close()