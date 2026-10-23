import pandas as pd
import numpy as np

from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

from available_foods import match_available_foods, CURATED_FOODS


BASE_DIR = Path(__file__).resolve().parent

NUTRITION_FILE = BASE_DIR / "data" / "processed" / "nutrition_data.csv"

CONSTRAINT_FILE = BASE_DIR / "data" / "processed" / "final_food_constraints.csv"

# Broad mode: extra everyday foods (besides CURATED_FOODS in available_foods.py)
EXTRA_COMMON_FOODS = [
    "Cheese, cottage, lowfat, 1% milkfat",
    "Cheese, mozzarella, whole milk",
    "Beans, black, mature seeds, cooked, boiled, without salt",
    "Peas, split, mature seeds, cooked, boiled, without salt",
    "Corn, sweet, yellow, cooked, boiled, drained, without salt",
]


# =========================================================
# LOAD FOOD DATA
# =========================================================

def load_food_data():

    nutrition = pd.read_csv(
        NUTRITION_FILE
    )

    constraints = pd.read_csv(
        CONSTRAINT_FILE
    )

    data = nutrition.merge(
        constraints[
            [
                "fdc_id",
                "category",
                "is_vegetarian",
                "is_vegan",
                "contains_dairy",
                "contains_egg",
                "contains_nuts",
                "contains_fish",
                "contains_shellfish",
                "contains_alcohol"
            ]
        ],
        on="fdc_id",
        how="inner"
    )

    return data


# =========================================================
# MEAL-READY FILTER (broad mode only)
# =========================================================

def apply_meal_ready_filter(data):
    """Broad mode (no available-food list): common, ready-to-eat foods only.

    Ranking all ~7,400 USDA entries by nutrient similarity gives odd results
    (for example chicken feet or exotic fruit), so broad mode uses a short
    list of everyday foods taken from the same curated table that the
    available-food matcher uses.  Every row still comes from USDA SR Legacy
    and still passes the safety filters applied before this step.
    When the user types their own foods this function is NOT used.
    """

    common_names = set(CURATED_FOODS.values()) | set(EXTRA_COMMON_FOODS)

    return data[data["food_name"].isin(common_names)].reset_index(drop=True)


# =========================================================
# NORMALIZE USER LISTS
# =========================================================

def normalize_list(items):

    if not items:
        return []

    return [
        str(item).strip().lower()
        for item in items
        if str(item).strip()
    ]


# =========================================================
# SAFETY FILTER
# =========================================================

def apply_basic_safety_filter(
    data,
    diet_preference,
    allergies=None,
    restrictions=None
):

    result = data.copy()

    diet = str(
        diet_preference
    ).lower().strip()

    allergies = normalize_list(
        allergies
    )

    restrictions = normalize_list(
        restrictions
    )

    if diet == "vegetarian":

        # The dataset flags eggs as "vegetarian".  In the usual Indian
        # meaning of vegetarian, eggs are NOT allowed, so eggs are removed
        # here.  (Eggetarian below allows them.)
        result = result[
            (result["is_vegetarian"] == True)
            &
            (result["contains_egg"] == False)
        ]

    elif diet == "vegan":

        result = result[
            result["is_vegan"] == True
        ]

    elif diet == "eggetarian":

        # vegetarian foods (the dataset already counts egg as vegetarian).
        # Foods that merely contain egg AND meat are not allowed.
        result = result[
            result["is_vegetarian"] == True
        ]

    if (
        "peanut" in allergies
        or "peanuts" in allergies
        or "nut" in allergies
        or "nuts" in allergies
    ):

        result = result[
            result["contains_nuts"] == False
        ]

    if (
        "milk" in allergies
        or "dairy" in allergies
    ):

        result = result[
            result["contains_dairy"] == False
        ]

    if (
        "egg" in allergies
        or "eggs" in allergies
    ):

        result = result[
            result["contains_egg"] == False
        ]

    if "fish" in allergies:

        result = result[
            result["contains_fish"] == False
        ]

    if "shellfish" in allergies:

        result = result[
            result["contains_shellfish"] == False
        ]

    if "alcohol" in allergies:

        result = result[
            result["contains_alcohol"] == False
        ]

    if (
        "no nuts" in restrictions
        or "nut free" in restrictions
    ):

        result = result[
            result["contains_nuts"] == False
        ]

    if "dairy free" in restrictions:

        result = result[
            result["contains_dairy"] == False
        ]

    if "egg free" in restrictions:

        result = result[
            result["contains_egg"] == False
        ]

    if "gluten free" in restrictions:

        result = result[
            ~result["category"]
            .astype(str)
            .str.lower()
            .isin(
                [
                    "baked products",
                    "cereal grains and pasta"
                ]
            )
        ]

    return result.reset_index(
        drop=True
    )


