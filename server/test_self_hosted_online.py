from __future__ import annotations

import importlib
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Barrier
from typing import Any

import pytest
from fastapi.testclient import TestClient


PUBLIC_STATES = {"active", "ended", "evicted", "rejected"}


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("XIANTU_DB_PATH", str(tmp_path / "xiantu-smoke.db"))
    monkeypatch.setenv("XIANTU_SECRET_KEY", "self-hosted-smoke-secret-a")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()
    with TestClient(main.app) as test_client:
        yield test_client


@dataclass
class Actor:
    username: str
    token: str
    char_id: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


def assert_ok(response: Any) -> dict[str, Any]:
    assert response.status_code < 400, response.text
    return response.json()


def assert_error_code(response: Any, status_code: int, code: str) -> dict[str, Any]:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body.get("code") == code or body.get("detail", {}).get("code") == code
    return body


def assert_has_keys(body: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in body]
    assert not missing, f"response missing contract keys {missing}: {body}"


def active_server_module() -> Any:
    return sys.modules["server.main"]


def mark_user_offline(username: str) -> None:
    main = active_server_module()
    with main.db() as conn:
        user = conn.execute("SELECT * FROM users WHERE user_name = ?", (username,)).fetchone()
        if user:
            conn.execute("DELETE FROM presence WHERE user_id = ?", (user["id"],))


def register_login_create_role(client: TestClient, username: str) -> Actor:
    password = f"{username}-pass"
    assert_ok(client.post("/api/v1/auth/register", json={"user_name": username, "password": password}))
    token = assert_ok(client.post("/api/v1/auth/token", json={"username": username, "password": password}))[
        "access_token"
    ]
    actor = Actor(username=username, token=token, char_id=f"{username}-char")
    assert_ok(
        client.post(
            "/api/v1/characters/create",
            headers=actor.headers,
            json={
                "char_id": actor.char_id,
                "base_info": {"name": username, "cultivation_level": "qi-refining"},
            },
        )
    )
    assert_ok(
        client.put(
            f"/api/v1/characters/{actor.char_id}/save",
            headers=actor.headers,
            json={
                "save_data": {
                    "onlineState": None,
                    "角色": {
                        "位置": {
                            "描述": f"{username} cave",
                            "x": 320,
                            "y": 180,
                        }
                    },
                    "社交": {
                        "关系": {
                            "守门人": {
                                "名字": "守门人",
                                "好感度": 5,
                            }
                        }
                    },
                },
                "world_map": {
                    "world_name": f"{username} world",
                    "locations": [
                        {"id": 1, "map_id": 1, "name": "gate"},
                        {"id": 2, "map_id": 2, "name": "back-mountain"},
                    ],
                },
                "game_time": "year-1-spring",
            },
        )
    )
    return actor


def create_online_pair(client: TestClient) -> tuple[Actor, Actor, dict[str, Any]]:
    owner = register_login_create_role(client, "owner")
    mark_user_offline(owner.username)
    traveler = register_login_create_role(client, "traveler")
    start = assert_ok(
        client.post(
            "/api/v1/travel/start",
            headers=traveler.headers,
            json={"target_username": owner.username},
        )
    )
    return owner, traveler, start


def post_world_action(
    client: TestClient,
    traveler: Actor,
    world_instance_id: int,
    session_id: int,
    action_type: str,
    intent: dict[str, Any],
) -> Any:
    return client.post(
        f"/api/v1/worlds/instance/{world_instance_id}/action",
        headers=traveler.headers,
        json={"session_id": session_id, "action_type": action_type, "intent": intent},
    )


def overlay_base_from(probe: dict[str, Any]) -> dict[str, int]:
    overlay_base = probe.get("overlay_base")
    assert isinstance(overlay_base, dict), f"overlay_base must be returned by contract probe: {probe}"
    assert isinstance(overlay_base.get("character_version"), int)
    assert isinstance(overlay_base.get("world_revision"), int)
    return overlay_base


def location_names(world_info: dict[str, Any]) -> set[str]:
    locations = world_info.get("地点信息") or world_info.get("locations") or []
    return {str(item.get("name") or item.get("名称")) for item in locations if isinstance(item, dict)}


