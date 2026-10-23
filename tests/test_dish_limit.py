import unittest

from tests.helpers import pantry, targets, profile
from meal_planner import create_meal_plan, replace_meal_detailed, MEAL_NAMES
from meal_recommendation import generate_meal_plan


class DishLimit(unittest.TestCase):

    def test_limit_never_exceeded_in_generation(self):
        t = targets(custom_meals={"Breakfast": 700, "Lunch": 1200, "Dinner": 1100})
        for limit in (1, 2, 3, 4):
            plan = create_meal_plan(pantry(), t, max_dishes=limit)
            for meal in plan.values():
                self.assertLessEqual(len(meal["foods"]), limit)
                self.assertEqual(meal["max_dishes"], limit)

    def test_limit_is_not_silently_overridden_to_reach_target(self):
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        one = create_meal_plan(pantry(), t, max_dishes=1)["Lunch"]
        three = create_meal_plan(pantry(), t, max_dishes=3)["Lunch"]
        self.assertEqual(len(one["foods"]), 1)
        self.assertLess(one["coverage_pct"], three["coverage_pct"])
        self.assertTrue(any("Allowing 2 dishes" in n for n in one["notes"]))   # tells the user how to improve

    def test_larger_portion_is_not_a_new_dish(self):
        t = targets(custom_meals={"Breakfast": 400, "Lunch": 300, "Dinner": 400})
        small = create_meal_plan(pantry(["rice"]), t, max_dishes=2)
        bigger = create_meal_plan(pantry(["rice"]), targets(custom_meals={"Breakfast": 400, "Lunch": 450, "Dinner": 400}), max_dishes=2)
        self.assertEqual(len(small["Lunch"]["foods"]), 1)
        self.assertEqual(len(bigger["Lunch"]["foods"]), 1)
        self.assertGreater(bigger["Lunch"]["foods"][0]["quantity_g"], small["Lunch"]["foods"][0]["quantity_g"])

    def test_limit_respected_by_replacement(self):
        t = targets()
        up = profile()
        for limit in (1, 2, 3, 4):
            plan = create_meal_plan(pantry(), t, max_dishes=limit)
            for meal in MEAL_NAMES:
                new_plan, _, _ = replace_meal_detailed(plan, meal, pantry(), t, max_dishes=limit, user_profile=up)
                self.assertLessEqual(len(new_plan[meal]["foods"]), limit)

    def test_limit_in_full_pipeline_broad_mode(self):
        up = profile()
        for limit in (1, 2, 3, 4):
            res = generate_meal_plan(up, targets(), available_foods=None, max_dishes=limit)
            for meal in res["meal_plan"].values():
                self.assertLessEqual(len(meal["foods"]), limit)


if __name__ == "__main__":
    unittest.main()
