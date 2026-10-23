"""Meal planner: finds a REAL meal whose calories approach the meal target.

Pipeline (one meal at a time)
-----------------------------
A. Eligible foods come in as a DataFrame.  Safety filters and the
   "available foods only" filter were already applied by the recommendation
   engine, so this module can never add a food that was not given to it.
B. Candidate generation: every combination of 1..max_dishes foods
   (distinct foods = dishes; a bigger portion is NOT a new dish).
C. Portion solving + nutrition evaluation: for each combination the gram
   portions are solved with a bounded least-squares fit (calories carry the
   biggest weight), rounded to practical grams, and the complete meal's
   calories / protein / carbs / fat / fibre are calculated.
D. Ranking: the COMPLETE meal is scored (calorie gap, macro fit, realistic
   portions, meal composition, simplicity, likes/dislikes, recent history).
   Cosine-similarity scores from the recommender are only a tiny tie-breaker.
E. Verification: the chosen meal is recomputed independently from the
   original USDA CSV before it is returned.

Nothing here fakes a percentage: coverage = planned kcal / target kcal * 100.
"""
import itertools
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

from nutrition_targets import MEAL_DISTRIBUTION

BASE_DIR = Path(__file__).resolve().parent
NUTRITION_FILE = BASE_DIR / "data" / "processed" / "nutrition_data.csv"

MEAL_NAMES = ["Breakfast", "Lunch", "Dinner"]
PLANNING_ORDER = ["Lunch", "Dinner", "Breakfast"]  # biggest meals first

NUTRIENTS = ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g"]

DEFAULT_MAX_DISHES = 3
MIN_DISHES = 1
MAX_DISHES_LIMIT = 4

PORTION_STEP_G = 5
ON_TARGET_TOLERANCE = 0.03          # +/-3 % of the meal calorie target
DAILY_STATUS_TOLERANCE = 0.05       # +/-5 % used for dashboard status pills

# ---------------------------------------------------------------------------
# Realistic portion rules (grams of the food AS LISTED in the dataset).
# (minimum grams, maximum grams, maximum kcal one dish may supply)
# The kcal cap automatically keeps dry / dense foods small.
# Change these numbers to make portions stricter or looser.
# ---------------------------------------------------------------------------
PORTION_RULES = {
    "staple": (50, 350, 650),
    "milk": (100, 400, 300),
    "bread": (30, 250, 600),
    "breakfast_grain": (30, 400, 500),
    "legume": (50, 350, 450),
    "meat": (50, 250, 500),
    "egg": (50, 200, 320),
    "dairy": (30, 400, 450),
    "starchy": (80, 400, 450),
    "fruit": (50, 300, 250),
    "vegetable": (50, 300, 150),
    "nuts": (10, 60, 350),
    "other": (30, 300, 400),
}

# Weights used while solving portions (calories first, then macros).
SOLVER_WEIGHTS = np.array([30.0, 1.2, 1.0, 0.8, 0.4])

MAIN_MEAL_CARBS = {"staple", "bread", "starchy"}
MAIN_MEAL_PROTEIN = {"legume", "meat", "egg", "dairy"}


# ===========================================================================
# BASIC NUTRITION HELPERS
# ===========================================================================

