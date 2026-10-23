"""Daily calorie / macro targets (Mifflin-St Jeor BMR x activity factor).

New in this version
-------------------
* ``custom_daily_calories``  : user sets their own daily calorie goal.
* ``custom_meal_calories``   : user sets Breakfast / Lunch / Dinner calories
  separately (for example Lunch = 876 kcal).  The daily target then becomes the
  sum of the three meals and every macro target is scaled consistently.

``MEAL_DISTRIBUTION`` is the single source of truth for the meal split
(25 % / 40 % / 35 %).  Every other module imports it from here.
"""

MEAL_DISTRIBUTION = {
    "Breakfast": 0.25,
    "Lunch": 0.40,
    "Dinner": 0.35,
}

MIN_MEAL_KCAL = 100.0
MAX_MEAL_KCAL = 3000.0


def calculate_bmr(age, gender, weight_kg, height_cm):
    if str(gender).lower() == "male":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    return round(bmr, 2)


def calculate_tdee(bmr, activity_level):
    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }

    factor = activity_factors.get(str(activity_level).lower(), 1.2)

    return round(bmr * factor, 2)


def _macro_targets(calorie_target, weight_kg):
    """Protein from body weight, 30 % fat, remaining calories as carbs."""
    protein_g = weight_kg * 1.2
    fat_g = (calorie_target * 0.30) / 9
    carbs_g = (calorie_target - (protein_g * 4) - (fat_g * 9)) / 4

    # Safety net for very small custom calorie goals: never let protein push
    # carbohydrates below 20 % of calories.
    min_carbs_g = (calorie_target * 0.20) / 4
    if carbs_g < min_carbs_g:
        protein_g = min(protein_g, (calorie_target * 0.25) / 4)
        carbs_g = (calorie_target - (protein_g * 4) - (fat_g * 9)) / 4

    return protein_g, carbs_g, fat_g


def clean_custom_meal_calories(custom_meal_calories):
    """Validate a {"Breakfast": x, "Lunch": y, "Dinner": z} dict.

    Returns a dict of floats or None when the input is missing/invalid.
    """
    if not custom_meal_calories:
        return None

    cleaned = {}
    for meal in MEAL_DISTRIBUTION:
        try:
            value = float(custom_meal_calories.get(meal))
        except (TypeError, ValueError):
            return None
        if not (MIN_MEAL_KCAL <= value <= MAX_MEAL_KCAL):
            return None
        cleaned[meal] = value

    return cleaned


def calculate_targets(
    age,
    gender,
    weight_kg,
    height_cm,
    activity_level,
    goal,
    custom_daily_calories=None,
    custom_meal_calories=None,
):
    bmr = calculate_bmr(age, gender, weight_kg, height_cm)
    tdee = calculate_tdee(bmr, activity_level)

    goal_adjustments = {
        "weight_loss": -300,
        "maintenance": 0,
        "weight_gain": 300,
    }

    auto_calorie_target = max(
        tdee + goal_adjustments.get(str(goal).lower(), 0),
        1200,
    )

    meal_calories = clean_custom_meal_calories(custom_meal_calories)
    target_source = "auto"

    if meal_calories:
        calorie_target = sum(meal_calories.values())
        target_source = "custom_meal"
    elif custom_daily_calories:
        calorie_target = float(custom_daily_calories)
        target_source = "custom_daily"
        meal_calories = {
            meal: calorie_target * share
            for meal, share in MEAL_DISTRIBUTION.items()
        }
    else:
        calorie_target = auto_calorie_target
        meal_calories = {
            meal: calorie_target * share
            for meal, share in MEAL_DISTRIBUTION.items()
        }

    protein_g, carbs_g, fat_g = _macro_targets(calorie_target, weight_kg)
    fiber_g = 25

    return {
        "bmr": round(bmr, 2),
        "tdee": round(tdee, 2),
        "auto_calorie_target": round(auto_calorie_target, 2),
        "calorie_target": round(calorie_target, 2),
        "protein_g": round(protein_g, 2),
        "carbs_g": round(carbs_g, 2),
        "fat_g": round(fat_g, 2),
        "fiber_g": round(fiber_g, 2),
        "target_source": target_source,
        "meal_calories": {k: round(v, 2) for k, v in meal_calories.items()},
    }


if __name__ == "__main__":
    result = calculate_targets(
        age=21,
        gender="male",
        weight_kg=55,
        height_cm=170,
        activity_level="moderate",
        goal="maintenance",
    )

    print("Nutrition Target Calculation")
    print("-----------------------------")

    for key, value in result.items():
        print(f"{key}: {value}")
