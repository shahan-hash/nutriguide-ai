"""Local SQLite store: profiles + meal-plan history (separate per profile).

* One database file: data/processed/meal_history.db (created automatically).
* Every row is tied to a profile id, so two profiles never see each other's
  history.  A profile id is just a local nickname, NOT a login or password.
* Set the environment variable NUTRIGUIDE_DB to use another database file
  (the automated tests do this so they never touch your real history).
"""
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "processed" / "meal_history.db"
DEFAULT_PROFILE_ID = "my-profile"
MEAL_NAMES = ["Breakfast", "Lunch", "Dinner"]


def db_path():
    override = os.environ.get("NUTRIGUIDE_DB")
    return Path(override) if override else DEFAULT_DB_PATH


def normalize_profile_id(profile_id):
    """'  Rahul  Kumar ' -> 'rahul kumar' (case-insensitive, trimmed)."""
    text = re.sub(r"\s+", " ", str(profile_id or "")).strip().lower()
    return text or DEFAULT_PROFILE_ID


def _connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("""CREATE TABLE IF NOT EXISTS meal_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        meal_plan_json TEXT NOT NULL
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS profiles (
        profile_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        settings_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    connection.commit()
    return connection


def _json_default(value):
    """Make numpy numbers JSON friendly."""
    try:
        return value.item()
    except AttributeError:
        return str(value)


def _plan_has_foods(meal_plan):
    if not isinstance(meal_plan, dict):
        return False
    for meal in meal_plan.values():
        items = meal.get("foods", []) if isinstance(meal, dict) else meal
        if items:
            return True
    return False


# --------------------------------------------------------------------------
# PROFILES
# --------------------------------------------------------------------------

def save_profile_settings(profile_id, settings, display_name=None):
    pid = normalize_profile_id(profile_id)
    name = (display_name or str(profile_id or pid)).strip() or pid
    payload = json.dumps(settings or {}, ensure_ascii=False, default=_json_default)
    now = datetime.now().isoformat(timespec="seconds")
    with closing(_connect()) as connection, connection:
        connection.execute(
            """INSERT INTO profiles(profile_id, display_name, settings_json, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(profile_id) DO UPDATE SET
                 display_name = excluded.display_name,
                 settings_json = excluded.settings_json,
                 updated_at = excluded.updated_at""",
            (pid, name, payload, now),
        )
    return pid


def load_profile_settings(profile_id):
    """Saved settings dict for this profile, or None if it has none."""
    pid = normalize_profile_id(profile_id)
    with closing(_connect()) as connection:
        row = connection.execute(
            "SELECT settings_json FROM profiles WHERE profile_id = ?", (pid,)
        ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None


def list_profiles():
    """[(profile_id, display_name)] for every known profile (A-Z)."""
    with closing(_connect()) as connection:
        saved = connection.execute(
            "SELECT profile_id, display_name FROM profiles"
        ).fetchall()
        in_history = connection.execute(
            "SELECT DISTINCT profile_id FROM meal_history"
        ).fetchall()

    result = {pid: name for pid, name in saved}
    for (pid,) in in_history:
        result.setdefault(normalize_profile_id(pid), pid)
    return sorted(result.items(), key=lambda pair: pair[0])


# --------------------------------------------------------------------------
# MEAL HISTORY
# --------------------------------------------------------------------------

def save_meal_plan(profile_id, meal_plan, created_at=None):
    """Store a plan for this profile.  Returns the new row id (or None)."""
    if not _plan_has_foods(meal_plan):
        return None
    pid = normalize_profile_id(profile_id)
    payload = json.dumps(meal_plan, ensure_ascii=False, default=_json_default)
    stamp = created_at or datetime.now().isoformat(timespec="seconds")
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT INTO meal_history(profile_id, created_at, meal_plan_json) VALUES (?, ?, ?)",
            (pid, stamp, payload),
        )
        return cursor.lastrowid


def update_meal_plan(row_id, profile_id, meal_plan):
    """Overwrite an existing plan (used after Replace so history is not duplicated)."""
    if row_id is None or not _plan_has_foods(meal_plan):
        return False
    pid = normalize_profile_id(profile_id)
    payload = json.dumps(meal_plan, ensure_ascii=False, default=_json_default)
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "UPDATE meal_history SET meal_plan_json = ? WHERE id = ? AND profile_id = ?",
            (payload, row_id, pid),
        )
        return cursor.rowcount > 0


def get_recent_plans(profile_id, days=10, limit=50):
    pid = normalize_profile_id(profile_id)
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    with closing(_connect()) as connection:
        rows = connection.execute(
            """SELECT id, created_at, meal_plan_json FROM meal_history
               WHERE profile_id = ? AND created_at >= ? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (pid, cutoff, limit),
        ).fetchall()

    plans = []
    for row_id, created_at, raw in rows:
        try:
            plans.append({"id": row_id, "created_at": created_at, "meal_plan": json.loads(raw)})
        except (TypeError, json.JSONDecodeError):
            continue
    return plans


def _items_of(meal):
    return meal.get("foods", []) if isinstance(meal, dict) else (meal or [])


def get_recent_meals(profile_id, days=10):
    """{'Breakfast': [[food names], ...], ...}, most recent plan first."""
    recent = {meal: [] for meal in MEAL_NAMES}
    for plan in get_recent_plans(profile_id, days=days):
        for meal in MEAL_NAMES:
            names = [
                str(item.get("food_name") or "").strip()
                for item in _items_of(plan["meal_plan"].get(meal))
                if isinstance(item, dict) and item.get("food_name")
            ]
            if names:
                recent[meal].append(names)
    return recent


def get_recent_food_names(profile_id, days=10):
    names = []
    for plan in get_recent_plans(profile_id, days=days):
        for meal in plan["meal_plan"].values():
            for item in _items_of(meal):
                if isinstance(item, dict):
                    name = item.get("food_name") or item.get("food") or item.get("user_food")
                    if name:
                        names.append(str(name).strip().lower())
    return list(dict.fromkeys(names))


def count_plans(profile_id):
    pid = normalize_profile_id(profile_id)
    with closing(_connect()) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM meal_history WHERE profile_id = ?", (pid,)
        ).fetchone()[0]


def clear_history(profile_id):
    """Delete the saved plans of ONE profile (other profiles are untouched)."""
    pid = normalize_profile_id(profile_id)
    with closing(_connect()) as connection, connection:
        cursor = connection.execute("DELETE FROM meal_history WHERE profile_id = ?", (pid,))
        return cursor.rowcount