def _num(value):
    """Safe float: missing / NaN / negative values become 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if np.isnan(number) or number < 0:
        return 0.0
    return number


def normalize_target(target):
    return {
        "calories": float(target.get("calories", target.get("calorie_target", 0))),
        "protein_g": float(target["protein_g"]),
        "carbs_g": float(target["carbs_g"]),
        "fat_g": float(target["fat_g"]),
        "fiber_g": float(target["fiber_g"]),
    }


def empty_nutrition():
    return {nutrient: 0.0 for nutrient in NUTRIENTS}


def calculate_portion_nutrition(row, grams):
    """Per-100-g USDA values -> nutrition for ``grams`` (no rounding)."""
    grams = _num(grams)
    factor = grams / 100.0
    return {nutrient: _num(row[nutrient]) * factor for nutrient in NUTRIENTS}


def add_nutrition(total, nutrition):
    result = total.copy()
    for nutrient in NUTRIENTS:
        result[nutrient] += _num(nutrition.get(nutrient, 0))
    return result


def combination_nutrition(items):
    total = empty_nutrition()
    for item in items:
        total = add_nutrition(total, item)
    return total


def meal_totals(items):
    """Exact (unrounded) totals of a meal = sum of its foods."""
    return combination_nutrition(items)


# ===========================================================================
# FOOD TYPES
# ===========================================================================

def _words(name):
    return set(re.findall(r"[a-z]+", str(name).lower()))


def food_type(food_name, category=None):
    """Classify a food into a meal role (uses USDA category when known)."""
    words = _words(food_name)
    category = str(category or "").lower()

    if "egg" in words or "eggs" in words:
        return "egg"
    if words & {"chicken", "beef", "pork", "lamb", "turkey", "fish", "salmon",
                "cod", "tuna", "shrimp", "meat", "mutton"}:
        return "meat"
    if words & {"milk", "buttermilk"} and not words & {"cheese", "yogurt", "yoghurt"}:
        return "milk"
    if words & {"paneer", "yogurt", "yoghurt", "curd", "cheese"}:
        return "dairy"
    if words & {"lentil", "lentils", "bean", "beans", "chickpea", "chickpeas",
                "garbanzo", "pea", "peas", "tofu", "soybeans", "dal"}:
        return "legume"
    if words & {"oat", "oats", "oatmeal", "porridge"} or "breakfast cereals" in category:
        return "breakfast_grain"
    if words & {"bread", "roti", "chapati", "naan", "tortilla", "tortillas", "pita",
                "toast", "bun", "buns", "bagel"}:
        return "bread"
    if words & {"rice", "pasta", "quinoa", "grits", "noodles", "macaroni",
                "couscous", "barley", "spaghetti"} or "cereal grains" in category:
        return "staple"
    if words & {"potato", "potatoes", "yam"}:
        return "starchy"
    if "fruits" in category or words & {"banana", "bananas", "apple", "apples",
                                         "orange", "oranges", "mango", "mangos", "berry"}:
        return "fruit"
    if "vegetables" in category:
        return "vegetable"
    if "nut" in category or words & {"almond", "almonds", "peanut", "peanuts", "walnut"}:
        return "nuts"
    return "other"


def is_prepared_food(food_name):
    name = str(food_name).lower()
    terms = ["fast food", "sandwich", "burger", "pizza", "canned", "frozen",
             "ready-to-serve", "ready to serve", "restaurant", "fried", "breaded",
             "nugget", "processed", "snack", "drink", "beverage", "pudding",
             "dessert", "syrup"]
    return any(term in name for term in terms)


def _get(row, key, default=None):
    """row.get() that also works for plain dicts and Series."""
    try:
        value = row.get(key, default)
    except AttributeError:
        value = default
    return default if value is None else value


# ===========================================================================
# FOOD PARAMETERS (per-gram nutrition + portion bounds)
# ===========================================================================

def food_params(row):
    """Per-gram nutrient vector and realistic portion bounds for one food."""
    kind = food_type(row["food_name"], _get(row, "category"))
    per_gram = np.array([_num(row[n]) / 100.0 for n in NUTRIENTS], dtype=float)

    min_g, max_g, max_kcal = PORTION_RULES.get(kind, PORTION_RULES["other"])
    kcal_per_g = per_gram[0]

    if kcal_per_g > 0:
        max_g = min(max_g, max_kcal / kcal_per_g)

    max_g = max(PORTION_STEP_G, np.floor(max_g / PORTION_STEP_G) * PORTION_STEP_G)
    min_g = min(min_g, max_g)

    return {
        "kind": kind,
        "per_gram": per_gram,
        "min_g": float(min_g),
        "max_g": float(max_g),
        "capacity_kcal": float(max_g * kcal_per_g),
    }


def portion_limits(row):
    params = food_params(row)
    return params["min_g"], params["max_g"]


def create_food_item(row, grams):
    """One dish of a meal.  Values are exact; rounding is display-only."""
    grams = int(round(_num(grams)))
    nutrition = calculate_portion_nutrition(row, grams)

    fdc_id = _get(row, "fdc_id")
    item = {
        "fdc_id": int(fdc_id) if fdc_id is not None and not pd.isna(fdc_id) else None,
        "food_name": str(row["food_name"]),
        "user_food": str(_get(row, "user_food", row["food_name"]) or row["food_name"]),
        "kind": food_type(row["food_name"], _get(row, "category")),
        "quantity_g": grams,
    }
    item.update(nutrition)

    note = _get(row, "match_note", "")
    if isinstance(note, str) and note:
        item["match_note"] = note

    return item


# ===========================================================================
# PORTION SOLVER
# ===========================================================================

def _loss(grams, density, target_vec):
    nutrients = density.T @ grams
    relative = (nutrients - target_vec) / target_vec
    return float(np.sum((SOLVER_WEIGHTS * relative) ** 2))


def solve_portions(params_list, target, step=PORTION_STEP_G, refine=False):
    """Gram portions for one combination of foods.

    1. bounded least squares (continuous grams)
    2. round to practical grams
    3. coordinate hill-climb (+/- step, and +/- 1 g when ``refine``)
    """
    density = np.array([p["per_gram"] for p in params_list])   # (k, 5)
    low = np.array([p["min_g"] for p in params_list])
    high = np.array([p["max_g"] for p in params_list])

    target_vec = np.array([max(target[n], 1.0) for n in NUTRIENTS], dtype=float)
    matrix = (density.T / target_vec[:, None]) * SOLVER_WEIGHTS[:, None]
    rhs = SOLVER_WEIGHTS.copy()

    try:
        start = lsq_linear(matrix, rhs, bounds=(low, high), method="bvls").x
    except Exception:
        start = (low + high) / 2.0

    grams = np.clip(np.round(start / step) * step, low, high)

    best_loss = _loss(grams, density, target_vec)
    steps = [step, 1] if refine else [step]

    for move in steps:
        improved = True
        guard = 0
        while improved and guard < 200:
            improved = False
            guard += 1
            for i in range(len(grams)):
                for direction in (-1, 1):
                    trial = grams.copy()
                    trial[i] = np.clip(trial[i] + direction * move, low[i], high[i])
                    if trial[i] == grams[i]:
                        continue
                    trial_loss = _loss(trial, density, target_vec)
                    if trial_loss + 1e-12 < best_loss:
                        grams, best_loss = trial, trial_loss
                        improved = True

    return grams


# ===========================================================================
# SCORING (lower = better)
# ===========================================================================

def calorie_error(kcal, target_kcal):
    return (kcal - target_kcal) / max(target_kcal, 1.0)


def composition_penalty(kinds, meal):
    """Soft rules that keep meals sensible (never hard requirements)."""
    kinds = list(kinds)
    kind_set = set(kinds)
    penalty = 0.0

    has_carb = bool(kind_set & MAIN_MEAL_CARBS)
    has_protein = bool(kind_set & MAIN_MEAL_PROTEIN)

    if meal == "Breakfast":
        if not (kind_set & {"breakfast_grain", "bread", "dairy", "milk", "egg", "fruit"}):
            penalty += 0.50            # e.g. a breakfast of only rice
        if kind_set & {"staple"}:
            penalty += 0.35
        if "starchy" in kind_set:
            penalty += 0.15
        if "meat" in kind_set:
            penalty += 0.50
        if "legume" in kind_set:
            penalty += 0.35
    else:
        if not has_carb:
            penalty += 0.25
        if not has_protein:
            penalty += 0.35
        if "breakfast_grain" in kind_set:
            penalty += 0.50
        if "fruit" in kind_set:
            penalty += 0.30
        if "milk" in kind_set:
            penalty += 0.40            # a glass of milk is not a main dish

    # Nuts are a side ingredient, never the main protein of a meal
    if "nuts" in kind_set:
        if not (kind_set & {"legume", "meat", "egg", "dairy"}):
            penalty += 0.60
        if meal != "Breakfast":
            penalty += 0.15

    # Incompatible or odd pairings
    if "fruit" in kind_set and kind_set & {"meat", "legume", "egg"}:
        penalty += 0.40
    if "milk" in kind_set and kind_set & {"meat", "legume"}:
        penalty += 0.40
    if "dairy" in kind_set and kind_set & {"meat"}:
        penalty += 0.20

    # Two foods playing the same role (two grains, two meats ...)
    for role in ("staple", "bread", "meat", "legume", "breakfast_grain", "starchy"):
        if kinds.count(role) >= 2:
            penalty += 0.40

    return penalty


def portion_realism_penalty(items_params, grams):
    penalty = 0.0
    for params, g in zip(items_params, grams):
        span = max(params["max_g"] - params["min_g"], 1.0)
        position = (g - params["min_g"]) / span
        if position > 0.85:
            penalty += 0.15 * (position - 0.85) / 0.15
    return penalty


def preference_adjustment(rows, user_profile):
    """Negative = bonus.  Uses likes / dislikes and the recommender's scores."""
    adjustment = 0.0
    profile = user_profile or {}
    likes = [str(x).lower().strip() for x in profile.get("likes", []) if str(x).strip()]
    dislikes = [str(x).lower().strip() for x in profile.get("dislikes", []) if str(x).strip()]

    for row in rows:
        label = f"{row['food_name']} {_get(row, 'user_food', '')}".lower()
        if any(word in label for word in likes):
            adjustment -= 0.20
        if any(word in label for word in dislikes):
            adjustment += 0.50

    adjustment = max(adjustment, -0.40)

    # Small tie-breaker from the content-based (cosine) recommender.
    scores = []
    for row in rows:
        value = _get(row, "final_score")
        if value is not None and not pd.isna(value):
            scores.append(float(value))
    if scores:
        adjustment -= 0.08 * float(np.mean(scores))

    return adjustment