def apply_map_overwrite(
    client: TestClient,
    traveler: Actor,
    start_or_probe: dict[str, Any],
    map_id: int,
    locations: list[dict[str, Any]],
) -> dict[str, Any]:
    base = overlay_base_from(start_or_probe)
    return assert_ok(
        post_world_action(
            client,
            traveler,
            int(start_or_probe["target_world_instance_id"]),
            int(start_or_probe["session_id"]),
            "map_overwrite",
            {
                "map_id": map_id,
                "locations": locations,
                "base_character_version": base["character_version"],
                "base_world_revision": base["world_revision"],
            },
        )
    )


def test_register_login_and_create_owner_traveler_roles(client: TestClient) -> None:
    owner = register_login_create_role(client, "owner")
    traveler = register_login_create_role(client, "traveler")

    assert_ok(client.get("/api/v1/auth/me", headers=owner.headers))["user_name"] == owner.username
    assert_ok(client.get("/api/v1/auth/me", headers=traveler.headers))["user_name"] == traveler.username
    stats = assert_ok(client.get("/api/v1/stats"))
    assert stats["version"]
    assert stats["total_users"] >= 2
    assert stats["total_characters"] >= 2
    assert stats["online_users"] >= 2
    assert stats["total_worlds"] >= 2


def test_backend_requires_non_default_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XIANTU_SECRET_KEY", raising=False)
    sys.modules.pop("server.main", None)
    with pytest.raises(RuntimeError, match="XIANTU_SECRET_KEY"):
        importlib.import_module("server.main")

    compose = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    assert "change-me-local-xiantu" not in compose.read_text(encoding="utf-8")
    assert "XIANTU_SECRET_KEY: ${XIANTU_SECRET_KEY:?" in compose.read_text(encoding="utf-8")
    env_example = Path(__file__).resolve().parents[1] / "server" / ".env.example"
    assert "XIANTU_SECRET_KEY=" in env_example.read_text(encoding="utf-8")
    assert "replace-with-a-long-random-secret" not in env_example.read_text(encoding="utf-8")

    for placeholder in ["change-me-local-xiantu", "replace-with-a-long-random-secret"]:
        monkeypatch.setenv("XIANTU_SECRET_KEY", placeholder)
        sys.modules.pop("server.main", None)
        with pytest.raises(RuntimeError, match="XIANTU_SECRET_KEY"):
            importlib.import_module("server.main")


def test_travel_start_returns_current_cursor_and_overlay_base(client: TestClient) -> None:
    _, _, start = create_online_pair(client)

    assert_has_keys(start, "state", "current_map_id", "current_poi_id", "overlay_base")
    assert start["current_map_id"] == start["entry_map_id"]
    assert start["current_poi_id"] == start["entry_poi_id"]
    overlay_base_from(start)
    assert start["state"] == "active"