# =========================================================
# MACRO RATIO
# =========================================================

def calculate_macro_ratio(
    protein,
    carbs,
    fat
):

    protein_calories = protein * 4
    carb_calories = carbs * 4
    fat_calories = fat * 9

    total = (
        protein_calories
        + carb_calories
        + fat_calories
    )

    if total <= 0:

        return [
            0.33,
            0.33,
            0.34
        ]

    return [
        protein_calories / total,
        carb_calories / total,
        fat_calories / total
    ]


# =========================================================
# TARGET PROFILE
# =========================================================

def create_target_profile(targets):

    calorie = max(
        targets["calorie_target"],
        1
    )

    protein = targets["protein_g"]
    carbs = targets["carbs_g"]
    fat = targets["fat_g"]
    fiber = targets["fiber_g"]

    macro_ratio = calculate_macro_ratio(
        protein,
        carbs,
        fat
    )

    fiber_per_100kcal = (
        fiber / calorie
    ) * 100

    return np.array(
        [
            macro_ratio[0],
            macro_ratio[1],
            macro_ratio[2],
            fiber_per_100kcal
        ]
    )


# =========================================================
# FOOD PROFILES
# =========================================================

def create_food_profiles(data):

    profiles = []

    for _, row in data.iterrows():

        calories = max(
            float(row["calories"]),
            1
        )

        macro_ratio = calculate_macro_ratio(
            row["protein_g"],
            row["carbs_g"],
            row["fat_g"]
        )

        fiber_per_100kcal = (
            row["fiber_g"] / calories
        ) * 100

        profiles.append(
            [
                macro_ratio[0],
                macro_ratio[1],
                macro_ratio[2],
                fiber_per_100kcal
            ]
        )

    profiles = np.array(
        profiles
    )

    profiles = np.nan_to_num(
        profiles,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    return profiles


# =========================================================
# CALORIE SUITABILITY
# =========================================================

def calculate_calorie_suitability(data):

    calories = data[
        "calories"
    ].astype(float)

    log_calories = np.log1p(
        calories
    )

    low = log_calories.quantile(
        0.05
    )

    high = log_calories.quantile(
        0.95
    )

    if high <= low:

        return pd.Series(
            1.0,
            index=data.index
        )

    normalized = (
        (log_calories - low)
        / (high - low)
    )

    normalized = normalized.clip(
        0,
        1
    )

    suitability = 1 - (
        np.abs(
            normalized - 0.35
        )
        / 0.65
    )

    return suitability.clip(
        0,
        1
    )


# =========================================================
# PREPARED FOOD DETECTION
# =========================================================

def is_prepared_food(food_name):

    name = str(
        food_name
    ).lower()

    prepared_words = [
        "fast food",
        "sandwich",
        "burger",
        "pizza",
        "canned",
        "frozen",
        "ready-to-serve",
        "restaurant",
        "fried",
        "breaded",
        "nugget",
        "processed",
        "snack",
        "drink",
        "beverage",
        "pudding",
        "dessert",
        "syrup",
        "sauce",
        "sweetened"
    ]

    return any(
        word in name
        for word in prepared_words
    )


# =========================================================
# BASIC FOOD DETECTION
# =========================================================

def is_basic_food(food_name):

    name = str(
        food_name
    ).lower()

    basic_words = [
        "raw",
        "fresh",
        "plain",
        "whole",
        "natural"
    ]

    return any(
        word in name
        for word in basic_words
    )


# =========================================================
# DIVERSITY
# =========================================================

def apply_diversity(
    ranked_data,
    top_k,
    already_selected=None
):

    selected = []

    if already_selected is None:
        already_selected = []

    selected_ids = set(
        already_selected
    )

    category_counts = {}

    for _, row in ranked_data.iterrows():

        food_id = row["fdc_id"]

        if food_id in selected_ids:
            continue

        category = str(
            row["category"]
        ).strip().lower()

        count = category_counts.get(
            category,
            0
        )

        if count >= 2:
            continue

        selected.append(row)

        selected_ids.add(
            food_id
        )

        category_counts[category] = (
            count + 1
        )

        if (
            len(selected)
            + len(already_selected)
            >= top_k
        ):
            break

    if (
        len(selected)
        + len(already_selected)
        < top_k
    ):

        for _, row in ranked_data.iterrows():

            food_id = row["fdc_id"]

            if food_id in selected_ids:
                continue

            selected.append(row)

            selected_ids.add(
                food_id
            )

            if (
                len(selected)
                + len(already_selected)
                >= top_k
            ):
                break

    return pd.DataFrame(
        selected
    ).reset_index(
        drop=True
    )


# =========================================================
# INCLUDE USER LIKES
# =========================================================

def include_liked_foods(
    data,
    likes,
    top_k
):

    if not likes:
        return data.copy()

    selected_rows = []
    selected_ids = set()

    food_names = (
        data["food_name"]
        .astype(str)
        .str.lower()
    )

    for word in likes:

        matches = data[
            food_names.str.contains(
                word,
                na=False,
                regex=False
            )
        ].copy()

        if matches.empty:
            continue

        matches = matches[
            ~matches["food_name"]
            .apply(is_prepared_food)
        ]

        if matches.empty:
            continue

        basic_matches = matches[
            matches["food_name"]
            .apply(is_basic_food)
        ]

        if not basic_matches.empty:
            matches = basic_matches

        matches = matches.sort_values(
            "final_score",
            ascending=False
        )

        selected = matches.iloc[0]

        food_id = selected["fdc_id"]

        if food_id not in selected_ids:

            selected_rows.append(
                selected
            )

            selected_ids.add(
                food_id
            )

        if len(selected_rows) >= top_k:
            break

    if not selected_rows:
        return data.copy()

    liked_data = pd.DataFrame(
        selected_rows
    )

    remaining = data[
        ~data["fdc_id"].isin(
            selected_ids
        )
    ]

    remaining = remaining.sort_values(
        "final_score",
        ascending=False
    )

    return pd.concat(
        [
            liked_data,
            remaining
        ],
        ignore_index=True
    )


# =========================================================
# MAIN RECOMMENDATION ENGINE
# =========================================================

def calculate_recommendations(
    user_profile,
    targets,
    available_foods=None,
    top_k=10
):

    # -----------------------------------------------------
    # LOAD USDA DATA
    # -----------------------------------------------------

    data = load_food_data()

    initial_count = len(data)

    # -----------------------------------------------------
    # SAFETY FILTER
    # -----------------------------------------------------

    data = apply_basic_safety_filter(
        data,
        user_profile["diet_preference"],
        user_profile.get(
            "allergies",
            []
        ),
        user_profile.get(
            "restrictions",
            []
        )
    )

    safe_count = len(data)

    if safe_count == 0:

        return pd.DataFrame(), {
            "initial_foods": initial_count,
            "safe_foods": 0,
            "matched_foods": 0,
            "not_found": [],
            "blocked": [],
            "availability_mode": bool(
                available_foods
            )
        }

    not_found = []
    blocked = []

    # -----------------------------------------------------
    # OPTIONAL AVAILABLE FOOD FILTER
    # -----------------------------------------------------

    if available_foods:

        full_data = load_food_data()

        data, not_found = match_available_foods(
            available_foods,
            data=data,
            full_data=full_data
        )

        # Separate "does not exist in USDA" from "blocked by your
        # diet / allergy settings" so the app can explain it clearly.
        if not_found:
            unfiltered, _ = match_available_foods(
                not_found,
                data=full_data
            )
            blocked = list(unfiltered["user_food"]) if len(unfiltered) else []
            not_found = [f for f in not_found if f not in blocked]

        matched_count = len(data)

        if matched_count == 0:

            return pd.DataFrame(), {
                "initial_foods": initial_count,
                "safe_foods": safe_count,
                "matched_foods": 0,
                "not_found": not_found,
                "blocked": blocked,
                "availability_mode": True
            }

    else:

        data = apply_meal_ready_filter(data)
        matched_count = len(data)

        if matched_count == 0:

            return pd.DataFrame(), {
                "initial_foods": initial_count,
                "safe_foods": safe_count,
                "matched_foods": 0,
                "not_found": [],
                "blocked": [],
                "availability_mode": False
            }

    # -----------------------------------------------------
    # NUTRITIONAL PROFILES
    # -----------------------------------------------------

    food_matrix = create_food_profiles(
        data
    )

    target_vector = create_target_profile(
        targets
    ).reshape(
        1,
        -1
    )

    similarities = cosine_similarity(
        food_matrix,
        target_vector
    ).flatten()

    data["nutrition_score"] = (
        similarities
    )

    # -----------------------------------------------------
    # CALORIE SUITABILITY
    # -----------------------------------------------------

    data["calorie_suitability"] = (
        calculate_calorie_suitability(
            data
        )
    )

    # -----------------------------------------------------
    # USER PREFERENCES
    # -----------------------------------------------------

    likes = normalize_list(
        user_profile.get(
            "likes",
            []
        )
    )

    dislikes = normalize_list(
        user_profile.get(
            "dislikes",
            []
        )
    )

    data["preference_score"] = 0.0

    food_names = (
        data["food_name"]
        .astype(str)
        .str.lower()
    )

    # -----------------------------------------------------
    # LIKES
    # -----------------------------------------------------

    for word in likes:

        exact_match = food_names.str.contains(
            word,
            na=False,
            regex=False
        )

        without_match = food_names.str.contains(
            f"without {word}",
            na=False,
            regex=False
        )

        data.loc[
            exact_match,
            "preference_score"
        ] += 0.35

        data.loc[
            without_match,
            "preference_score"
        ] -= 0.20

        # Basic foods receive a small additional preference.
        basic_mask = (
            exact_match
            &
            data["food_name"]
            .apply(is_basic_food)
        )

        data.loc[
            basic_mask,
            "preference_score"
        ] += 0.08

        # Prepared versions receive lower preference.
        prepared_mask = (
            exact_match
            &
            data["food_name"]
            .apply(is_prepared_food)
        )

        data.loc[
            prepared_mask,
            "preference_score"
        ] -= 0.15

    # -----------------------------------------------------
    # DISLIKES
    # -----------------------------------------------------

    for word in dislikes:

        mask = food_names.str.contains(
            word,
            na=False,
            regex=False
        )

        data.loc[
            mask,
            "preference_score"
        ] -= 0.25

    # -----------------------------------------------------
    # RECENT HISTORY (profile-specific): gently reduce repetition.
    # Applied BEFORE the final score so it really affects ranking.
    # -----------------------------------------------------

    recent_foods = normalize_list(user_profile.get("recent_foods", []))
    if recent_foods:
        recent_mask = food_names.apply(
            lambda name: any(previous == name for previous in recent_foods)
        )
        data.loc[recent_mask, "preference_score"] -= 0.12

    # -----------------------------------------------------
    # FINAL SCORE
    # -----------------------------------------------------

    data["final_score"] = (
        data["nutrition_score"] * 0.70
        +
        data["calorie_suitability"] * 0.15
        +
        data["preference_score"]
    )

    # -----------------------------------------------------
    # SORT
    # -----------------------------------------------------

    data = data.sort_values(
        "final_score",
        ascending=False
    ).reset_index(
        drop=True
    )

    if available_foods:

        # Strict pantry mode: return EVERY matched food (nothing is dropped
        # by top_k or diversity rules and nothing is added).
        return data, {
            "initial_foods": initial_count,
            "safe_foods": safe_count,
            "matched_foods": matched_count,
            "not_found": not_found,
            "blocked": blocked,
            "availability_mode": True
        }

    # -----------------------------------------------------
    # GUARANTEE LIKED FOODS IN CANDIDATE POOL
    # -----------------------------------------------------

    data_with_likes = include_liked_foods(
        data,
        likes,
        top_k
    )

    # -----------------------------------------------------
    # DIVERSITY
    # -----------------------------------------------------

    liked_ids = []

    if likes:

        food_names = (
            data_with_likes["food_name"]
            .astype(str)
            .str.lower()
        )

        for word in likes:

            matches = data_with_likes[
                food_names.str.contains(
                    word,
                    na=False,
                    regex=False
                )
            ]

            matches = matches[
                ~matches["food_name"]
                .apply(is_prepared_food)
            ]

            if not matches.empty:

                liked_ids.append(
                    matches.iloc[0]["fdc_id"]
                )

    liked_ids = list(
        dict.fromkeys(
            liked_ids
        )
    )

    liked_rows = data_with_likes[
        data_with_likes["fdc_id"].isin(
            liked_ids
        )
    ]

    remaining = data_with_likes[
        ~data_with_likes["fdc_id"].isin(
            liked_ids
        )
    ]

    remaining = remaining.sort_values(
        "final_score",
        ascending=False
    )

    recommendations = apply_diversity(
        remaining,
        top_k,
        already_selected=liked_ids
    )

    if not liked_rows.empty:

        recommendations = pd.concat(
            [
                liked_rows,
                recommendations
            ],
            ignore_index=True
        )

    recommendations = (
        recommendations
        .drop_duplicates(
            subset=["fdc_id"]
        )
        .head(top_k)
        .reset_index(drop=True)
    )

    # -----------------------------------------------------
    # RETURN
    # -----------------------------------------------------

    return recommendations, {
        "initial_foods": initial_count,
        "safe_foods": safe_count,
        "matched_foods": matched_count,
        "not_found": not_found,
        "blocked": blocked,
        "availability_mode": False
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    from nutrition_targets import calculate_targets

    user_profile = {
        "age": 21,
        "gender": "male",
        "height_cm": 170,
        "weight_kg": 55,
        "activity_level": "moderate",
        "goal": "maintenance",
        "diet_preference": "no_restriction",
        "allergies": ["peanut"],
        "restrictions": [],
        "likes": [
            "chicken",
            "rice"
        ],
        "dislikes": [
            "broccoli"
        ]
    }

    # Optional.
    # Use [] to test normal USDA recommendation mode.

    available_foods = [
        "rice",
        "chicken",
        "dal",
        "banana"
    ]

    targets = calculate_targets(
        age=user_profile["age"],
        gender=user_profile["gender"],
        weight_kg=user_profile["weight_kg"],
        height_cm=user_profile["height_cm"],
        activity_level=user_profile["activity_level"],
        goal=user_profile["goal"]
    )

    recommendations, stats = (
        calculate_recommendations(
            user_profile,
            targets,
            available_foods=available_foods,
            top_k=10
        )
    )

    print("=" * 50)
    print("RECOMMENDATION ENGINE")
    print("=" * 50)

    print(
        "\nInitial foods:",
        stats["initial_foods"]
    )

    print(
        "Safe foods:",
        stats["safe_foods"]
    )

    print(
        "Matched available foods:",
        stats["matched_foods"]
    )

    print(
        "Not found:",
        stats["not_found"]
    )

    print(
        "Availability mode:",
        stats["availability_mode"]
    )

    print("\nTop Recommendations:")

    if len(recommendations) > 0:

        columns = [
            "food_name",
            "category",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g",
            "nutrition_score",
            "final_score"
        ]

        if "user_food" in recommendations.columns:

            columns.insert(
                1,
                "user_food"
            )

        print(
            recommendations[
                columns
            ].to_string(
                index=False
            )
        )

    else:

        print(
            "No suitable foods found."
        )