def history_penalty(food_names, past_meals):
    """Encourage variety: small penalty when this meal repeats a recent one.

    ``past_meals`` is a list (most recent first) of lists of food names.
    The penalty is capped, so variety can never beat a clearly better fit.
    """
    if not past_meals:
        return 0.0

    current = {str(n).strip().lower() for n in food_names}
    worst = 0.0

    for position, past in enumerate(past_meals):
        past_set = {str(n).strip().lower() for n in past}
        if not past_set:
            continue
        recency = 1.0 / (1.0 + 0.10 * position)
        union = current | past_set
        similarity = len(current & past_set) / len(union) if union else 0.0
        if current == past_set:
            value = 0.30 * recency
        else:
            value = 0.12 * similarity * recency
        worst = max(worst, value)

    return min(worst, 0.30)


def score_meal(totals, target, kinds, items_params, grams, meal, rows,
               user_profile=None, past_meals=None, avoid_sets=None, names=None):
    kcal_error = calorie_error(totals["calories"], target["calories"])
    score = 8.0 * abs(kcal_error) + (2.0 * kcal_error if kcal_error > 0 else 0.0)

    macro_weights = {"protein_g": 0.60, "carbs_g": 0.35, "fat_g": 0.35, "fiber_g": 0.20}
    for nutrient, weight in macro_weights.items():
        reference = max(target[nutrient], 1.0)
        score += weight * min(abs(totals[nutrient] - target[nutrient]) / reference, 1.0)

    score += composition_penalty(kinds, meal)
    score += portion_realism_penalty(items_params, grams)
    score += 0.08 * (len(kinds) - 1)          # simpler meals are preferred
    score += preference_adjustment(rows, user_profile)
    score += history_penalty(names or [], past_meals)

    current = {n.lower() for n in (names or [])}
    for other in avoid_sets or []:
        shared = current & other
        if shared:
            score += 0.10 * len(shared)
        if other and current == other:
            score += 0.30

    return score


