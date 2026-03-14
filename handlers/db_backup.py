from __future__ import annotations

import datetime as dt
import re
import json
import os
import pymysql
import threading
import time
from typing import Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

from db.connect import engine


# === Configuration ===
# Используем настройки из config.py
import config

GOOGLE_SERVICE_ACCOUNT_FILE: str = config.GOOGLE_SERVICE_ACCOUNT_FILE
GOOGLE_SERVICE_ACCOUNT_JSON: str = config.GOOGLE_SERVICE_ACCOUNT_JSON
GDRIVE_FOLDER_ID: str = config.GDRIVE_FOLDER_ID
BACKUP_DIR: str = config.BACKUP_DIR
SCOPES = ['https://www.googleapis.com/auth/drive']
GDRIVE_DELEGATED_USER: str = config.GDRIVE_DELEGATED_USER
BACKUP_COMMAND_ALLOWED_USER_ID: Optional[int] = config.BACKUP_COMMAND_ALLOWED_USER_ID

def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def _extract_drive_folder_id(raw: Optional[str]) -> Optional[str]:
    """
    Accept either a Google Drive folder URL or a bare folder ID and return the ID.
    Example URLs supported:
      - https://drive.google.com/drive/folders/<ID>
      - https://drive.google.com/drive/u/0/folders/<ID>
      - https://drive.google.com/drive/folders/<ID>?usp=sharing
      - https://drive.google.com/open?id=<ID>
    """
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("http://") or s.startswith("https://"):
        m = re.search(r"/folders/([a-zA-Z0-9_-]{10,})", s)
        if not m:
            m = re.search(r"[?&]id=([a-zA-Z0-9_-]{10,})", s)
        return m.group(1) if m else s
    return s


def _load_drive_credentials(delegated_user: Optional[str] = None):
    json_inline = GOOGLE_SERVICE_ACCOUNT_JSON
    file_path = GOOGLE_SERVICE_ACCOUNT_FILE
    scopes = ["https://www.googleapis.com/auth/drive"]
    if isinstance(json_inline, str):
        inline = json_inline.strip()
        if inline.startswith("{"):
            info = json.loads(inline)
            creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            if delegated_user:
                creds = creds.with_subject(delegated_user)
            return creds
    if isinstance(file_path, str):
        p = file_path.strip()
        if p:
            creds = service_account.Credentials.from_service_account_file(p, scopes=scopes)
            if delegated_user:
                creds = creds.with_subject(delegated_user)
            return creds
    raise RuntimeError("Google Drive credentials not configured. Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON.")


# OAuth flow removed per request; Service Account only


def _now_str() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")


def _get_db_params() -> Tuple[str, str, str, int, str]:
    url = engine.url
    user = url.username or ""
    password = url.password or ""
    host = url.host or "localhost"
    port = int(url.port or 3306)
    database = url.database or ""
    if not database:
        raise RuntimeError("Database name is empty in engine.url")
    return user, password, host, port, database


