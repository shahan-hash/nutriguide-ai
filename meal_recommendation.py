"""Glue between the recommender (Stage A/ranking) and the meal planner."""
from recommendation_engine import calculate_recommendations
from meal_planner import (
    create_meal_plan,
    calculate_daily_summary,
    clamp_dishes,
)

BROAD_POOL_SIZE = 45      # foods kept when NO available-food list is given


def get_eligible_foods(user_profile, targets, available_foods=None):
    """Stage A: safety-filtered (and, if asked, pantry-only) food pool.

    ``available_foods`` is a list of typed foods when "available foods only"
    mode is ON, otherwise None.  The returned DataFrame is the ONLY source of
    foods for generation, replacement and regeneration.
    """
    return calculate_recommendations(
        user_profile=user_profile,
        targets=targets,
        available_foods=available_foods or None,
        top_k=BROAD_POOL_SIZE,
    )


def generate_meal_plan(user_profile, targets, available_foods=None, max_dishes=None):
    if max_dishes is None:
        max_dishes = (user_profile or {}).get("max_dishes", 3)
    max_dishes = clamp_dishes(max_dishes)

    recommendations, stats = get_eligible_foods(user_profile, targets, available_foods)
    stats = dict(stats)
    stats["max_dishes"] = max_dishes

    if recommendations.empty:
        return {
            "recommendations": recommendations,
            "meal_plan": {},
            "daily_summary": {},
            "stats": stats,
            "max_dishes": max_dishes,
        }

    meal_plan = create_meal_plan(
        recommendations,
        targets,
        max_dishes=max_dishes,
        user_profile=user_profile,
    )

    return {
        "recommendations": recommendations,
        "meal_plan": meal_plan,
        "daily_summary": calculate_daily_summary(meal_plan),
        "stats": stats,
        "max_dishes": max_dishes,
    }