# ===========================================================================
# CANDIDATE POOL
# ===========================================================================

def food_priority(row):
    score = 0.0

    value = _get(row, "preference_score")
    if value is not None and not pd.isna(value):
        score += float(value) * 2.0

    value = _get(row, "final_score")
    if value is not None and not pd.isna(value):
        score += float(value) * 0.25

    if is_prepared_food(row["food_name"]):
        score -= 0.45

    name = str(row["food_name"]).lower()
    if any(term in name for term in ["raw", "fresh", "plain", "whole"]):
        score += 0.20

    return score


def clamp_dishes(max_dishes):
    try:
        value = int(max_dishes)
    except (TypeError, ValueError):
        value = DEFAULT_MAX_DISHES
    return max(MIN_DISHES, min(MAX_DISHES_LIMIT, value))


def _usable_pool(foods):
    """Rows with a positive calorie value and a food id, no duplicates."""
    if foods is None or len(foods) == 0:
        return pd.DataFrame()

    rows = foods.copy()
    for nutrient in NUTRIENTS:
        rows[nutrient] = rows[nutrient].apply(_num)

    rows = rows[rows["calories"] > 0]
    if "fdc_id" in rows.columns:
        rows = rows.drop_duplicates(subset=["fdc_id"])
    else:
        rows = rows.drop_duplicates(subset=["food_name"])

    return rows.reset_index(drop=True)