def test_move_updates_current_cursor_returned_by_active_and_status(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_instance_id = start["target_world_instance_id"]

    assert_ok(
        post_world_action(
            client,
            traveler,
            world_instance_id,
            session_id,
            "move",
            {"to_map_id": 2, "to_poi_id": 2},
        )
    )

    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert_has_keys(active, "current_map_id", "current_poi_id")
    assert_has_keys(status, "current_map_id", "current_poi_id")
    assert active["current_map_id"] == 2
    assert active["current_poi_id"] == 2
    assert status["current_map_id"] == 2
    assert status["current_poi_id"] == 2


def test_map_overwrite_rejects_missing_or_non_current_map_id(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_instance_id = start["target_world_instance_id"]
    base = overlay_base_from(start)

    missing = post_world_action(
        client,
        traveler,
        world_instance_id,
        session_id,
        "map_overwrite",
        {
            "locations": [{"id": 1, "name": "rewritten-gate"}],
            "base_character_version": base["character_version"],
            "base_world_revision": base["world_revision"],
        },
    )
    assert_error_code(missing, 400, "INVALID_MAP_ID")

    mismatch = post_world_action(
        client,
        traveler,
        world_instance_id,
        session_id,
        "map_overwrite",
        {
            "map_id": 2,
            "locations": [{"id": 2, "name": "rewritten-back-mountain"}],
            "base_character_version": base["character_version"],
            "base_world_revision": base["world_revision"],
        },
    )
    assert_error_code(mismatch, 409, "MAP_CURSOR_MISMATCH")

    unknown = post_world_action(
        client,
        traveler,
        world_instance_id,
        session_id,
        "map_overwrite",
        {
            "map_id": 999,
            "locations": [],
            "base_character_version": base["character_version"],
            "base_world_revision": base["world_revision"],
        },
    )
    assert_error_code(unknown, 400, "INVALID_MAP_ID")


def test_map_overwrite_applies_overlay_and_rejects_stale_world_revision(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_instance_id = start["target_world_instance_id"]
    base = overlay_base_from(start)
    intent = {
        "map_id": start["current_map_id"],
        "locations": [{"id": 1, "name": "traveler-rewritten-gate"}],
        "base_character_version": base["character_version"],
        "base_world_revision": base["world_revision"],
    }

    applied = assert_ok(post_world_action(client, traveler, world_instance_id, session_id, "map_overwrite", intent))
    assert applied["success"] is True
    assert isinstance(applied["applied_overlay_id"], int)
    assert applied["new_world_revision"] == base["world_revision"] + 1
    assert applied["overlay_base"]["world_revision"] == applied["new_world_revision"]

    conflict = post_world_action(client, traveler, world_instance_id, session_id, "map_overwrite", intent)
    body = assert_error_code(conflict, 409, "WORLD_REVISION_CONFLICT")
    assert body["current_world_revision"] == applied["new_world_revision"]
    assert body["expected_world_revision"] == base["world_revision"]
    assert "current_character_version" in body
    assert "expected_character_version" in body


def test_map_overwrite_concurrent_same_base_accepts_only_one_overlay(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_instance_id = start["target_world_instance_id"]
    base = overlay_base_from(start)
    barrier = Barrier(2)

    def submit(index: int) -> tuple[int, dict[str, Any]]:
        barrier.wait(timeout=5)
        response = post_world_action(
            client,
            traveler,
            world_instance_id,
            session_id,
            "map_overwrite",
            {
                "map_id": start["current_map_id"],
                "locations": [{"id": index, "name": f"concurrent-{index}"}],
                "base_character_version": base["character_version"],
                "base_world_revision": base["world_revision"],
            },
        )
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, [1, 2]))

    success = [body for status, body in results if status == 200]
    conflicts = [body for status, body in results if status == 409]
    assert len(success) == 1, results
    assert len(conflicts) == 1, results
    assert conflicts[0]["code"] == "WORLD_REVISION_CONFLICT"
    assert conflicts[0]["current_world_revision"] == success[0]["new_world_revision"]
    assert success[0]["new_world_revision"] == base["world_revision"] + 1

    main = active_server_module()
    with main.db() as conn:
        overlays = conn.execute(
            "SELECT COUNT(*) AS count FROM world_overlays WHERE world_instance_id = ? AND state = 'accepted'",
            (world_instance_id,),
        ).fetchone()
        instance = conn.execute("SELECT revision FROM world_instances WHERE id = ?", (world_instance_id,)).fetchone()
    assert overlays["count"] == 1
    assert instance["revision"] == success[0]["new_world_revision"]


def test_end_active_terminal_and_ack_terminal_are_idempotent(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]

    assert_ok(client.post("/api/v1/travel/end", headers=traveler.headers, json={"session_id": session_id}))

    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert active is not None, "terminal session must remain visible on /travel/active until ack-terminal"
    assert_has_keys(active, "session_id", "state", "end_reason")
    assert_has_keys(status, "session_id", "state", "end_reason")
    assert active["session_id"] == session_id
    assert active["state"] == "ended"
    assert active["end_reason"] == "normal"
    assert status["state"] == "ended"

    first_ack = assert_ok(
        client.post("/api/v1/travel/ack-terminal", headers=traveler.headers, json={"session_id": session_id})
    )
    second_ack = assert_ok(
        client.post("/api/v1/travel/ack-terminal", headers=traveler.headers, json={"session_id": session_id})
    )
    assert first_ack == {"success": True, "cleared": True, "reason": "acknowledged"}
    assert second_ack == {"success": True, "cleared": False, "reason": "already_cleared"}
    assert client.get("/api/v1/travel/active", headers=traveler.headers).json() is None
    assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))["state"] == "ended"


