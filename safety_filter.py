import pandas as pd


def normalize_list(items):
    if not items:
        return []

    return [
        str(item).strip().lower()
        for item in items
        if str(item).strip()
    ]


def apply_diet_filter(data, diet_preference):
    diet = diet_preference.lower().strip()

    if diet == "vegetarian":
        data = data[data["is_vegetarian"] == True]

    elif diet == "vegan":
        data = data[data["is_vegan"] == True]

    elif diet == "eggetarian":
        data = data[
            (data["is_vegetarian"] == True) |
            (data["contains_egg"] == True)
        ]

    elif diet in ["non-vegetarian", "non_vegetarian"]:
        pass

    elif diet in ["no_restriction", "anything"]:
        pass

    return data


def apply_allergy_filter(data, allergies):
    allergies = normalize_list(allergies)

    if "peanut" in allergies or "peanuts" in allergies:
        data = data[
            data["contains_nuts"] == False
        ]

    if "nut" in allergies or "nuts" in allergies:
        data = data[
            data["contains_nuts"] == False
        ]

    if "milk" in allergies or "dairy" in allergies:
        data = data[
            data["contains_dairy"] == False
        ]

    if "egg" in allergies or "eggs" in allergies:
        data = data[
            data["contains_egg"] == False
        ]

    if "fish" in allergies:
        data = data[
            data["contains_fish"] == False
        ]

    if "shellfish" in allergies:
        data = data[
            data["contains_shellfish"] == False
        ]

    if "alcohol" in allergies:
        data = data[
            data["contains_alcohol"] == False
        ]

    return data


def apply_restriction_filter(data, restrictions):
    restrictions = normalize_list(restrictions)

    if "no nuts" in restrictions or "nut free" in restrictions:
        data = data[
            data["contains_nuts"] == False
        ]

    if "dairy free" in restrictions:
        data = data[
            data["contains_dairy"] == False
        ]

    if "egg free" in restrictions:
        data = data[
            data["contains_egg"] == False
        ]

    if "gluten free" in restrictions:
        data = data[
            ~data["category"].str.lower().isin([
                "baked products",
                "cereal grains and pasta"
            ])
        ]

    return data


def filter_safe_foods(food_data, user_profile):
    data = food_data.copy()

    initial_count = len(data)

    data = apply_diet_filter(
        data,
        user_profile["diet_preference"]
    )

    after_diet = len(data)

    data = apply_allergy_filter(
        data,
        user_profile.get("allergies", [])
    )

    after_allergy = len(data)

    data = apply_restriction_filter(
        data,
        user_profile.get("restrictions", [])
    )

    after_restrictions = len(data)

    return data.reset_index(drop=True), {
        "initial_foods": initial_count,
        "after_diet_filter": after_diet,
        "after_allergy_filter": after_allergy,
        "after_restriction_filter": after_restrictions
    }


if __name__ == "__main__":

    nutrition = pd.read_csv(
        "data/processed/nutrition_data.csv"
    )

    constraints = pd.read_csv(
        "data/processed/food_constraints.csv"
    )

    food_data = nutrition.merge(
        constraints.drop(
            columns=["food_name"]
        ),
        on="fdc_id",
        how="inner"
    )

    user_profile = {
        "diet_preference": "no_restriction",
        "allergies": ["peanut"],
        "restrictions": []
    }

    safe_foods, stats = filter_safe_foods(
        food_data,
        user_profile
    )

    print("Safety Filtering Test")
    print("---------------------")

    print("Initial foods:", stats["initial_foods"])
    print("After diet filter:", stats["after_diet_filter"])
    print("After allergy filter:", stats["after_allergy_filter"])
    print(
        "After restriction filter:",
        stats["after_restriction_filter"]
    )

    print("\nSample safe foods:")
    print(
        safe_foods[
            ["fdc_id", "food_name", "category"]
        ].head(10).to_string(index=False)
    )