def select_meal_foods(foods, meal, max_foods=14):
    """Keep a small, varied pool (round-robin over food roles)."""
    rows = _usable_pool(foods)
    if rows.empty or len(rows) <= max_foods:
        return rows

    rows = rows.copy()
    rows["_priority"] = rows.apply(food_priority, axis=1)
    rows["_kind"] = [
        food_type(rows.iloc[i]["food_name"], _get(rows.iloc[i], "category"))
        for i in range(len(rows))
    ]
    rows = rows.sort_values("_priority", ascending=False)

    if meal == "Breakfast":
        order = ["breakfast_grain", "dairy", "egg", "fruit", "bread", "staple",
                 "starchy", "legume", "meat", "vegetable", "nuts", "other"]
    else:
        order = ["staple", "legume", "meat", "bread", "dairy", "egg", "starchy",
                 "vegetable", "fruit", "breakfast_grain", "nuts", "other"]

    buckets = {kind: list(group.index) for kind, group in rows.groupby("_kind")}
    chosen = []
    while len(chosen) < max_foods and any(buckets.values()):
        for kind in order:
            if buckets.get(kind):
                chosen.append(buckets[kind].pop(0))
                if len(chosen) >= max_foods:
                    break

    return rows.loc[chosen].drop(columns=["_priority", "_kind"]).reset_index(drop=True)


# ===========================================================================
# MEAL GENERATION
# ===========================================================================

def _signature(names):
    return "|".join(sorted(str(n).strip().lower() for n in names))


def generate_ranked_meals(foods, meal, target, max_dishes=DEFAULT_MAX_DISHES,
                          user_profile=None, avoid_sets=None, limit=60,
                          pool_size=None):
    """Return candidate meals sorted best-first.

    Every candidate uses ONLY foods from ``foods`` and at most ``max_dishes``
    distinct foods.
    """
    max_dishes = clamp_dishes(max_dishes)
    pool_size = pool_size or (14 if max_dishes <= 3 else 12)
    pool = select_meal_foods(foods, meal, max_foods=pool_size)

    if pool.empty:
        return []

    rows = [pool.iloc[i] for i in range(len(pool))]
    params = [food_params(row) for row in rows]
    past_meals = (user_profile or {}).get("recent_meals", {}).get(meal, [])

    candidates = []

    for count in range(1, min(max_dishes, len(rows)) + 1):
        for indices in itertools.combinations(range(len(rows)), count):
            chosen_params = [params[i] for i in indices]
            chosen_rows = [rows[i] for i in indices]

            grams = solve_portions(chosen_params, target)
            nutrition = np.array([p["per_gram"] for p in chosen_params]).T @ grams
            totals = dict(zip(NUTRIENTS, nutrition))
            kinds = [p["kind"] for p in chosen_params]
            names = [str(r["food_name"]) for r in chosen_rows]

            score = score_meal(
                totals, target, kinds, chosen_params, grams, meal, chosen_rows,
                user_profile=user_profile, past_meals=past_meals,
                avoid_sets=avoid_sets, names=names,
            )
            candidates.append((score, indices))

    candidates.sort(key=lambda entry: entry[0])
    finalists = candidates[: max(limit, 1)]

    ranked = []
    for _, indices in finalists:
        chosen_params = [params[i] for i in indices]
        chosen_rows = [rows[i] for i in indices]

        grams = solve_portions(chosen_params, target, refine=True)
        items = [create_food_item(row, g) for row, g in zip(chosen_rows, grams)]
        totals = meal_totals(items)
        kinds = [p["kind"] for p in chosen_params]
        names = [item["food_name"] for item in items]

        score = score_meal(
            totals, target, kinds, chosen_params, grams, meal, chosen_rows,
            user_profile=user_profile, past_meals=past_meals,
            avoid_sets=avoid_sets, names=names,
        )

        ranked.append({
            "items": items,
            "totals": totals,
            "score": score,
            "signature": _signature(names),
            "names": names,
        })

    ranked.sort(key=lambda entry: entry["score"])
    return ranked


