from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


APP_VERSION = "self-hosted-1.0.0"
DB_PATH = Path(os.environ.get("XIANTU_DB_PATH", "server/data/xiantu.db"))
INSECURE_SECRET_PLACEHOLDERS = {"change-me-local-xiantu", "replace-with-a-long-random-secret"}
SECRET_KEY = os.environ.get("XIANTU_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY in INSECURE_SECRET_PLACEHOLDERS:
    raise RuntimeError("XIANTU_SECRET_KEY must be set to a non-default secret before starting the backend")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 30
PRESENCE_ONLINE_SECONDS = 90
TERMINAL_MARKER_SECONDS = 10 * 60
PUBLIC_TRAVEL_STATES = {"active", "ended", "evicted", "rejected"}
TERMINAL_TRAVEL_STATES = {"ended", "evicted", "rejected"}
LEGACY_TRAVEL_STATE_MAP = {"expired": "evicted", "settled": "ended"}
PUBLIC_END_REASONS = {"normal", "owner_online", "kicked", None}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def public_travel_state(raw_state: Any) -> str:
    state = str(raw_state or "")
    if state in PUBLIC_TRAVEL_STATES:
        return state
    return LEGACY_TRAVEL_STATE_MAP.get(state, "rejected")


def public_end_reason(raw_reason: Any) -> str | None:
    if raw_reason in PUBLIC_END_REASONS:
        return raw_reason
    return None


def api_error(status_code: int, code: str, message: str, **extra: Any) -> HTTPException:
    detail: dict[str, Any] = {"code": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def iso_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def is_recent_iso(value: str | None, seconds: int = PRESENCE_ONLINE_SECONDS) -> bool:
    dt = parse_iso(value)
    if not dt:
        return False
    return (datetime.now(timezone.utc) - dt).total_seconds() < seconds


def row_has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    return any(row["name"] == column for row in conn.execute(f"PRAGMA table_info({table})").fetchall())


def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not row_has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


@contextmanager
def db() -> Any:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_name TEXT NOT NULL UNIQUE,
              password_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS characters (
              char_id TEXT PRIMARY KEY,
              user_id INTEGER NOT NULL,
              base_info TEXT NOT NULL,
              save_data TEXT,
              world_map TEXT,
              game_time TEXT,
              version INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS presence (
              user_id INTEGER PRIMARY KEY,
              last_heartbeat_at TEXT NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS travel_profiles (
              user_id INTEGER PRIMARY KEY,
              travel_points INTEGER NOT NULL DEFAULT 3,
              last_signin_date TEXT,
              FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS world_instances (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              owner_user_id INTEGER NOT NULL UNIQUE,
              owner_char_id TEXT,
              visibility_mode TEXT NOT NULL DEFAULT 'public',
              invite_code TEXT NOT NULL,
              allow_offline_travel INTEGER NOT NULL DEFAULT 1,
              allow_map_overwrite INTEGER NOT NULL DEFAULT 1,
              offline_agent_prompt TEXT,
              revision INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(owner_user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS travel_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              traveler_user_id INTEGER NOT NULL,
              target_world_instance_id INTEGER NOT NULL,
              state TEXT NOT NULL DEFAULT 'active',
              end_reason TEXT,
              entry_map_id INTEGER NOT NULL DEFAULT 1,
              entry_poi_id TEXT NOT NULL DEFAULT '1',
              current_map_id INTEGER NOT NULL DEFAULT 1,
              current_poi_id TEXT NOT NULL DEFAULT '1',
              return_anchor TEXT NOT NULL DEFAULT '{}',
              terminal_acknowledged_at TEXT,
              terminal_marker_expires_at TEXT,
              events TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(traveler_user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS world_overlays (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              world_instance_id INTEGER NOT NULL,
              session_id INTEGER NOT NULL,
              map_id INTEGER NOT NULL,
              character_version INTEGER NOT NULL,
              base_world_revision INTEGER NOT NULL,
              payload TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'accepted',
              created_at TEXT NOT NULL,
              FOREIGN KEY(world_instance_id) REFERENCES world_instances(id),
              FOREIGN KEY(session_id) REFERENCES travel_sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_world_overlays_latest
              ON world_overlays(world_instance_id, character_version, map_id, id);
            CREATE TABLE IF NOT EXISTS invasion_reports (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              world_instance_id INTEGER NOT NULL,
              session_id INTEGER NOT NULL,
              traveler_user_id INTEGER NOT NULL,
              owner_user_id INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              unread INTEGER NOT NULL DEFAULT 1,
              summary TEXT,
              FOREIGN KEY(world_instance_id) REFERENCES world_instances(id),
              FOREIGN KEY(session_id) REFERENCES travel_sessions(id)
            );
            CREATE TABLE IF NOT EXISTS workshop_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              type TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT,
              tags TEXT NOT NULL DEFAULT '[]',
              payload TEXT NOT NULL,
              game_version TEXT,
              data_version TEXT,
              author_id INTEGER NOT NULL,
              downloads INTEGER NOT NULL DEFAULT 0,
              likes INTEGER NOT NULL DEFAULT 0,
              is_public INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(author_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS generated_items (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              type TEXT NOT NULL,
              content TEXT NOT NULL,
              owner_user_id INTEGER,
              created_at TEXT NOT NULL
            );
            """
        )
        add_column_if_missing(conn, "travel_sessions", "entry_map_id", "INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "travel_sessions", "entry_poi_id", "TEXT NOT NULL DEFAULT '1'")
        add_column_if_missing(conn, "travel_sessions", "current_map_id", "INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "travel_sessions", "current_poi_id", "TEXT NOT NULL DEFAULT '1'")
        add_column_if_missing(conn, "travel_sessions", "return_anchor", "TEXT NOT NULL DEFAULT '{}'")
        add_column_if_missing(conn, "travel_sessions", "terminal_acknowledged_at", "TEXT")
        add_column_if_missing(conn, "travel_sessions", "terminal_marker_expires_at", "TEXT")
        migrate_canonical_online_roles(conn)


def migrate_canonical_online_roles(conn: sqlite3.Connection) -> None:
    instances = conn.execute("SELECT * FROM world_instances").fetchall()
    for instance in instances:
        owner_user_id = instance["owner_user_id"]
        current = instance["owner_char_id"]
        if current:
            owned = conn.execute(
                "SELECT char_id FROM characters WHERE char_id = ? AND user_id = ?",
                (current, owner_user_id),
            ).fetchone()
            if owned:
                continue
        canonical = conn.execute(
            """
            SELECT char_id FROM characters
            WHERE user_id = ?
            ORDER BY updated_at DESC, created_at DESC, char_id DESC
            LIMIT 1
            """,
            (owner_user_id,),
        ).fetchone()
        if canonical:
            conn.execute(
                "UPDATE world_instances SET owner_char_id = ?, updated_at = ? WHERE id = ?",
                (canonical["char_id"], utc_now(), instance["id"]),
            )


def assert_canonical_online_role(conn: sqlite3.Connection, user: sqlite3.Row, char_id: str) -> None:
    instance = conn.execute("SELECT * FROM world_instances WHERE owner_user_id = ?", (user["id"],)).fetchone()
    if not instance:
        return
    canonical = instance["owner_char_id"]
    if canonical and canonical != char_id:
        raise api_error(409, "ONLINE_CHARACTER_LIMIT", "一个账号只能拥有一个联机角色")


def coerce_poi_id(value: Any) -> Any:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return stripped
    return value


def default_world_info() -> dict[str, Any]:
    return {"世界名称": "未命名世界", "大陆信息": [], "势力信息": [], "地点信息": []}


def get_owner_character(conn: sqlite3.Connection, instance: sqlite3.Row) -> sqlite3.Row | None:
    if not instance["owner_char_id"]:
        return None
    return conn.execute("SELECT * FROM characters WHERE char_id = ?", (instance["owner_char_id"],)).fetchone()


def get_owner_info(conn: sqlite3.Connection, instance: sqlite3.Row) -> tuple[sqlite3.Row, sqlite3.Row | None]:
    owner = conn.execute("SELECT * FROM users WHERE id = ?", (instance["owner_user_id"],)).fetchone()
    return owner, get_owner_character(conn, instance)


def get_character_version(conn: sqlite3.Connection, instance: sqlite3.Row) -> int:
    char = get_owner_character(conn, instance)
    return int(char["version"]) if char else 0


def overlay_base(conn: sqlite3.Connection, instance: sqlite3.Row) -> dict[str, int]:
    return {
        "character_version": get_character_version(conn, instance),
        "world_revision": int(instance["revision"]),
    }


def owner_presence(conn: sqlite3.Connection, owner_user_id: int) -> dict[str, Any]:
    presence = conn.execute("SELECT * FROM presence WHERE user_id = ?", (owner_user_id,)).fetchone()
    last = presence["last_heartbeat_at"] if presence else None
    return {"owner_online": is_recent_iso(last), "owner_last_heartbeat_at": last}


def map_ids_from_world(world_info: Any) -> set[int]:
    ids = {1}
    if not isinstance(world_info, dict):
        return ids
    for key in ("地点信息", "locations"):
        raw = world_info.get(key)
        if not isinstance(raw, list):
            continue
        for loc in raw:
            if not isinstance(loc, dict):
                continue
            raw_id = loc.get("map_id")
            if raw_id is None:
                raw_id = loc.get("地图ID")
            try:
                if raw_id is not None:
                    ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
    maps = world_info.get("maps")
    if isinstance(maps, list):
        for item in maps:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("map_id")
            if raw_id is None:
                raw_id = item.get("地图ID")
            if raw_id is None:
                raw_id = item.get("id")
            try:
                if raw_id is not None:
                    ids.add(int(raw_id))
            except (TypeError, ValueError):
                continue
    return ids


def is_known_map_id(conn: sqlite3.Connection, instance: sqlite3.Row, map_id: int) -> bool:
    _, char = get_owner_info(conn, instance)
    world = json_loads(char["world_map"], {}) if char else {}
    return map_id in map_ids_from_world(world)


def replace_locations_for_map(world_info: dict[str, Any], map_id: int, locations: list[Any]) -> dict[str, Any]:
    world = json.loads(json_dumps(world_info or default_world_info()))
    key = "地点信息" if "地点信息" in world or "locations" not in world else "locations"
    raw_locations = world.get(key)
    existing = raw_locations if isinstance(raw_locations, list) else []
    kept = []
    for loc in existing:
        if not isinstance(loc, dict):
            continue
        raw_map_id = loc.get("map_id", loc.get("地图ID", 1))
        try:
            loc_map_id = int(raw_map_id)
        except (TypeError, ValueError):
            loc_map_id = 1
        if loc_map_id != map_id:
            kept.append(loc)
    normalized_locations = []
    for loc in locations:
        if isinstance(loc, dict):
            item = dict(loc)
            item.setdefault("map_id", map_id)
            normalized_locations.append(item)
        else:
            normalized_locations.append(loc)
    world[key] = kept + normalized_locations
    if key == "地点信息" and "locations" in world:
        world["locations"] = world[key]
    return world


def derived_world_view(conn: sqlite3.Connection, instance: sqlite3.Row) -> dict[str, Any]:
    char = get_owner_character(conn, instance)
    base_world = json_loads(char["world_map"], {}) if char else {}
    world = base_world if isinstance(base_world, dict) and base_world else default_world_info()
    character_version = int(char["version"]) if char else 0
    overlays = conn.execute(
        """
        SELECT * FROM world_overlays
        WHERE world_instance_id = ? AND character_version = ? AND state = 'accepted'
        ORDER BY id ASC
        """,
        (instance["id"], character_version),
    ).fetchall()
    latest_by_map: dict[int, sqlite3.Row] = {}
    for overlay in overlays:
        latest_by_map[int(overlay["map_id"])] = overlay
    for map_id, overlay in latest_by_map.items():
        payload = json_loads(overlay["payload"], {})
        locations = payload.get("locations") if isinstance(payload, dict) else None
        if isinstance(locations, list):
            world = replace_locations_for_map(world, map_id, locations)
    return world


def owner_character_info(char: sqlite3.Row | None) -> dict[str, Any] | None:
    if not char:
        return None
    base = json_loads(char["base_info"], {})
    if not isinstance(base, dict):
        return None
    return {
        "name": base.get("name") or base.get("名字"),
        "cultivation_level": base.get("cultivation_level") or base.get("境界"),
        "sect": base.get("sect") or base.get("门派"),
        "personality": base.get("personality") or base.get("性格"),
        "_raw": base,
    }


def owner_save_data(char: sqlite3.Row | None) -> dict[str, Any]:
    if not char:
        return {}
    data = json_loads(char["save_data"], {})
    return data if isinstance(data, dict) else {}


def first_dict_path(data: dict[str, Any], paths: list[tuple[str, ...]]) -> dict[str, Any] | None:
    for path in paths:
        current: Any = data
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if isinstance(current, dict):
            return current
    return None


def owner_location_from_save(char: sqlite3.Row | None) -> dict[str, Any] | None:
    data = owner_save_data(char)
    return first_dict_path(data, [("角色", "位置"), ("character", "location"), ("location",)])


def owner_relationships_from_save(char: sqlite3.Row | None) -> dict[str, Any] | None:
    data = owner_save_data(char)
    return first_dict_path(data, [("社交", "关系"), ("relationships",)])


def append_session_event(
    conn: sqlite3.Connection,
    session_id: int,
    event_type: str,
    *,
    map_id: int | None = None,
    poi_id: Any = None,
    payload: Any = None,
) -> None:
    row = conn.execute("SELECT events FROM travel_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return
    events = json_loads(row["events"], [])
    if not isinstance(events, list):
        events = []
    event: dict[str, Any] = {"created_at": utc_now(), "event_type": event_type}
    if map_id is not None:
        event["map_id"] = map_id
    if poi_id is not None:
        event["poi_id"] = coerce_poi_id(poi_id)
    if payload is not None:
        event["payload"] = payload
    events.append(event)
    conn.execute("UPDATE travel_sessions SET events = ?, updated_at = ? WHERE id = ?", (json_dumps(events), utc_now(), session_id))


def create_invasion_report(conn: sqlite3.Connection, session: sqlite3.Row, summary: dict[str, Any]) -> None:
    instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (session["target_world_instance_id"],)).fetchone()
    if not instance:
        return
    conn.execute(
        """
        INSERT INTO invasion_reports (
          world_instance_id, session_id, traveler_user_id, owner_user_id, created_at, unread, summary
        ) VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (
            instance["id"],
            session["id"],
            session["traveler_user_id"],
            instance["owner_user_id"],
            utc_now(),
            json_dumps(summary),
        ),
    )


def mark_session_terminal(
    conn: sqlite3.Connection,
    session: sqlite3.Row,
    state: str,
    end_reason: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    if state not in PUBLIC_TRAVEL_STATES or end_reason not in PUBLIC_END_REASONS:
        raise ValueError("invalid public session terminal state")
    conn.execute(
        """
        UPDATE travel_sessions
        SET state = ?, end_reason = ?, terminal_acknowledged_at = NULL,
            terminal_marker_expires_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (state, end_reason, iso_after(TERMINAL_MARKER_SECONDS), utc_now(), session["id"]),
    )
    append_session_event(
        conn,
        int(session["id"]),
        event_type,
        map_id=int(session["current_map_id"]),
        poi_id=session["current_poi_id"],
        payload=payload or {"end_reason": end_reason},
    )
    updated = conn.execute("SELECT * FROM travel_sessions WHERE id = ?", (session["id"],)).fetchone()
    if updated:
        create_invasion_report(conn, updated, {"terminal": state, "end_reason": end_reason})


def evict_owner_world_sessions(conn: sqlite3.Connection, owner_user_id: int) -> int:
    worlds = conn.execute("SELECT * FROM world_instances WHERE owner_user_id = ?", (owner_user_id,)).fetchall()
    count = 0
    for world in worlds:
        sessions = conn.execute(
            """
            SELECT * FROM travel_sessions
            WHERE target_world_instance_id = ? AND state = 'active' AND traveler_user_id != ?
            """,
            (world["id"], owner_user_id),
        ).fetchall()
        for session in sessions:
            mark_session_terminal(
                conn,
                session,
                "evicted",
                "owner_online",
                "travel_evicted",
                {"reason": "owner_online"},
            )
            count += 1
    return count


def travel_points_left(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute("SELECT * FROM travel_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        conn.execute("INSERT INTO travel_profiles (user_id, travel_points) VALUES (?, ?)", (user_id, 3))
        return 3
    return int(row["travel_points"])


def serialize_travel_session(conn: sqlite3.Connection, session: sqlite3.Row, *, active_probe: bool) -> dict[str, Any]:
    instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (session["target_world_instance_id"],)).fetchone()
    if not instance:
        raise api_error(404, "SESSION_NOT_FOUND", "穿越会话不存在")
    owner, char = get_owner_info(conn, instance)
    presence = owner_presence(conn, int(instance["owner_user_id"]))
    view: dict[str, Any] = {
        "session_id": session["id"],
        "state": public_travel_state(session["state"]),
        "end_reason": public_end_reason(session["end_reason"]),
        "target_world_instance_id": session["target_world_instance_id"],
        "entry_map_id": int(session["entry_map_id"]),
        "entry_poi_id": coerce_poi_id(session["entry_poi_id"]),
        "current_map_id": int(session["current_map_id"]),
        "current_poi_id": coerce_poi_id(session["current_poi_id"]),
        "owner_online": presence["owner_online"],
        "owner_last_heartbeat_at": presence["owner_last_heartbeat_at"],
    }
    if active_probe:
        view.update(
            {
                "return_anchor": json_loads(session["return_anchor"], {}),
                "travel_points_left": travel_points_left(conn, int(session["traveler_user_id"])),
                "owner_offline_agent_prompt": instance["offline_agent_prompt"],
                "owner_character_info": owner_character_info(char),
                "owner_username": owner["user_name"] if owner else None,
                "overlay_base": overlay_base(conn, instance),
            }
        )
    return view


def active_or_terminal_session(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    active = conn.execute(
        "SELECT * FROM travel_sessions WHERE traveler_user_id = ? AND state = 'active' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    if active:
        return active
    now = utc_now()
    return conn.execute(
        """
        SELECT * FROM travel_sessions
        WHERE traveler_user_id = ? AND state IN ('ended', 'evicted', 'rejected')
          AND terminal_acknowledged_at IS NULL
          AND (terminal_marker_expires_at IS NULL OR terminal_marker_expires_at > ?)
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (user_id, now),
    ).fetchone()


def require_travel_session(
    conn: sqlite3.Connection,
    session_id: Any,
    user: sqlite3.Row,
    *,
    require_active: bool = False,
) -> sqlite3.Row:
    try:
        sid = int(session_id)
    except (TypeError, ValueError):
        raise api_error(404, "SESSION_NOT_FOUND", "穿越会话不存在")
    session = conn.execute("SELECT * FROM travel_sessions WHERE id = ?", (sid,)).fetchone()
    if not session:
        raise api_error(404, "SESSION_NOT_FOUND", "穿越会话不存在")
    if int(session["traveler_user_id"]) != int(user["id"]):
        raise api_error(403, "SESSION_FORBIDDEN", "不能访问他人的穿越会话")
    if require_active and session["state"] != "active":
        raise api_error(410, "SESSION_NOT_ACTIVE", "穿越会话已结束")
    return session


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 150_000)
    return f"pbkdf2_sha256${salt}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    expected = hash_password(password, salt)
    return hmac.compare_digest(expected, stored)


def sign_token(payload: dict[str, Any]) -> str:
    raw = base64.urlsafe_b64encode(json_dumps(payload).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).digest()
    enc_sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")
    return f"{raw}.{enc_sig}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        raw, enc_sig = token.split(".", 1)
        expected = base64.urlsafe_b64encode(
            hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).digest()
        ).decode().rstrip("=")
        if not hmac.compare_digest(expected, enc_sig):
            raise ValueError("bad signature")
        padded = raw + ("=" * (-len(raw) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
    except Exception as exc:
        raise HTTPException(status_code=401, detail="无效或过期的登录凭证") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=401, detail="登录已过期")
    return payload


def get_current_user(authorization: str | None = Header(default=None)) -> sqlite3.Row:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (payload.get("sub"),)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def issue_token(user: sqlite3.Row) -> str:
    return sign_token(
        {
            "sub": user["id"],
            "user_name": user["user_name"],
            "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        }
    )


def ensure_world_instance(conn: sqlite3.Connection, user: sqlite3.Row, char_id: str | None = None) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM world_instances WHERE owner_user_id = ?", (user["id"],)).fetchone()
    if row:
        if char_id and row["owner_char_id"] and row["owner_char_id"] != char_id:
            raise api_error(409, "ONLINE_CHARACTER_LIMIT", "一个账号只能拥有一个联机角色")
        if char_id and not row["owner_char_id"]:
            conn.execute(
                "UPDATE world_instances SET owner_char_id = ?, updated_at = ? WHERE id = ?",
                (char_id, utc_now(), row["id"]),
            )
            row = conn.execute("SELECT * FROM world_instances WHERE id = ?", (row["id"],)).fetchone()
        return row
    now = utc_now()
    conn.execute(
        """
        INSERT INTO world_instances (
          owner_user_id, owner_char_id, invite_code, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (user["id"], char_id, secrets.token_urlsafe(8), now, now),
    )
    return conn.execute("SELECT * FROM world_instances WHERE owner_user_id = ?", (user["id"],)).fetchone()


def serialize_world_instance(conn: sqlite3.Connection, row: sqlite3.Row, include_invite: bool = True) -> dict[str, Any]:
    maps = [{"map_id": 1, "map_key": "main", "revision": row["revision"]}]
    data = {
        "world_instance_id": row["id"],
        "owner_player_id": row["owner_user_id"],
        "owner_char_id": row["owner_char_id"],
        "visibility_mode": row["visibility_mode"],
        "allow_offline_travel": bool(row["allow_offline_travel"]),
        "allow_map_overwrite": bool(row["allow_map_overwrite"]),
        "offline_agent_prompt": row["offline_agent_prompt"],
        "revision": row["revision"],
        "maps": maps,
    }
    if include_invite:
        data["invite_code"] = row["invite_code"]
    return data


BASE_WORLDS = [
    {
        "id": 1,
        "name": "朝天大陆",
        "era": "朝天历元年",
        "description": "天道完整、灵气充沛的修仙大陆，万灵竞渡，大道争锋。",
        "source": "cloud",
    },
    {
        "id": 2,
        "name": "地球",
        "era": "灵气复苏元年",
        "description": "现代都市与灵气复苏相撞，科技和修真并行。",
        "source": "cloud",
    },
    {
        "id": 3,
        "name": "赛博修真",
        "era": "新纪元2156",
        "description": "义体、神经网络与灵能水晶构成的新修行时代。",
        "source": "cloud",
    },
]

BASE_TALENT_TIERS = [
    {"id": 1, "name": "废柴", "description": "资质平平，但道心可贵。", "total_points": 10, "rarity": 1, "color": "#718096", "source": "cloud"},
    {"id": 2, "name": "凡人", "description": "芸芸众生，有缘可入仙途。", "total_points": 20, "rarity": 2, "color": "#E2E8F0", "source": "cloud"},
    {"id": 3, "name": "俊杰", "description": "百里挑一，可为宗门内门。", "total_points": 35, "rarity": 3, "color": "#63B3ED", "source": "cloud"},
    {"id": 4, "name": "天骄", "description": "千年难遇，修行速度远超常人。", "total_points": 50, "rarity": 4, "color": "#9F7AEA", "source": "cloud"},
    {"id": 5, "name": "妖孽", "description": "万古无一，潜力逆天。", "total_points": 70, "rarity": 5, "color": "#F6E05E", "source": "cloud"},
]

BASE_ORIGINS = [
    {"id": 1, "name": "山野遗孤", "description": "与山野为伴，体魄坚韧。", "talent_cost": 0, "attribute_modifiers": {"root_bone": 1}, "rarity": 3, "source": "cloud"},
    {"id": 2, "name": "书香门第", "description": "饱读诗书，悟性出众。", "talent_cost": 2, "attribute_modifiers": {"comprehension": 2}, "rarity": 3, "source": "cloud"},
    {"id": 3, "name": "散修传人", "description": "继承散修衣钵，见识不凡。", "talent_cost": 4, "attribute_modifiers": {"comprehension": 1, "temperament": 1}, "rarity": 4, "source": "cloud"},
]

BASE_SPIRIT_ROOTS = [
    {"id": 1, "name": "金灵根", "tier": "中品", "description": "锐意锋芒，适合攻伐。", "cultivation_speed": "1.3x", "special_effects": ["金系法术威力+25%"], "base_multiplier": 1.3, "talent_cost": 6, "rarity": 2, "source": "cloud"},
    {"id": 2, "name": "木灵根", "tier": "中品", "description": "生机绵长，恢复力佳。", "cultivation_speed": "1.3x", "special_effects": ["生命力恢复+20%"], "base_multiplier": 1.3, "talent_cost": 6, "rarity": 2, "source": "cloud"},
    {"id": 3, "name": "天灵根", "tier": "极品", "description": "灵气亲和极佳，修行极快。", "cultivation_speed": "2.0x", "special_effects": ["修炼效率大幅提升"], "base_multiplier": 2.0, "talent_cost": 15, "rarity": 5, "source": "cloud"},
]

BASE_TALENTS = [
    {"id": 1, "name": "天命主角", "description": "气运惊人，绝境逢生。", "talent_cost": 15, "rarity": 5, "effects": [{"类型": "后天六司", "目标": "气运", "数值": 8}], "source": "cloud"},
    {"id": 2, "name": "剑道独尊", "description": "剑心通明，剑法威力倍增。", "talent_cost": 12, "rarity": 5, "effects": [{"类型": "技能加成", "技能": "剑法", "数值": 0.2}], "source": "cloud"},
    {"id": 3, "name": "过目不忘", "description": "记忆力超群，学习更快。", "talent_cost": 2, "rarity": 2, "effects": [{"类型": "后天六司", "目标": "悟性", "数值": 2}], "source": "cloud"},
]


app = FastAPI(title="XianTu self-hosted backend", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail, headers=exc.headers)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health", response_model=None)
@app.head("/api/health", response_model=None)
def health():
    return {"ok": True, "version": APP_VERSION, "server_time": utc_now()}


@app.get("/api/v1/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}


@app.get("/api/v1/stats")
def stats() -> dict[str, Any]:
    with db() as conn:
        users = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
        characters = conn.execute("SELECT COUNT(*) AS count FROM characters").fetchone()["count"]
        worlds = conn.execute("SELECT COUNT(*) AS count FROM world_instances").fetchone()["count"]
        presence_rows = conn.execute("SELECT last_heartbeat_at FROM presence").fetchall()
    online_users = sum(1 for row in presence_rows if is_recent_iso(row["last_heartbeat_at"]))
    return {
        "version": APP_VERSION,
        "total_users": int(users),
        "total_characters": int(characters),
        "online_users": int(online_users),
        "total_worlds": int(worlds),
    }


@app.get("/api/v1/auth/security-settings")
def security_settings() -> dict[str, Any]:
    return {
        "turnstile_enabled": False,
        "turnstile_site_key": "",
        "email_verification_enabled": False,
    }


@app.post("/api/v1/auth/send-email-code")
async def send_email_code() -> dict[str, Any]:
    return {"success": True, "message": "自托管后端未启用邮箱验证"}


@app.post("/api/v1/auth/register")
async def register(request: Request) -> dict[str, Any]:
    data = await request.json()
    user_name = str(data.get("user_name") or data.get("username") or "").strip()
    password = str(data.get("password") or "")
    if len(user_name) < 2:
        raise HTTPException(status_code=400, detail="道号至少需要 2 个字符")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="令牌至少需要 4 个字符")
    now = utc_now()
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO users (user_name, password_hash, created_at) VALUES (?, ?, ?)",
                (user_name, hash_password(password), now),
            )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=400, detail="道号已存在") from exc
    return {"success": True, "message": "注册成功"}


@app.post("/api/v1/auth/token")
async def login(request: Request) -> dict[str, Any]:
    data = await request.json()
    username = str(data.get("username") or data.get("user_name") or "").strip()
    password = str(data.get("password") or "")
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_name = ?", (username,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="道号或令牌不正确")
        now = utc_now()
        conn.execute(
            "INSERT INTO presence (user_id, last_heartbeat_at) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_heartbeat_at = excluded.last_heartbeat_at",
            (user["id"], now),
        )
        evict_owner_world_sessions(conn, int(user["id"]))
        return {"access_token": issue_token(user), "token_type": "bearer"}


@app.get("/api/v1/auth/me")
def me(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return {"id": user["id"], "user_name": user["user_name"], "created_at": user["created_at"]}


def list_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {"items": items, "total": len(items)}


@app.get("/api/v1/worlds")
@app.get("/api/v1/worlds/")
def worlds() -> dict[str, Any]:
    return list_response(BASE_WORLDS)


@app.get("/api/v1/talent_tiers")
@app.get("/api/v1/talent_tiers/")
def talent_tiers() -> dict[str, Any]:
    return list_response(BASE_TALENT_TIERS)


@app.get("/api/v1/origins")
@app.get("/api/v1/origins/")
def origins() -> dict[str, Any]:
    return list_response(BASE_ORIGINS)


@app.get("/api/v1/spirit_roots")
@app.get("/api/v1/spirit_roots/")
def spirit_roots() -> dict[str, Any]:
    return list_response(BASE_SPIRIT_ROOTS)


@app.get("/api/v1/talents")
@app.get("/api/v1/talents/")
def talents() -> dict[str, Any]:
    return list_response(BASE_TALENTS)


@app.post("/api/v1/characters/create")
async def create_character(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    char_id = str(data.get("char_id") or "").strip() or f"char_{int(time.time() * 1000)}"
    base_info = data.get("base_info") or {}
    now = utc_now()
    with db() as conn:
        assert_canonical_online_role(conn, user, char_id)
        conn.execute(
            """
            INSERT INTO characters (char_id, user_id, base_info, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(char_id) DO UPDATE SET
              user_id = excluded.user_id,
              base_info = excluded.base_info,
              updated_at = excluded.updated_at
            """,
            (char_id, user["id"], json_dumps(base_info), now, now),
        )
        ensure_world_instance(conn, user, char_id)
    return {"success": True, "char_id": char_id, "message": "角色已创建"}


@app.put("/api/v1/characters/{char_id}/save")
async def update_character_save(char_id: str, request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    now = utc_now()
    with db() as conn:
        assert_canonical_online_role(conn, user, char_id)
        row = conn.execute(
            "SELECT * FROM characters WHERE char_id = ? AND user_id = ?",
            (char_id, user["id"]),
        ).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO characters (char_id, user_id, base_info, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (char_id, user["id"], json_dumps({}), now, now),
            )
            row = conn.execute("SELECT * FROM characters WHERE char_id = ? AND user_id = ?", (char_id, user["id"])).fetchone()
        version_num = int(row["version"]) + 1
        conn.execute(
            """
            UPDATE characters SET save_data = ?, world_map = ?, game_time = ?,
              version = ?, updated_at = ? WHERE char_id = ? AND user_id = ?
            """,
            (
                json_dumps(data.get("save_data")),
                json_dumps(data.get("world_map") or {}),
                data.get("game_time"),
                version_num,
                now,
                char_id,
                user["id"],
            ),
        )
        ensure_world_instance(conn, user, char_id)
    return {"success": True, "version": version_num, "last_sync": now}


@app.get("/api/v1/characters/{char_id}")
def get_character(char_id: str, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM characters WHERE char_id = ? AND user_id = ?",
            (char_id, user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    return {
        "char_id": row["char_id"],
        "base_info": json_loads(row["base_info"], {}),
        "game_save": {
            "save_data": json_loads(row["save_data"], None),
            "world_map": json_loads(row["world_map"], {}),
            "game_time": row["game_time"],
            "version": row["version"],
            "last_sync": row["updated_at"],
        },
    }


@app.post("/api/v1/presence/heartbeat")
def presence_heartbeat(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    now = utc_now()
    with db() as conn:
        conn.execute(
            "INSERT INTO presence (user_id, last_heartbeat_at) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET last_heartbeat_at = excluded.last_heartbeat_at",
            (user["id"], now),
        )
        evicted = evict_owner_world_sessions(conn, int(user["id"]))
    return {"user_name": user["user_name"], "server_time": now, "last_heartbeat_at": now, "evicted_sessions": evicted}


@app.get("/api/v1/presence/me")
def presence_me(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return presence_status(user["user_name"], user)


@app.get("/api/v1/presence/status/{username}")
def presence_status(username: str, _: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute(
            """
            SELECT users.user_name, presence.last_heartbeat_at FROM users
            LEFT JOIN presence ON presence.user_id = users.id
            WHERE users.user_name = ?
            """,
            (username,),
        ).fetchone()
    now = utc_now()
    last = row["last_heartbeat_at"] if row else None
    is_online = is_recent_iso(last)
    return {"user_name": username, "is_online": is_online, "last_heartbeat_at": last, "server_time": now}


@app.get("/api/v1/travel/profile")
def travel_profile(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as conn:
        row = conn.execute("SELECT * FROM travel_profiles WHERE user_id = ?", (user["id"],)).fetchone()
        if not row:
            conn.execute("INSERT INTO travel_profiles (user_id, travel_points) VALUES (?, ?)", (user["id"], 3))
            row = conn.execute("SELECT * FROM travel_profiles WHERE user_id = ?", (user["id"],)).fetchone()
    return {
        "travel_points": row["travel_points"],
        "signed_in": row["last_signin_date"] == today,
        "message": "ok",
    }


@app.post("/api/v1/travel/signin")
def travel_signin(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    with db() as conn:
        row = conn.execute("SELECT * FROM travel_profiles WHERE user_id = ?", (user["id"],)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO travel_profiles (user_id, travel_points, last_signin_date) VALUES (?, ?, ?)",
                (user["id"], 4, today),
            )
            points = 4
            signed = True
            message = "签到成功，获得 1 点穿越点"
        elif row["last_signin_date"] == today:
            points = row["travel_points"]
            signed = True
            message = "今日已签到"
        else:
            points = row["travel_points"] + 1
            conn.execute(
                "UPDATE travel_profiles SET travel_points = ?, last_signin_date = ? WHERE user_id = ?",
                (points, today, user["id"]),
            )
            signed = True
            message = "签到成功，获得 1 点穿越点"
    return {"travel_points": points, "signed_in": signed, "message": message}


@app.get("/api/v1/travel/active")
def travel_active(user: sqlite3.Row = Depends(get_current_user)) -> Any:
    with db() as conn:
        row = active_or_terminal_session(conn, int(user["id"]))
        if not row:
            return None
        return serialize_travel_session(conn, row, active_probe=True)


@app.post("/api/v1/travel/start")
async def travel_start(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    target_username = str(data.get("target_username") or "").strip()
    invite_code = data.get("invite_code")
    with db() as conn:
        existing_active = conn.execute(
            "SELECT id FROM travel_sessions WHERE traveler_user_id = ? AND state = 'active' ORDER BY id DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
        if existing_active:
            raise api_error(409, "ACTIVE_SESSION_EXISTS", "已有进行中的穿越会话")
        target = conn.execute("SELECT * FROM users WHERE user_name = ?", (target_username,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="目标道友不存在")
        instance = ensure_world_instance(conn, target)
        if int(instance["owner_user_id"]) == int(user["id"]):
            raise api_error(409, "OWNER_ONLINE", "不能穿越到自己的在线世界")
        presence = owner_presence(conn, int(instance["owner_user_id"]))
        if presence["owner_online"]:
            raise api_error(409, "OWNER_ONLINE", "世界主人在线，无法穿越")
        if not bool(instance["allow_offline_travel"]):
            raise api_error(409, "OFFLINE_TRAVEL_DISABLED", "该世界未开启下线代理")
        if instance["visibility_mode"] == "locked" and invite_code != instance["invite_code"]:
            raise api_error(403, "INVITE_CODE_INVALID", "邀请码不正确")
        profile = conn.execute("SELECT * FROM travel_profiles WHERE user_id = ?", (user["id"],)).fetchone()
        points = int(profile["travel_points"]) if profile else 3
        if points <= 0:
            raise HTTPException(status_code=400, detail="穿越点不足")
        if not profile:
            conn.execute("INSERT INTO travel_profiles (user_id, travel_points) VALUES (?, ?)", (user["id"], points))
        conn.execute("UPDATE travel_profiles SET travel_points = travel_points - 1 WHERE user_id = ?", (user["id"],))
        now = utc_now()
        conn.execute(
            """
            UPDATE travel_sessions
            SET terminal_acknowledged_at = ?, terminal_marker_expires_at = NULL
            WHERE traveler_user_id = ? AND state != 'active' AND terminal_acknowledged_at IS NULL
            """,
            (now, user["id"]),
        )
        events = [
            {
                "created_at": now,
                "event_type": "travel_start",
                "map_id": 1,
                "poi_id": 1,
                "payload": {"target_username": target_username},
            }
        ]
        cur = conn.execute(
            """
            INSERT INTO travel_sessions (
              traveler_user_id, target_world_instance_id, state, end_reason,
              entry_map_id, entry_poi_id, current_map_id, current_poi_id,
              return_anchor, events, created_at, updated_at
            ) VALUES (?, ?, 'active', NULL, 1, '1', 1, '1', ?, ?, ?, ?)
            """,
            (user["id"], instance["id"], json_dumps(data.get("return_anchor") or {}), json_dumps(events), now, now),
        )
        session = conn.execute("SELECT * FROM travel_sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
        return serialize_travel_session(conn, session, active_probe=True)


@app.get("/api/v1/travel/status/{session_id}")
def travel_status(session_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = require_travel_session(conn, session_id, user)
        return serialize_travel_session(conn, row, active_probe=False)


@app.post("/api/v1/travel/end")
async def travel_end(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    session_id = data.get("session_id")
    with db() as conn:
        session = require_travel_session(conn, session_id, user, require_active=True)
        mark_session_terminal(conn, session, "ended", "normal", "travel_end", {"reason": "normal"})
    return {"success": True, "message": "穿越已结束"}


@app.post("/api/v1/travel/ack-terminal")
async def ack_terminal(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    with db() as conn:
        session = require_travel_session(conn, data.get("session_id"), user)
        active = conn.execute(
            "SELECT * FROM travel_sessions WHERE traveler_user_id = ? AND state = 'active' ORDER BY id DESC LIMIT 1",
            (user["id"],),
        ).fetchone()
        if session["state"] != "active" and active and int(active["id"]) != int(session["id"]):
            return {"success": True, "cleared": False, "reason": "superseded_by_new_active"}
        if session["state"] == "active":
            return {"success": True, "cleared": False, "reason": "superseded_by_new_active"}
        if session["terminal_acknowledged_at"] is not None:
            return {"success": True, "cleared": False, "reason": "already_cleared"}
        conn.execute(
            "UPDATE travel_sessions SET terminal_acknowledged_at = ?, terminal_marker_expires_at = NULL, updated_at = ? WHERE id = ?",
            (utc_now(), utc_now(), session["id"]),
        )
    return {"success": True, "cleared": True, "reason": "acknowledged"}


@app.get("/api/v1/travel/logs/{session_id}")
def travel_logs(session_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = require_travel_session(conn, session_id, user)
        view = serialize_travel_session(conn, row, active_probe=False)
        view["events"] = json_loads(row["events"], [])
        return view


@app.post("/api/v1/travel/note")
async def travel_note(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    session_id = data.get("session_id")
    with db() as conn:
        row = require_travel_session(conn, session_id, user)
        append_session_event(
            conn,
            int(row["id"]),
            "note",
            map_id=int(row["current_map_id"]),
            poi_id=row["current_poi_id"],
            payload={"note": data.get("note"), "meta": data.get("meta")},
        )
    return {"success": True, "message": "已记录"}


@app.get("/api/v1/travel/snapshot/{session_id}")
def travel_snapshot(session_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        session = require_travel_session(conn, session_id, user)
        instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (session["target_world_instance_id"],)).fetchone()
        owner, char = get_owner_info(conn, instance)
        base_info = json_loads(char["base_info"], {}) if char else {}
        return {
            "session_id": session_id,
            "target_world_instance_id": instance["id"],
            "owner_player_id": owner["id"],
            "owner_username": owner["user_name"],
            "owner_char_id": instance["owner_char_id"],
            "save_version": char["version"] if char else None,
            "game_time": char["game_time"] if char else None,
            "world_info": derived_world_view(conn, instance),
            "owner_location": owner_location_from_save(char),
            "owner_base_info": base_info,
            "relationships": owner_relationships_from_save(char),
            "overlay_base": overlay_base(conn, instance),
        }


@app.get("/api/v1/worlds/instance/me")
def my_world_instance(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = ensure_world_instance(conn, user)
        return serialize_world_instance(conn, row)


@app.post("/api/v1/worlds/instance/me/visibility")
async def my_world_visibility(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    mode = data.get("visibility_mode")
    if mode not in {"public", "hidden", "locked"}:
        raise HTTPException(status_code=400, detail="visibility_mode 不合法")
    with db() as conn:
        row = ensure_world_instance(conn, user)
        conn.execute("UPDATE world_instances SET visibility_mode = ?, updated_at = ? WHERE id = ?", (mode, utc_now(), row["id"]))
        row = conn.execute("SELECT * FROM world_instances WHERE id = ?", (row["id"],)).fetchone()
        return serialize_world_instance(conn, row)


@app.post("/api/v1/worlds/instance/me/policy")
async def my_world_policy(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    with db() as conn:
        row = ensure_world_instance(conn, user)
        conn.execute(
            "UPDATE world_instances SET allow_offline_travel = ?, updated_at = ? WHERE id = ?",
            (1 if data.get("allow_offline_travel") else 0, utc_now(), row["id"]),
        )
        row = conn.execute("SELECT * FROM world_instances WHERE id = ?", (row["id"],)).fetchone()
        return serialize_world_instance(conn, row)


@app.post("/api/v1/worlds/instance/me/offline-prompt")
async def my_world_offline_prompt(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    with db() as conn:
        row = ensure_world_instance(conn, user)
        conn.execute(
            "UPDATE world_instances SET offline_agent_prompt = ?, updated_at = ? WHERE id = ?",
            (data.get("offline_agent_prompt"), utc_now(), row["id"]),
        )
        row = conn.execute("SELECT * FROM world_instances WHERE id = ?", (row["id"],)).fetchone()
        return serialize_world_instance(conn, row)


@app.post("/api/v1/worlds/instance/me/invite-code/regenerate")
def my_world_invite(user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        row = ensure_world_instance(conn, user)
        conn.execute("UPDATE world_instances SET invite_code = ?, updated_at = ? WHERE id = ?", (secrets.token_urlsafe(8), utc_now(), row["id"]))
        row = conn.execute("SELECT * FROM world_instances WHERE id = ?", (row["id"],)).fetchone()
        return serialize_world_instance(conn, row)


@app.get("/api/v1/worlds/instance/list")
def list_world_instances(skip: int = 0, limit: int = 20, visibility: str | None = None, search: str | None = None, user: sqlite3.Row = Depends(get_current_user)) -> list[dict[str, Any]]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT wi.*, u.user_name FROM world_instances wi
            JOIN users u ON u.id = wi.owner_user_id
            WHERE wi.visibility_mode != 'hidden'
            ORDER BY wi.updated_at DESC
            """
        ).fetchall()
        result = []
        for row in rows:
            if visibility and row["visibility_mode"] != visibility:
                continue
            if search and search.lower() not in row["user_name"].lower():
                continue
            presence = owner_presence(conn, int(row["owner_user_id"]))
            result.append(
                {
                    "world_instance_id": row["id"],
                    "owner_player_id": row["owner_user_id"],
                    "owner_username": row["user_name"],
                    "owner_char_id": row["owner_char_id"],
                    "visibility_mode": row["visibility_mode"],
                    "allow_offline_travel": bool(row["allow_offline_travel"]),
                    "allow_map_overwrite": bool(row["allow_map_overwrite"]),
                    "owner_online": presence["owner_online"],
                    "owner_last_heartbeat_at": presence["owner_last_heartbeat_at"],
                    "revision": row["revision"],
                    "created_at": row["created_at"],
                }
            )
    return result[skip : skip + limit]


@app.get("/api/v1/worlds/instance/{world_instance_id}/map/{map_id}/graph")
def map_graph(world_instance_id: int, map_id: int, session_id: int | None = None, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (world_instance_id,)).fetchone()
        if not instance:
            raise HTTPException(status_code=404, detail="世界实例不存在")
        session = None
        if session_id is not None:
            session = require_travel_session(conn, session_id, user)
            if int(session["target_world_instance_id"]) != int(world_instance_id):
                raise api_error(403, "SESSION_FORBIDDEN", "穿越会话不属于该世界")
        if not is_known_map_id(conn, instance, int(map_id)):
            raise api_error(400, "INVALID_MAP_ID", "地图不存在")
        _, char = get_owner_info(conn, instance)
        base_info = json_loads(char["base_info"], {}) if char else {}
        return {
            "map_id": int(map_id),
            "map_key": "main",
            "viewer_poi_id": coerce_poi_id(session["current_poi_id"]) if session else 1,
            "world_info": derived_world_view(conn, instance),
            "owner_base_info": base_info,
            "owner_location": owner_location_from_save(char),
            "relationships": owner_relationships_from_save(char),
            "overlay_base": overlay_base(conn, instance),
        }


@app.post("/api/v1/worlds/instance/{world_instance_id}/action")
async def world_action(world_instance_id: int, request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    action_type = data.get("action_type")
    intent = data.get("intent") or {}
    with db() as conn:
        instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (world_instance_id,)).fetchone()
        if not instance:
            raise HTTPException(status_code=404, detail="世界实例不存在")
        session = require_travel_session(conn, data.get("session_id"), user, require_active=True)
        if int(session["target_world_instance_id"]) != int(world_instance_id):
            raise api_error(403, "SESSION_FORBIDDEN", "穿越会话不属于该世界")

        if action_type == "move":
            try:
                to_map_id = int(intent.get("to_map_id") or session["current_map_id"] or 1)
            except (TypeError, ValueError):
                raise api_error(400, "INVALID_MAP_ID", "地图 ID 不合法")
            if not is_known_map_id(conn, instance, to_map_id):
                raise api_error(400, "INVALID_MAP_ID", "地图不存在")
            to_poi_id = intent.get("to_poi_id") or session["current_poi_id"] or "1"
            now = utc_now()
            conn.execute(
                """
                UPDATE travel_sessions
                SET current_map_id = ?, current_poi_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (to_map_id, str(to_poi_id), now, session["id"]),
            )
            append_session_event(
                conn,
                int(session["id"]),
                "world_action_move",
                map_id=to_map_id,
                poi_id=to_poi_id,
                payload={"to_map_id": to_map_id, "to_poi_id": coerce_poi_id(to_poi_id)},
            )
            return {"success": True, "message": "已移动", "new_map_id": to_map_id, "new_poi_id": coerce_poi_id(to_poi_id)}

        if action_type == "map_overwrite":
            if not bool(instance["allow_map_overwrite"]):
                raise api_error(409, "OFFLINE_TRAVEL_DISABLED", "该世界未开启地图覆盖")
            raw_map_id = intent.get("map_id")
            if raw_map_id is None:
                raise api_error(400, "INVALID_MAP_ID", "map_id 必填")
            try:
                map_id = int(raw_map_id)
            except (TypeError, ValueError):
                raise api_error(400, "INVALID_MAP_ID", "map_id 不合法")
            if not is_known_map_id(conn, instance, map_id):
                raise api_error(400, "INVALID_MAP_ID", "地图不存在")
            if map_id != int(session["current_map_id"]):
                raise api_error(409, "MAP_CURSOR_MISMATCH", "只能覆盖当前地图")
            locations = intent.get("locations")
            if not isinstance(locations, list):
                locations = []

            try:
                expected_character_version = int(intent.get("base_character_version"))
                expected_world_revision = int(intent.get("base_world_revision"))
            except (TypeError, ValueError):
                expected_character_version = -1
                expected_world_revision = -1
            current_base = overlay_base(conn, instance)
            if (
                expected_character_version != current_base["character_version"]
                or expected_world_revision != current_base["world_revision"]
            ):
                raise api_error(
                    409,
                    "WORLD_REVISION_CONFLICT",
                    "世界版本已变化",
                    current_character_version=current_base["character_version"],
                    current_world_revision=current_base["world_revision"],
                    expected_character_version=expected_character_version,
                    expected_world_revision=expected_world_revision,
                )

            now = utc_now()
            updated = conn.execute(
                """
                UPDATE world_instances
                SET revision = revision + 1, updated_at = ?
                WHERE id = ?
                  AND owner_char_id = ?
                  AND revision = ?
                """,
                (now, world_instance_id, instance["owner_char_id"], expected_world_revision),
            )
            if updated.rowcount != 1:
                fresh_instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (world_instance_id,)).fetchone()
                fresh_base = overlay_base(conn, fresh_instance)
                raise api_error(
                    409,
                    "WORLD_REVISION_CONFLICT",
                    "世界版本已变化",
                    current_character_version=fresh_base["character_version"],
                    current_world_revision=fresh_base["world_revision"],
                    expected_character_version=expected_character_version,
                    expected_world_revision=expected_world_revision,
                )
            new_revision = expected_world_revision + 1
            cur = conn.execute(
                """
                INSERT INTO world_overlays (
                  world_instance_id, session_id, map_id, character_version,
                  base_world_revision, payload, state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'accepted', ?)
                """,
                (
                    world_instance_id,
                    session["id"],
                    map_id,
                    expected_character_version,
                    expected_world_revision,
                    json_dumps({"locations": locations}),
                    now,
                ),
            )
            append_session_event(
                conn,
                int(session["id"]),
                "map_overwrite",
                map_id=map_id,
                poi_id=session["current_poi_id"],
                payload={"overlay_id": cur.lastrowid, "locations_count": len(locations)},
            )
            updated_instance = conn.execute("SELECT * FROM world_instances WHERE id = ?", (world_instance_id,)).fetchone()
            return {
                "success": True,
                "message": "地图已接收",
                "applied_overlay_id": cur.lastrowid,
                "new_world_revision": new_revision,
                "overlay_base": overlay_base(conn, updated_instance),
            }

        append_session_event(
            conn,
            int(session["id"]),
            f"world_action_{action_type or 'unknown'}",
            map_id=int(session["current_map_id"]),
            poi_id=session["current_poi_id"],
            payload=intent,
        )
        return {"success": True, "message": "操作已记录"}


@app.get("/api/v1/invasion/reports/me")
def invasion_reports(user: sqlite3.Row = Depends(get_current_user)) -> list[Any]:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM invasion_reports
            WHERE owner_user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user["id"],),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "world_instance_id": row["world_instance_id"],
                "session_id": row["session_id"],
                "created_at": row["created_at"],
                "unread": bool(row["unread"]),
                "summary": json_loads(row["summary"], {}),
            }
            for row in rows
        ]


def workshop_out(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    author = conn.execute("SELECT user_name FROM users WHERE id = ?", (row["author_id"],)).fetchone()
    return {
        "id": row["id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "tags": json_loads(row["tags"], []),
        "game_version": row["game_version"],
        "data_version": row["data_version"],
        "author_id": row["author_id"],
        "author_name": author["user_name"] if author else "unknown",
        "downloads": row["downloads"],
        "likes": row["likes"],
        "is_public": bool(row["is_public"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.get("/api/v1/workshop/items")
def workshop_items(type: str | None = None, q: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM workshop_items WHERE is_public = 1 ORDER BY updated_at DESC").fetchall()
        items = [workshop_out(conn, row) for row in rows]
    if type:
        items = [item for item in items if item["type"] == type]
    if q:
        needle = q.lower()
        items = [item for item in items if needle in item["title"].lower() or needle in (item.get("description") or "").lower()]
    total = len(items)
    start = max(page - 1, 0) * page_size
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


@app.get("/api/v1/workshop/my-items")
def my_workshop_items(type: str | None = None, q: str | None = None, page: int = 1, page_size: int = 20, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM workshop_items WHERE author_id = ? ORDER BY updated_at DESC", (user["id"],)).fetchall()
        items = [workshop_out(conn, row) for row in rows]
    if type:
        items = [item for item in items if item["type"] == type]
    if q:
        needle = q.lower()
        items = [item for item in items if needle in item["title"].lower() or needle in (item.get("description") or "").lower()]
    total = len(items)
    start = max(page - 1, 0) * page_size
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


@app.post("/api/v1/workshop/items")
async def create_workshop_item(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    now = utc_now()
    with db() as conn:
        cur = conn.execute(
            """
            INSERT INTO workshop_items (type, title, description, tags, payload, game_version, data_version, author_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("type"),
                data.get("title"),
                data.get("description"),
                json_dumps(data.get("tags") or []),
                json_dumps(data.get("payload")),
                data.get("game_version"),
                data.get("data_version"),
                user["id"],
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM workshop_items WHERE id = ?", (cur.lastrowid,)).fetchone()
        return workshop_out(conn, row)


@app.post("/api/v1/workshop/items/{item_id}/download")
def download_workshop_item(item_id: int) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM workshop_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="工坊项目不存在")
        conn.execute("UPDATE workshop_items SET downloads = downloads + 1 WHERE id = ?", (item_id,))
        updated = conn.execute("SELECT * FROM workshop_items WHERE id = ?", (item_id,)).fetchone()
        return {"item": workshop_out(conn, updated), "payload": json_loads(row["payload"], None)}


@app.delete("/api/v1/workshop/items/{item_id}")
def delete_workshop_item(item_id: int, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, str]:
    with db() as conn:
        row = conn.execute("SELECT * FROM workshop_items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="工坊项目不存在")
        if row["author_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="只能删除自己的项目")
        conn.execute("DELETE FROM workshop_items WHERE id = ?", (item_id,))
    return {"message": "已删除"}


@app.get("/api/v1/prompts/config")
def prompts_config() -> dict[str, Any]:
    return {"prompts": {}, "version": APP_VERSION, "lastUpdated": utc_now()}


@app.post("/api/v1/redemption/validate/{code}")
def redemption_validate(code: str, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    return {"id": 1, "code": code, "times_used": 0, "max_uses": 999999}


@app.post("/api/v1/ai/save")
async def ai_save(request: Request, user: sqlite3.Row = Depends(get_current_user)) -> dict[str, Any]:
    data = await request.json()
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO generated_items (type, content, owner_user_id, created_at) VALUES (?, ?, ?, ?)",
            (data.get("type"), json_dumps(data.get("content")), user["id"], utc_now()),
        )
    return {"message": "已保存自托管生成内容", "saved_id": cur.lastrowid}