def dump_mysql_database(output_dir: Optional[str] = None) -> str:
    """
    Create a .sql dump of the configured MySQL database using pure Python (PyMySQL).
    Includes CREATE TABLE/VIEW statements and INSERTs for table data.
    Returns absolute file path to the dump.
    """
    user, password, host, port, database = _get_db_params()
    backup_dir = os.path.abspath(output_dir or BACKUP_DIR)
    _ensure_dir(backup_dir)

    filename = f"backup_{database}_{_now_str()}.sql"
    dump_path = os.path.join(backup_dir, filename)

    conn = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        port=port,
        ssl={"ssl_disabled": False},
        charset="utf8mb4",
        autocommit=False,
        cursorclass=pymysql.cursors.Cursor,
    )

    try:
        with conn.cursor() as cur, open(dump_path, "w", encoding="utf-8", errors="replace") as f:
            # Header and environment
            f.write(f"-- Backup generated at {_now_str()} UTC\n")
            f.write(f"-- Database: `{database}`\n\n")
            f.write("SET NAMES utf8mb4;\n")
            f.write("SET FOREIGN_KEY_CHECKS=0;\n")
            f.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n")
            f.write("SET time_zone = '+00:00';\n\n")

            # Consistent snapshot
            cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;")
            cur.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT;")

            # List tables and views
            cur.execute(
                """
                SELECT TABLE_NAME, TABLE_TYPE
                FROM information_schema.tables
                WHERE table_schema = %s
                ORDER BY TABLE_NAME
                """,
                (database,),
            )
            objects = cur.fetchall()  # tuples (name, type)

            # Dump base tables first
            for table_name, table_type in objects:
                if table_type != "BASE TABLE":
                    continue
                # DDL
                cur.execute(f"SHOW CREATE TABLE `{table_name}`")
                _, create_sql = cur.fetchone()
                # sanitize possible surrogate code points
                if isinstance(create_sql, str):
                    create_sql = create_sql.encode("utf-8", "replace").decode("utf-8")
                f.write(f"\n--\n-- Table structure for `{table_name}`\n--\n\n")
                f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                f.write(create_sql + ";\n\n")

                # Data
                f.write(f"--\n-- Dumping data for table `{table_name}`\n--\n")
                cur.execute(f"SELECT * FROM `{table_name}`")
                column_count = len(cur.description)
                if column_count == 0:
                    f.write("\n")
                else:
                    insert_tpl = (
                        f"INSERT INTO `{table_name}` VALUES (" + ",".join(["%s"] * column_count) + ");"
                    )
                    while True:
                        rows = cur.fetchmany(1000)
                        if not rows:
                            break
                        for row in rows:
                            sql_line = cur.mogrify(insert_tpl, row)
                            if isinstance(sql_line, bytes):
                                sql_line = sql_line.decode("utf-8", errors="replace")
                            else:
                                # sanitize to strip surrogates
                                sql_line = sql_line.encode("utf-8", "replace").decode("utf-8")
                            f.write(sql_line + "\n")
                f.write("\n")

            # Dump views after tables
            for table_name, table_type in objects:
                if table_type != "VIEW":
                    continue
                cur.execute(f"SHOW CREATE VIEW `{table_name}`")
                _, create_sql = cur.fetchone()
                if isinstance(create_sql, str):
                    create_sql = create_sql.encode("utf-8", "replace").decode("utf-8")
                f.write(f"\n--\n-- View structure for `{table_name}`\n--\n\n")
                f.write(f"DROP VIEW IF EXISTS `{table_name}`;\n")
                f.write(create_sql + ";\n\n")

            # Finish
            f.write("SET FOREIGN_KEY_CHECKS=1;\n")
            cur.execute("COMMIT;")

        if not os.path.isfile(dump_path) or os.path.getsize(dump_path) == 0:
            raise RuntimeError("Dump file was not created or is empty.")

        return dump_path
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _create_drive_file(service, file_path: str, folder_id: Optional[str]) -> Tuple[str, Optional[str]]:
    media = MediaFileUpload(file_path, mimetype="application/sql", resumable=True)
    body = {"name": os.path.basename(file_path)}
    if folder_id:
        # Validate folder existence and access; supports shared drives
        service.files().get(fileId=folder_id, fields="id, name, driveId", supportsAllDrives=True).execute()
        body["parents"] = [folder_id]
    created = service.files().create(
        body=body,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True,
    ).execute()
    return created.get("id"), created.get("webViewLink")