def food_capacity(foods, meal, max_dishes):
    """Most kcal the foods can supply at realistic portions with N dishes."""
    pool = _usable_pool(foods)
    if pool.empty:
        return 0.0
    caps = sorted(
        (food_params(pool.iloc[i])["capacity_kcal"] for i in range(len(pool))),
        reverse=True,
    )
    return float(sum(caps[: clamp_dishes(max_dishes)]))


def explain_gap(totals, target_kcal, foods, meal, max_dishes, n_foods):
    """Honest, plain-language reason when the meal is off target."""
    notes = []
    kcal = totals["calories"]
    gap = kcal - target_kcal

    if abs(gap) <= ON_TARGET_TOLERANCE * target_kcal:
        return notes

    if gap < 0:
        cap_now = food_capacity(foods, meal, max_dishes)
        if cap_now < target_kcal * (1 - ON_TARGET_TOLERANCE):
            notes.append(
                f"With at most {max_dishes} dish(es) from the allowed foods, realistic "
                f"portion limits allow about {cap_now:.0f} kcal, so this meal is "
                f"{-gap:.0f} kcal short of its {target_kcal:.0f} kcal target."
            )
            if max_dishes < MAX_DISHES_LIMIT and n_foods > max_dishes:
                cap_more = food_capacity(foods, meal, max_dishes + 1)
                if cap_more > cap_now + 1:
                    notes.append(
                        f"Allowing {max_dishes + 1} dishes could reach about "
                        f"{min(cap_more, target_kcal):.0f} kcal."
                    )
            elif n_foods <= max_dishes:
                notes.append("Add more available foods to close the gap.")
        else:
            notes.append(
                f"Best balanced combination found: {-gap:.0f} kcal below target. "
                "A closer calorie match would break portion or composition rules."
            )
    else:
        notes.append(
            f"The smallest realistic portions of this combination give {gap:.0f} kcal "
            "more than the target."
        )

    return notes


# ===========================================================================
# TARGETS, DAILY TOTALS, COMPARISON
# ===========================================================================

def calculate_meal_targets(daily_targets):
    """Meal targets that always add up to the daily target.

    Uses ``meal_calories`` when the targets dict carries custom meal
    calories; otherwise the 25 / 40 / 35 split.  Macros follow the same share.
    """
    target = normalize_target(daily_targets)
    daily_kcal = max(target["calories"], 1.0)
    custom = daily_targets.get("meal_calories") if isinstance(daily_targets, dict) else None

    result = {}
    for meal, share in MEAL_DISTRIBUTION.items():
        meal_kcal = float(custom[meal]) if custom and meal in custom else daily_kcal * share
        fraction = meal_kcal / daily_kcal
        result[meal] = {
            "calories": meal_kcal,
            "protein_g": target["protein_g"] * fraction,
            "carbs_g": target["carbs_g"] * fraction,
            "fat_g": target["fat_g"] * fraction,
            "fiber_g": target["fiber_g"] * fraction,
        }
    return result


def coverage_percent(planned_kcal, target_kcal):
    """Calorie coverage % = planned / target * 100 (never capped)."""
    if not target_kcal:
        return 0.0
    return planned_kcal / target_kcal * 100.0


def meal_status(kcal, target_kcal):
    error = calorie_error(kcal, target_kcal)
    if abs(error) <= ON_TARGET_TOLERANCE:
        return "on target"
    return "below target" if error < 0 else "above target"


def get_meal_foods(meal_plan, meal_name):
    meal = meal_plan.get(meal_name, {})
    if isinstance(meal, dict):
        return meal.get("foods", [])
    return meal or []


def build_meal_entry(candidate, target, foods, meal, max_dishes, seen=None):
    """Turn a ranked candidate (or None) into the stored meal dictionary."""
    items = candidate["items"] if candidate else []
    totals = meal_totals(items)
    kcal = totals["calories"]
    n_foods = len(_usable_pool(foods))

    if items:
        notes = explain_gap(totals, target["calories"], foods, meal, max_dishes, n_foods)
    else:
        notes = ["No valid food combination was found for this meal with the allowed foods."]

    signatures = list(seen or [])
    if candidate and candidate["signature"] not in signatures:
        signatures.append(candidate["signature"])

    return {
        "target": target,
        "foods": items,
        "totals": totals,
        "coverage_pct": coverage_percent(kcal, target["calories"]),
        "gap_kcal": kcal - target["calories"],
        "status": meal_status(kcal, target["calories"]) if items else "no meal",
        "notes": notes,
        "max_dishes": max_dishes,
        "seen_signatures": signatures,
        "verified": True,
    }