def test_ack_terminal_reports_superseded_after_new_active_replaces_marker(client: TestClient) -> None:
    owner, traveler, start = create_online_pair(client)
    first_session_id = start["session_id"]

    assert_ok(client.post("/api/v1/travel/end", headers=traveler.headers, json={"session_id": first_session_id}))
    mark_user_offline(owner.username)
    second = assert_ok(
        client.post(
            "/api/v1/travel/start",
            headers=traveler.headers,
            json={"target_username": owner.username},
        )
    )
    assert second["session_id"] != first_session_id

    ack = assert_ok(
        client.post("/api/v1/travel/ack-terminal", headers=traveler.headers, json={"session_id": first_session_id})
    )
    assert ack == {"success": True, "cleared": False, "reason": "superseded_by_new_active"}
    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    assert active["session_id"] == second["session_id"]


def test_owner_heartbeat_evicts_active_sessions(client: TestClient) -> None:
    owner, traveler, start = create_online_pair(client)
    session_id = start["session_id"]

    assert_ok(client.post("/api/v1/presence/heartbeat", headers=owner.headers))

    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert active is not None, "owner-online eviction must remain visible on /travel/active until ack-terminal"
    assert_has_keys(active, "state", "end_reason")
    assert_has_keys(status, "state", "end_reason")
    assert active["state"] == "evicted"
    assert active["end_reason"] == "owner_online"
    assert status["state"] == "evicted"
    assert status["end_reason"] == "owner_online"


def test_owner_login_evicts_active_sessions(client: TestClient) -> None:
    owner, traveler, start = create_online_pair(client)
    session_id = start["session_id"]

    assert_ok(
        client.post(
            "/api/v1/auth/token",
            json={"username": owner.username, "password": f"{owner.username}-pass"},
        )
    )

    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert active["state"] == "evicted"
    assert active["end_reason"] == "owner_online"
    assert status["state"] == "evicted"
    assert status["end_reason"] == "owner_online"


