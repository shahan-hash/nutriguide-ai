import unittest

from tests.helpers import pantry, targets, profile, FOUR_FOODS
from available_foods import match_available_foods, load_food_data
from meal_planner import create_meal_plan, replace_meal_detailed, MEAL_NAMES
from meal_recommendation import generate_meal_plan
from recommendation_engine import calculate_recommendations


def used_ids(plan):
    return {f["fdc_id"] for m in plan.values() for f in m["foods"]}


class StrictPantry(unittest.TestCase):

    def test_four_foods_match_expected_usda_rows(self):
        rows = pantry()
        self.assertEqual(len(rows), 4)
        names = " | ".join(rows["food_name"]).lower()
        for word in ("rice", "lentils", "mozzarella", "chapati"):
            self.assertIn(word, names)

    def test_every_dish_comes_from_the_four_foods_in_all_meals(self):
        rows = pantry()
        allowed = set(rows["fdc_id"])
        for dishes in (1, 2, 3, 4):
            for custom in (None, {"Breakfast": 700, "Lunch": 1200, "Dinner": 1000}):
                plan = create_meal_plan(rows, targets(custom_meals=custom), max_dishes=dishes)
                self.assertTrue(used_ids(plan) <= allowed, (dishes, used_ids(plan) - allowed))

    def test_full_pipeline_never_adds_unselected_foods(self):
        up = profile(available_foods=FOUR_FOODS, available_only=True, likes=["chicken", "egg", "oats"])
        res = generate_meal_plan(up, targets(), available_foods=FOUR_FOODS, max_dishes=3)
        allowed = set(res["recommendations"]["fdc_id"])
        self.assertEqual(len(allowed), 4)
        self.assertTrue(used_ids(res["meal_plan"]) <= allowed)
        text = " ".join(f["food_name"].lower() for m in res["meal_plan"].values() for f in m["foods"])
        for banned in ("oat", "chicken", "egg"):
            self.assertNotIn(banned, text)

    def test_replacement_and_regeneration_never_add_unselected_foods(self):
        up = profile(available_foods=FOUR_FOODS, available_only=True)
        t = targets()
        res = generate_meal_plan(up, t, available_foods=FOUR_FOODS, max_dishes=3)
        allowed = set(res["recommendations"]["fdc_id"])
        plan = res["meal_plan"]
        for _ in range(4):
            for meal in MEAL_NAMES:
                plan, _, _ = replace_meal_detailed(plan, meal, res["recommendations"], t, max_dishes=3, user_profile=up)
                self.assertTrue(used_ids(plan) <= allowed)
        again = generate_meal_plan(up, t, available_foods=FOUR_FOODS, max_dishes=3)
        self.assertTrue(used_ids(again["meal_plan"]) <= allowed)

    def test_four_foods_cannot_reach_target_reports_shortfall_without_extra_foods(self):
        # Only rice + dal: cannot reach 1000 kcal at realistic portions with 2 dishes.
        rows = pantry(["rice", "dal"])
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        plan = create_meal_plan(rows, t, max_dishes=2)
        lunch = plan["Lunch"]
        self.assertLess(lunch["totals"]["calories"], 970)
        self.assertTrue(used_ids(plan) <= set(rows["fdc_id"]))
        self.assertTrue(any("short" in n for n in lunch["notes"]))
        self.assertTrue(any("Add more available foods" in n for n in lunch["notes"]))

    def test_unknown_food_and_blocked_food_are_explained(self):
        up = profile(diet_preference="vegan")
        pool, stats = calculate_recommendations(up, targets(), available_foods=["rice", "dosa", "egg", "chicken"], top_k=30)
        self.assertIn("dosa", stats["not_found"])          # not in USDA SR Legacy
        self.assertIn("egg", stats["blocked"])             # exists, blocked by vegan filter
        self.assertIn("chicken", stats["blocked"])
        self.assertEqual(list(pool["user_food"]), ["rice"])

    def test_allergy_filter_still_applies_in_pantry_mode(self):
        up = profile(allergies=["dairy"])
        pool, stats = calculate_recommendations(up, targets(), available_foods=FOUR_FOODS, top_k=30)
        self.assertNotIn("Paneer", list(pool["user_food"]))
        self.assertIn("Paneer", stats["blocked"])

    def test_vegetarian_excludes_eggs_but_eggetarian_allows(self):
        for diet, expect_egg in (("vegetarian", False), ("eggetarian", True)):
            up = profile(diet_preference=diet)
            pool, _ = calculate_recommendations(up, targets(), available_foods=["egg", "rice"], top_k=30)
            self.assertEqual("egg" in set(pool["user_food"].str.lower()), expect_egg, diet)

    def test_same_food_typed_twice_is_one_dish(self):
        rows, _ = match_available_foods(["dal", "lentils", "rice"], data=load_food_data())
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