def upload_to_google_drive(file_path: str, folder_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    delegated_user = GDRIVE_DELEGATED_USER if GDRIVE_DELEGATED_USER else None
    credentials = _load_drive_credentials(delegated_user=delegated_user)
    service = build("drive", "v3", credentials=credentials)

    # Validate and inspect folder if provided
    target_drive_id: Optional[str] = None
    if folder_id:
        try:
            folder_meta = service.files().get(
                fileId=folder_id,
                fields="id, name, driveId",
                supportsAllDrives=True,
            ).execute()
            target_drive_id = folder_meta.get("driveId")
        except Exception as e:
            raise RuntimeError(
                f"Google Drive folder not accessible or not found: {folder_id}. "
                f"If using a Shared Drive, ensure the service account is a member. "
                f"Original error: {e}"
            )

    # Proactive checks to avoid misleading 403s when using a Service Account without delegation
    if not delegated_user:
        # If no delegated user, uploading to My Drive will fail due to missing quota for service accounts
        if not folder_id:
            raise RuntimeError(
                "No target folder specified. Service accounts do not have personal storage. "
                "Set GDRIVE_FOLDER_ID to a Shared Drive folder and grant access, or set GDRIVE_DELEGATED_USER to impersonate a Workspace user."
            )
        if target_drive_id in (None, ""):
            raise RuntimeError(
                "Target folder appears to be in a user's My Drive. Service accounts do not have storage quota there. "
                "Move the folder to a Shared Drive and add the service account as a member, or set GDRIVE_DELEGATED_USER to impersonate a Workspace user."
            )

    return _create_drive_file(service, file_path, folder_id)


_backup_lock = threading.Lock()


def backup_and_upload() -> Tuple[bool, str]:
    print("start backup")
    """
    Performs a DB dump and uploads to Google Drive.
    Returns (success, message/link).
    """
    if not _backup_lock.acquire(blocking=False):
        return False, "Резервное копирование уже выполняется, подождите."
    try:
        dump_path = dump_mysql_database()
        folder_id = (_extract_drive_folder_id(GDRIVE_FOLDER_ID) or None)
        file_id, link = upload_to_google_drive(dump_path, folder_id)
        msg = f"Бэкап загружен. file_id={file_id}"
        if link:
            msg += f"\nСсылка: {link}"
            print(msg)
        print(True)
        return True, msg
    except Exception as e:
        print(False)
        return False, f"Ошибка бэкапа: {e}"
    finally:
        _backup_lock.release()


def trigger_backup_to_chat(bot, chat_id: int) -> None:
    if not _backup_lock.acquire(blocking=False):
        bot.send_message(chat_id, "Резервное копирование уже выполняется, подождите.")
        return

    def _run():
        dump_path: Optional[str] = None
        try:
            bot.send_message(chat_id, "Создаю резервную копию, подождите...")
            dump_path = dump_mysql_database()
            with open(dump_path, "rb") as fh:
                filename = os.path.basename(dump_path)
                bot.send_document(chat_id, fh, caption=f"Резервная копия базы данных: {filename}")
        except Exception as e:
            bot.send_message(chat_id, f"Ошибка бэкапа: {e}")
        finally:
            if dump_path and os.path.exists(dump_path):
                try:
                    os.remove(dump_path)
                except Exception:
                    pass
            _backup_lock.release()

    threading.Thread(target=_run, daemon=True).start()


def register_backup_commands(bot) -> None:
    from telebot import types

    @bot.message_handler(commands=["backup_now"])  # manual trigger
    def _backup_now(m: types.Message):
        chat_id = m.chat.id

        def _run():
            ok, msg = backup_and_upload()
            try:
                bot.send_message(chat_id, msg)
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    # OAuth helper command removed; Service Account only


def _loop_worker(bot, interval_seconds: int):
    while True:
        try:
            ok, msg = backup_and_upload()
            # Optionally log to console; avoid spamming bot users
            print("[backup]", "OK" if ok else "FAIL", msg)
        except Exception as e:
            print("[backup] loop error:", e)
        time.sleep(interval_seconds)


def integrate_backup_scheduler(bot, interval_seconds: int = 86400) -> None:
    t = threading.Thread(target=_loop_worker, args=(bot, interval_seconds), daemon=True)
    t.start()


# Backwards-compatible-style aliases
start_backup_scheduler = integrate_backup_scheduler
register_manual_backup_handler = register_backup_commands