def test_saved_online_state_round_trips_but_server_cursor_and_terminal_state_win(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_instance_id = start["target_world_instance_id"]
    stale_online_state = {
        "模式": "联机",
        "房间ID": str(session_id),
        "当前地图ID": 999,
        "当前POI": "stale-poi",
        "穿越目标": {
            "世界ID": world_instance_id,
            "主人用户名": "owner",
            "允许地图覆盖": True,
            "overlay_base": {"character_version": 0, "world_revision": 0},
        },
    }

    assert_ok(
        client.put(
            f"/api/v1/characters/{traveler.char_id}/save",
            headers=traveler.headers,
            json={
                "save_data": {"系统": {"联机": stale_online_state}},
                "world_map": {
                    "world_name": "traveler world",
                    "locations": [{"id": 1, "map_id": 1, "name": "traveler-gate"}],
                },
                "game_time": "year-1-summer",
            },
        )
    )
    reloaded = assert_ok(client.get(f"/api/v1/characters/{traveler.char_id}", headers=traveler.headers))
    assert reloaded["game_save"]["save_data"]["系统"]["联机"] == stale_online_state

    assert_ok(
        post_world_action(
            client,
            traveler,
            world_instance_id,
            session_id,
            "move",
            {"to_map_id": 2, "to_poi_id": 2},
        )
    )
    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert active["current_map_id"] == 2
    assert active["current_poi_id"] == 2
    assert status["current_map_id"] == 2
    assert status["current_poi_id"] == 2

    assert_ok(client.post("/api/v1/travel/end", headers=traveler.headers, json={"session_id": session_id}))
    terminal_active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    terminal_status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert terminal_active["state"] == "ended"
    assert terminal_status["state"] == "ended"
    assert terminal_active["current_map_id"] == 2
    assert terminal_status["current_map_id"] == 2


def test_derived_world_uses_latest_overlay_per_map_and_expires_on_character_version_change(client: TestClient) -> None:
    owner, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    world_id = start["target_world_instance_id"]

    first = apply_map_overwrite(client, traveler, start, 1, [{"id": 1, "map_id": 1, "name": "gate-v1"}])
    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    assert overlay_base_from(active)["world_revision"] == first["new_world_revision"]

    second = apply_map_overwrite(client, traveler, active, 1, [{"id": 1, "map_id": 1, "name": "gate-v2"}])
    assert second["new_world_revision"] == first["new_world_revision"] + 1

    assert_ok(
        post_world_action(
            client,
            traveler,
            world_id,
            session_id,
            "move",
            {"to_map_id": 2, "to_poi_id": 2},
        )
    )
    active = assert_ok(client.get("/api/v1/travel/active", headers=traveler.headers))
    third = apply_map_overwrite(client, traveler, active, 2, [{"id": 2, "map_id": 2, "name": "back-v1"}])

    snapshot = assert_ok(client.get(f"/api/v1/travel/snapshot/{session_id}", headers=traveler.headers))
    graph = assert_ok(client.get(f"/api/v1/worlds/instance/{world_id}/map/2/graph?session_id={session_id}", headers=traveler.headers))
    snapshot_names = location_names(snapshot["world_info"])
    graph_names = location_names(graph["world_info"])
    assert "gate-v2" in snapshot_names
    assert "gate-v1" not in snapshot_names
    assert "back-v1" in snapshot_names
    assert snapshot["world_info"] == graph["world_info"]
    assert snapshot["owner_location"] == graph["owner_location"]
    assert snapshot["owner_location"]["描述"] == "owner cave"
    assert snapshot["owner_base_info"] == graph["owner_base_info"]
    assert snapshot["relationships"] == graph["relationships"]
    assert "守门人" in snapshot["relationships"]

    assert_ok(
        client.put(
            f"/api/v1/characters/{owner.char_id}/save",
            headers=owner.headers,
            json={
                "save_data": {"onlineState": None},
                "world_map": {
                    "world_name": "owner world v2",
                    "locations": [
                        {"id": 1, "map_id": 1, "name": "gate-base-v2"},
                        {"id": 2, "map_id": 2, "name": "back-base-v2"},
                    ],
                },
                "game_time": "year-2-spring",
            },
        )
    )
    after_version_change = assert_ok(client.get(f"/api/v1/travel/snapshot/{session_id}", headers=traveler.headers))
    names_after = location_names(after_version_change["world_info"])
    assert "gate-base-v2" in names_after
    assert "back-base-v2" in names_after
    assert "gate-v2" not in names_after
    assert "back-v1" not in names_after
    assert overlay_base_from(after_version_change)["character_version"] == third["overlay_base"]["character_version"] + 1


def test_single_online_role_limit_and_migration_prefer_owner_char_then_latest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "xiantu-role-migration.db"
    monkeypatch.setenv("XIANTU_DB_PATH", str(db_path))
    monkeypatch.setenv("XIANTU_SECRET_KEY", "role-migration-secret")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()

    with TestClient(main.app) as app_client:
        owner = register_login_create_role(app_client, "role_owner")
        limit = app_client.post(
            "/api/v1/characters/create",
            headers=owner.headers,
            json={"char_id": "second-role", "base_info": {"name": "second"}},
        )
        assert_error_code(limit, 409, "ONLINE_CHARACTER_LIMIT")

    with main.db() as conn:
        conn.execute("UPDATE world_instances SET owner_char_id = NULL")
    main.init_db()
    with main.db() as conn:
        migrated = conn.execute("SELECT owner_char_id FROM world_instances WHERE owner_user_id = 1").fetchone()
        assert migrated["owner_char_id"] == "role_owner-char"

    with main.db() as conn:
        now = main.utc_now()
        conn.execute(
            "INSERT INTO users (user_name, password_hash, created_at) VALUES (?, ?, ?)",
            ("legacy", main.hash_password("legacy-pass"), now),
        )
        legacy_user = conn.execute("SELECT * FROM users WHERE user_name = 'legacy'").fetchone()
        conn.execute(
            "INSERT INTO characters (char_id, user_id, base_info, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("legacy-old", legacy_user["id"], "{}", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO characters (char_id, user_id, base_info, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("legacy-new", legacy_user["id"], "{}", "2026-01-02T00:00:00+00:00", "2026-01-02T00:00:00+00:00"),
        )
        conn.execute(
            """
            INSERT INTO world_instances (owner_user_id, owner_char_id, invite_code, created_at, updated_at)
            VALUES (?, NULL, 'invite', ?, ?)
            """,
            (legacy_user["id"], now, now),
        )
    main.init_db()
    with main.db() as conn:
        migrated = conn.execute(
            """
            SELECT owner_char_id FROM world_instances
            JOIN users ON users.id = world_instances.owner_user_id
            WHERE users.user_name = 'legacy'
            """
        ).fetchone()
        assert migrated["owner_char_id"] == "legacy-new"


def test_public_state_matrix_excludes_expired(client: TestClient) -> None:
    _, traveler, start = create_online_pair(client)
    session_id = start["session_id"]
    main = active_server_module()

    with main.db() as conn:
        conn.execute(
            """
            UPDATE travel_sessions
            SET state = 'expired',
                end_reason = 'legacy-weird',
                terminal_acknowledged_at = NULL,
                terminal_marker_expires_at = '9999-01-01T00:00:00+00:00'
            WHERE id = ?
            """,
            (session_id,),
        )
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))

    assert status["state"] in PUBLIC_STATES
    assert status["state"] == "evicted"
    assert status["end_reason"] is None
    assert client.get("/api/v1/travel/active", headers=traveler.headers).json() is None

    with main.db() as conn:
        conn.execute("UPDATE travel_sessions SET state = 'settled' WHERE id = ?", (session_id,))
    status = assert_ok(client.get(f"/api/v1/travel/status/{session_id}", headers=traveler.headers))
    assert status["state"] == "ended"


