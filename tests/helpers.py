"""Shared test helpers.  Tests use the REAL USDA CSV files in data/processed
and a temporary history database (never your real history)."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="nutriguide_tests_")
os.environ["NUTRIGUIDE_DB"] = os.path.join(_TMP, "test_history.db")

from available_foods import load_food_data, match_available_foods  # noqa: E402
from nutrition_targets import calculate_targets  # noqa: E402
from user_profile import create_user_profile  # noqa: E402

FOUR_FOODS = ["Rice", "Dal", "Paneer", "Roti"]


def pantry(foods=None):
    """USDA rows for the typed foods (strict pantry mode pool)."""
    rows, _ = match_available_foods(foods or FOUR_FOODS, data=load_food_data())
    return rows


def targets(custom_meals=None, custom_daily=None):
    return calculate_targets(
        21, "male", 55, 170, "moderate", "maintenance",
        custom_daily_calories=custom_daily, custom_meal_calories=custom_meals,
    )


def profile(**kwargs):
    base = dict(age=21, gender="male", height_cm=170, weight_kg=55,
                activity_level="moderate", goal="maintenance",
                diet_preference="no restriction")
    base.update(kwargs)
    return create_user_profile(**base)


def fresh_db_path():
    return os.environ["NUTRIGUIDE_DB"]
