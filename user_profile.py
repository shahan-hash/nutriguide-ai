"""Plain-dictionary user profile used by the recommendation pipeline."""

DEFAULT_MAX_DISHES = 3
DEFAULT_HISTORY_DAYS = 10


def create_user_profile(
    age,
    gender,
    height_cm,
    weight_kg,
    activity_level,
    goal,
    diet_preference,
    allergies=None,
    restrictions=None,
    likes=None,
    dislikes=None,
    profile_id="my-profile",
    available_foods=None,
    available_only=False,
    max_dishes=DEFAULT_MAX_DISHES,
    history_days=DEFAULT_HISTORY_DAYS,
):
    profile = {
        "profile_id": profile_id,
        "age": age,
        "gender": gender,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "activity_level": activity_level,
        "goal": goal,
        "diet_preference": diet_preference,
        "allergies": allergies or [],
        "restrictions": restrictions or [],
        "likes": likes or [],
        "dislikes": dislikes or [],
        "available_foods": available_foods or [],
        "available_only": bool(available_only and available_foods),
        "max_dishes": int(max_dishes),
        "history_days": int(history_days),
        # filled by the app from the local history database
        "recent_foods": [],
        "recent_meals": {},
    }

    return profile


if __name__ == "__main__":

    profile = create_user_profile(
        age=21,
        gender="male",
        height_cm=170,
        weight_kg=55,
        activity_level="moderate",
        goal="maintenance",
        diet_preference="no_restriction",
        allergies=["peanut"],
        restrictions=[],
        likes=["rice", "chicken"],
        dislikes=["broccoli"],
    )

    print("User Profile")
    print("------------")

    for key, value in profile.items():
        print(f"{key}: {value}")