def test_secret_key_rotation_invalidates_old_token_and_allows_new_login(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "xiantu-secret-rotation.db"
    monkeypatch.setenv("XIANTU_DB_PATH", str(db_path))
    monkeypatch.setenv("XIANTU_SECRET_KEY", "secret-before-rotation")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()
    with TestClient(main.app) as client_before:
        assert_ok(client_before.post("/api/v1/auth/register", json={"user_name": "rotator", "password": "rotator-pass"}))
        old_token = assert_ok(
            client_before.post("/api/v1/auth/token", json={"username": "rotator", "password": "rotator-pass"})
        )["access_token"]

    monkeypatch.setenv("XIANTU_SECRET_KEY", "secret-after-rotation")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()
    with TestClient(main.app) as client_after:
        old_token_response = client_after.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {old_token}"})
        assert old_token_response.status_code == 401
        new_token = assert_ok(
            client_after.post("/api/v1/auth/token", json={"username": "rotator", "password": "rotator-pass"})
        )["access_token"]
        assert_ok(client_after.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}))[
            "user_name"
        ] == "rotator"


def test_named_volume_database_backup_restore_and_old_records_remain_readable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    db_path = data_dir / "xiantu.db"
    backup_path = tmp_path / "xiantu.db.backup"
    monkeypatch.setenv("XIANTU_DB_PATH", str(db_path))
    monkeypatch.setenv("XIANTU_SECRET_KEY", "backup-restore-secret")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()

    with TestClient(main.app) as app_client:
        original = register_login_create_role(app_client, "backup_owner")
        assert db_path.exists()
        shutil.copy2(db_path, backup_path)
        extra = register_login_create_role(app_client, "temporary_user")
        assert_ok(app_client.get("/api/v1/auth/me", headers=extra.headers))["user_name"] == "temporary_user"

    shutil.copy2(backup_path, db_path)
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()
    with TestClient(main.app) as restored_client:
        token = assert_ok(
            restored_client.post(
                "/api/v1/auth/token",
                json={"username": "backup_owner", "password": "backup_owner-pass"},
            )
        )["access_token"]
        assert_ok(restored_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}))[
            "user_name"
        ] == original.username
        missing = restored_client.post(
            "/api/v1/auth/token",
            json={"username": "temporary_user", "password": "temporary_user-pass"},
        )
        assert missing.status_code == 401


def test_init_db_is_idempotent_and_rolls_back_failed_migration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "xiantu-migration.db"
    monkeypatch.setenv("XIANTU_DB_PATH", str(db_path))
    monkeypatch.setenv("XIANTU_SECRET_KEY", "migration-secret")
    sys.modules.pop("server.main", None)
    main = importlib.import_module("server.main")
    main.init_db()
    main.init_db()

    with main.db() as conn:
        now = main.utc_now()
        conn.execute(
            "INSERT INTO users (user_name, password_hash, created_at) VALUES (?, ?, ?)",
            ("rollback_owner", main.hash_password("rollback-pass"), now),
        )
        user = conn.execute("SELECT * FROM users WHERE user_name = 'rollback_owner'").fetchone()
        conn.execute(
            "INSERT INTO characters (char_id, user_id, base_info, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("rollback-char", user["id"], "{}", now, now),
        )
        conn.execute(
            """
            INSERT INTO world_instances (owner_user_id, owner_char_id, invite_code, created_at, updated_at)
            VALUES (?, NULL, 'rollback-invite', ?, ?)
            """,
            (user["id"], now, now),
        )

    def failing_migration(conn: sqlite3.Connection) -> None:
        conn.execute("UPDATE world_instances SET owner_char_id = 'partial-write' WHERE invite_code = 'rollback-invite'")
        raise RuntimeError("forced migration failure")

    monkeypatch.setattr(main, "migrate_canonical_online_roles", failing_migration)
    with pytest.raises(RuntimeError):
        main.init_db()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT owner_char_id FROM world_instances WHERE invite_code = 'rollback-invite'").fetchone()
        assert row["owner_char_id"] is None