def create_meal_plan(foods, daily_targets, max_dishes=DEFAULT_MAX_DISHES, user_profile=None):
    """Plan Breakfast, Lunch and Dinner from the eligible ``foods`` only."""
    max_dishes = clamp_dishes(max_dishes)
    meal_targets = calculate_meal_targets(daily_targets)

    plan = {}
    used_sets = []

    for meal in PLANNING_ORDER:
        ranked = generate_ranked_meals(
            foods, meal, meal_targets[meal], max_dishes=max_dishes,
            user_profile=user_profile, avoid_sets=used_sets,
        )
        best = ranked[0] if ranked else None
        plan[meal] = build_meal_entry(best, meal_targets[meal], foods, meal, max_dishes)
        if best:
            used_sets.append({n.lower() for n in best["names"]})

    ordered = {meal: plan[meal] for meal in MEAL_NAMES}

    problems = verify_meal_plan(ordered, max_dishes=max_dishes)
    for meal, meal_problems in problems.items():
        ordered[meal]["verified"] = False
        ordered[meal]["notes"].append("Verification problem: " + "; ".join(meal_problems))

    return ordered


def calculate_daily_summary(meal_plan):
    """Daily totals = Breakfast + Lunch + Dinner (exact, unrounded)."""
    summary = empty_nutrition()
    for meal_name in meal_plan:
        for food in get_meal_foods(meal_plan, meal_name):
            for nutrient in NUTRIENTS:
                summary[nutrient] += _num(food.get(nutrient, 0))
    return summary


def compare_with_targets(daily_summary, daily_targets):
    """Planned vs target for every nutrient (planned, NOT eaten)."""
    target = normalize_target(daily_targets)
    result = {}

    for nutrient in NUTRIENTS:
        target_value = target[nutrient]
        planned_value = float(daily_summary.get(nutrient, 0.0))
        difference = planned_value - target_value
        percentage = difference / target_value * 100 if target_value else 0.0
        coverage = planned_value / target_value * 100 if target_value else 0.0

        if abs(percentage) <= DAILY_STATUS_TOLERANCE * 100:
            status = "on target"
        else:
            status = "above target" if percentage > 0 else "below target"

        result[nutrient] = {
            "nutrient": nutrient,
            "target": target_value,
            "planned": planned_value,
            "difference": difference,
            "difference_percent": percentage,
            "diff_pct": percentage,
            "coverage_percent": coverage,
            "status": status,
            "note": "",
        }

    return result


# ===========================================================================
# VERIFICATION (stage E)
# ===========================================================================

@lru_cache(maxsize=1)
def _reference_table():
    table = pd.read_csv(NUTRITION_FILE)
    return table.set_index("fdc_id")


def verify_meal_items(items, max_dishes=None, tolerance=1e-6):
    """Recompute every dish from the original USDA CSV and compare."""
    problems = []
    reference = _reference_table()

    if max_dishes is not None and len(items) > max_dishes:
        problems.append(f"{len(items)} dishes exceed the limit of {max_dishes}")

    ids = [item.get("fdc_id") for item in items]
    if len(ids) != len(set(ids)):
        problems.append("the same food appears twice in one meal")

    for item in items:
        fdc_id = item.get("fdc_id")
        grams = item.get("quantity_g", 0)

        if grams is None or grams <= 0:
            problems.append(f"invalid portion for {item.get('food_name')}")
            continue
        if fdc_id not in reference.index:
            problems.append(f"food id {fdc_id} not found in the nutrition CSV")
            continue

        row = reference.loc[fdc_id]
        for nutrient in NUTRIENTS:
            expected = _num(row[nutrient]) * grams / 100.0
            if abs(expected - item.get(nutrient, 0.0)) > tolerance * max(1.0, expected):
                problems.append(f"{item.get('food_name')}: {nutrient} mismatch")

    return problems


