import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent.parent / "minivms.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER NOT NULL,
                alarm_type TEXT NOT NULL,
                alarm_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT '新产生'
                    CHECK (
                        status IN (
                            '新产生',
                            '已确认',
                            '处理中',
                            '已关闭'
                        )
                    ),
                handling_note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (device_id)
                    REFERENCES devices(id)
                    ON DELETE CASCADE
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

ALARM_SELECT_SQL = """
    SELECT
        alarms.id,
        alarms.device_id,
        devices.name AS device_name,
        alarms.alarm_type,
        alarms.alarm_time,
        alarms.status,
        alarms.handling_note
    FROM alarms
    JOIN devices
        ON devices.id = alarms.device_id
"""


class AlarmDeviceNotFoundError(Exception):
    """创建告警时指定的设备不存在。"""


def alarm_row_to_dict(row):
    if row is None:
        return None

    return {
        "id": row["id"],
        "device_id": row["device_id"],
        "device_name": row["device_name"],
        "alarm_type": row["alarm_type"],
        "alarm_time": row["alarm_time"],
        "status": row["status"],
        "handling_note": row["handling_note"],
    }


def create_alarm_record(alarm_data):
    connection = get_connection()

    try:
        device = connection.execute(
            "SELECT id FROM devices WHERE id = ?",
            (alarm_data["device_id"],),
        ).fetchone()

        if device is None:
            raise AlarmDeviceNotFoundError

        cursor = connection.execute(
            """
            INSERT INTO alarms (
                device_id,
                alarm_type
            )
            VALUES (?, ?)
            """,
            (
                alarm_data["device_id"],
                alarm_data["alarm_type"],
            ),
        )
        connection.commit()

        row = connection.execute(
            ALARM_SELECT_SQL + " WHERE alarms.id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return alarm_row_to_dict(row)
    finally:
        connection.close()


def list_alarm_records(alarm_status=None):
    connection = get_connection()

    try:
        if alarm_status is None:
            rows = connection.execute(
                ALARM_SELECT_SQL
                + " ORDER BY alarms.id DESC"
            ).fetchall()
        else:
            rows = connection.execute(
                ALARM_SELECT_SQL
                + " WHERE alarms.status = ?"
                + " ORDER BY alarms.id DESC",
                (alarm_status,),
            ).fetchall()

        return [alarm_row_to_dict(row) for row in rows]
    finally:
        connection.close()


def get_alarm_record(alarm_id):
    connection = get_connection()

    try:
        row = connection.execute(
            ALARM_SELECT_SQL + " WHERE alarms.id = ?",
            (alarm_id,),
        ).fetchone()

        return alarm_row_to_dict(row)
    finally:
        connection.close()


def clear_alarm_records():
    """仅供自动化测试清空告警数据。"""
    connection = get_connection()

    try:
        connection.execute("DELETE FROM alarms")
        connection.execute(
            "DELETE FROM sqlite_sequence WHERE name = 'alarms'"
        )
        connection.commit()
    finally:
        connection.close()

def update_alarm_status_record(
    alarm_id,
    new_status,
    handling_note=None,
):
    connection = get_connection()

    try:
        current_alarm = connection.execute(
            "SELECT id, handling_note FROM alarms WHERE id = ?",
            (alarm_id,),
        ).fetchone()

        if current_alarm is None:
            return None

        note = (
            handling_note
            if handling_note is not None
            else current_alarm["handling_note"]
        )

        connection.execute(
            """
            UPDATE alarms
            SET status = ?, handling_note = ?
            WHERE id = ?
            """,
            (new_status, note, alarm_id),
        )
        connection.commit()

        row = connection.execute(
            ALARM_SELECT_SQL + " WHERE alarms.id = ?",
            (alarm_id,),
        ).fetchone()

        return alarm_row_to_dict(row)
    finally:
        connection.close()