def test_frontend_online_contract_consumers_use_authoritative_cursor_and_terminal_ack() -> None:
    root = Path(__file__).resolve().parents[1]
    sources = {
        path: (root / path).read_text(encoding="utf-8")
        for path in [
            "src/services/httpClient.ts",
            "src/services/api/onlineTravel.ts",
            "src/components/dashboard/OnlineTravelPanel.vue",
            "src/components/dashboard/OnlineTravelMapPanel.vue",
            "src/components/dashboard/WorldMapRoute.vue",
            "src/components/dashboard/GameMapPanel.vue",
            "src/utils/AIBidirectionalSystem.ts",
            "src/components/dashboard/MainGamePanel.vue",
            "src/App.vue",
            "webpack.config.js",
            "游戏介绍.html",
        ]
    }

    api = sources["src/services/api/onlineTravel.ts"]
    assert "state: 'active' | 'ended' | 'evicted' | 'rejected'" in api
    assert "'settled'" not in api
    assert "current_map_id: number" in api
    assert "current_poi_id: number" in api
    assert "ackTerminalTravel" in api
    assert "base_character_version" in api
    assert "base_world_revision" in api
    http_client = sources["src/services/httpClient.ts"]
    assert "class HttpRequestError" in http_client
    assert "payload: unknown" in http_client
    assert "extractErrorCodeFromBody" in http_client

    panel = sources["src/components/dashboard/OnlineTravelPanel.vue"]
    for needle in [
        "ackTerminalTravel",
        "extractConflictOverlayBase",
        "WORLD_REVISION_CONFLICT",
        "isTerminalTravelState(activeSession.state)",
        "isTerminalTravelState(status.state)",
        "getSessionMapId(session.value)",
        "当前地图ID",
        "当前POI",
        "离线代理提示词",
        "角色信息",
        "overlay_base",
        "overlayBase?.character_version",
        "overlayBase?.world_revision",
        "备份角色ID不匹配，跳过部分恢复",
        "clearLocalOnlineTravelState",
        "backup_character_mismatch",
        "full_backup_character_mismatch",
        "missing_backup",
    ]:
        assert needle in panel
    assert "备份角色ID不匹配，但仍然恢复" not in panel
    assert panel.index("await ackTerminalTravel(endedSessionId)") < panel.index("await restoreWorldBackup({ persist: true })")
    full_mismatch_start = panel.index("完整备份角色ID不匹配，跳过完整恢复")
    assert panel.index("await clearFullBackup()", full_mismatch_start) < panel.index(
        "full_backup_character_mismatch", full_mismatch_start
    )
    mismatch_start = panel.index("备份角色ID不匹配，跳过部分恢复")
    assert panel.index("localStorage.removeItem(`${onlineBackupPrefix}latest`)", mismatch_start) < panel.index(
        "backup_character_mismatch", mismatch_start
    )

    assert "endTravelBeacon" not in sources["src/App.vue"]
    assert "active.current_map_id ?? active.entry_map_id" in sources["src/components/dashboard/OnlineTravelMapPanel.vue"]
    assert "online?.模式 === '联机' && !!online?.房间ID" in sources["src/components/dashboard/WorldMapRoute.vue"]
    assert "穿越目标?.世界主人位置" in sources["src/components/dashboard/GameMapPanel.vue"]
    assert "穿越目标" in sources["src/utils/AIBidirectionalSystem.ts"]
    assert "online?.模式 === '联机' && !!online?.房间ID" in sources["src/components/dashboard/MainGamePanel.vue"]
    assert "const API_BASE = '/api/v1'" in sources["游戏介绍.html"]
    assert "CopyIntroPage" in sources["webpack.config.js"]
