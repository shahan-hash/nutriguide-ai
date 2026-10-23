"""Calorie-target accuracy check on random profiles (reproducible: fixed seed).

Run from the project folder:   python evaluate.py
Optional:                      python evaluate.py --profiles 40

For every random profile and every meal it compares
    planned kcal (sum of the dishes)   with   the meal calorie target
and prints how close the plans are.  It is read-only: it never touches your
history database.
"""
import argparse
import inspect
import json
import os
import random
import sys
import tempfile

# never write to the real history DB while evaluating
os.environ.setdefault("NUTRIGUIDE_DB", os.path.join(tempfile.mkdtemp(), "eval.db"))
sys.path.insert(0, os.getcwd())

from nutrition_targets import calculate_targets            # noqa: E402
from user_profile import create_user_profile                # noqa: E402
from meal_recommendation import generate_meal_plan          # noqa: E402

SPLIT = {"Breakfast": 0.25, "Lunch": 0.40, "Dinner": 0.35}
PANTRY = ["rice", "dal", "chicken", "egg", "oats", "milk", "potato", "banana"]
ACTIVITY = ["sedentary", "light", "moderate", "active"]
GOALS = ["weight_loss", "maintenance", "weight_gain"]
DIETS = ["no restriction", "vegetarian", "vegan"]


def random_profiles(count, seed=2026):
    rng = random.Random(seed)
    for _ in range(count):
        yield dict(
            age=rng.randint(18, 60), gender=rng.choice(["male", "female"]),
            height_cm=rng.randint(150, 190), weight_kg=rng.randint(45, 100),
            activity_level=rng.choice(ACTIVITY), goal=rng.choice(GOALS),
            diet_preference=rng.choice(DIETS),
        )


def planned_kcal(entry):
    foods = entry.get("foods", []) if isinstance(entry, dict) else entry
    return sum(float(f.get("calories", 0)) for f in foods)


def run(count, pantry_mode):
    accepts_dishes = "max_dishes" in inspect.signature(generate_meal_plan).parameters
    errors, coverage = [], []
    for spec in random_profiles(count):
        targets = calculate_targets(spec["age"], spec["gender"], spec["weight_kg"], spec["height_cm"],
                                    spec["activity_level"], spec["goal"])
        profile = create_user_profile(**spec)
        foods = PANTRY if pantry_mode else None
        kwargs = {"max_dishes": 3} if accepts_dishes else {}
        try:
            result = generate_meal_plan(profile, targets, available_foods=foods, **kwargs)
        except Exception as error:                      # keep going, count it as a failure
            print("  profile failed:", type(error).__name__, error)
            continue
        for meal, share in SPLIT.items():
            target = targets["calorie_target"] * share
            entry = result["meal_plan"].get(meal)
            if not entry:
                continue
            planned = planned_kcal(entry)
            errors.append(abs(planned - target) / target * 100)
            coverage.append(planned / target * 100)
    return errors, coverage


def summarize(name, errors, coverage):
    errors_sorted = sorted(errors)
    n = len(errors)
    return {
        "mode": name, "meals": n,
        "mean_abs_error_pct": round(sum(errors) / n, 1),
        "median_abs_error_pct": round(errors_sorted[n // 2], 1),
        "meals_within_5pct": round(100 * sum(e <= 5 for e in errors) / n, 1),
        "meals_below_70pct_coverage": round(100 * sum(c < 70 for c in coverage) / n, 1),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=int, default=40)
    args = parser.parse_args()
    rows = []
    for name, pantry in (("broad mode (common foods)", False), ("pantry mode (8 typed foods)", True)):
        errors, coverage = run(args.profiles, pantry)
        rows.append(summarize(name, errors, coverage))
    print(json.dumps(rows, indent=2))