def verify_meal_plan(meal_plan, max_dishes=None):
    """Return {meal: [problems]} (empty dict when everything checks out)."""
    report = {}
    for meal_name in meal_plan:
        items = get_meal_foods(meal_plan, meal_name)
        problems = verify_meal_items(items, max_dishes=max_dishes)

        entry = meal_plan[meal_name]
        if isinstance(entry, dict) and "totals" in entry:
            recomputed = meal_totals(items)
            for nutrient in NUTRIENTS:
                if abs(recomputed[nutrient] - entry["totals"][nutrient]) > 1e-6:
                    problems.append(f"stored {nutrient} total differs from its foods")

        if problems:
            report[meal_name] = problems
    return report


# ===========================================================================
# REPLACE ONE MEAL
# ===========================================================================

def replace_meal_detailed(meal_plan, meal_name, foods, daily_targets,
                          max_dishes=None, user_profile=None):
    """Replace ONE meal.  Returns (new_plan, changed, message).

    * The other two meals are the very same objects as before (unchanged).
    * Only a different FOOD combination counts as a replacement.
    * If no acceptable alternative exists the original meal is kept.
    """
    if meal_name not in meal_plan:
        return meal_plan, False, f"{meal_name} was not found in the current plan."
    if foods is None or len(foods) == 0:
        return meal_plan, False, "There are no eligible foods to build an alternative from."

    current = meal_plan[meal_name]
    current_items = get_meal_foods(meal_plan, meal_name)
    max_dishes = clamp_dishes(
        max_dishes if max_dishes is not None else current.get("max_dishes", DEFAULT_MAX_DISHES)
    )

    target = calculate_meal_targets(daily_targets)[meal_name]

    current_signature = _signature([i["food_name"] for i in current_items])
    seen = list(current.get("seen_signatures", [])) if isinstance(current, dict) else []
    if current_signature and current_signature not in seen:
        seen.append(current_signature)

    # foods used by the other two meals (soft preference only)
    other_sets = [
        {i["food_name"].lower() for i in get_meal_foods(meal_plan, other)}
        for other in meal_plan if other != meal_name
    ]

    ranked = generate_ranked_meals(
        foods, meal_name, target, max_dishes=max_dishes,
        user_profile=user_profile, avoid_sets=other_sets, limit=200,
    )
    if not ranked:
        return meal_plan, False, f"No valid {meal_name.lower()} could be built from the allowed foods."

    different = [c for c in ranked if c["signature"] != current_signature]
    if not different:
        return (
            meal_plan, False,
            f"No different {meal_name.lower()} exists with the current foods and a limit of "
            f"{max_dishes} dish(es). The original {meal_name.lower()} is kept. "
            "Add more available foods or allow more dishes to get alternatives.",
        )

    # Quality gate: do not swap in a meal that misses the calories badly.
    best_error = abs(calorie_error(ranked[0]["totals"]["calories"], target["calories"]))
    current_error = (
        abs(calorie_error(meal_totals(current_items)["calories"], target["calories"]))
        if current_items else 1.0
    )
    allowed_error = max(0.15, best_error + 0.10, min(current_error, 0.25))

    acceptable = [
        c for c in different
        if abs(calorie_error(c["totals"]["calories"], target["calories"])) <= allowed_error
    ]
    if not acceptable:
        return (
            meal_plan, False,
            f"Other {meal_name.lower()} options exist but they miss the "
            f"{target['calories']:.0f} kcal target by more than {allowed_error * 100:.0f}%. "
            f"The original {meal_name.lower()} is kept.",
        )

    # Prefer combinations not shown before so repeated clicks keep changing.
    unseen = [c for c in acceptable if c["signature"] not in seen]
    if unseen:
        chosen = unseen[0]
    else:
        chosen = acceptable[0]
        seen = [current_signature]   # every alternative used once: start a new cycle

    entry = build_meal_entry(chosen, target, foods, meal_name, max_dishes, seen=seen)

    problems = verify_meal_items(entry["foods"], max_dishes=max_dishes)
    if problems:
        return meal_plan, False, "The alternative failed verification: " + "; ".join(problems)

    updated_plan = dict(meal_plan)
    updated_plan[meal_name] = entry
    return updated_plan, True, f"{meal_name} replaced. The other two meals are unchanged."


def replace_meal(meal_plan, meal_name, foods, daily_targets, max_dishes=None, user_profile=None):
    """Compatibility wrapper: returns (updated_plan, changed)."""
    plan, changed, _ = replace_meal_detailed(
        meal_plan, meal_name, foods, daily_targets,
        max_dishes=max_dishes, user_profile=user_profile,
    )
    return plan, changed
