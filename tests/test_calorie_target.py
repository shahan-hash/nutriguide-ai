import unittest

from tests.helpers import pantry, targets, profile
from meal_planner import (
    create_meal_plan, generate_ranked_meals, calculate_meal_targets, calorie_error,
    coverage_percent,
)
from meal_recommendation import generate_meal_plan


def kcal(entry):
    return sum(f["calories"] for f in entry["foods"])


class CalorieTargets(unittest.TestCase):

    def test_lunch_1000_kcal(self):
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        self.assertAlmostEqual(kcal(plan["Lunch"]), 1000, delta=15)
        self.assertGreaterEqual(plan["Lunch"]["coverage_pct"], 98.5)

    def test_dinner_1000_kcal(self):
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        self.assertAlmostEqual(kcal(plan["Dinner"]), 1000, delta=15)

    def test_breakfast_target(self):
        t = targets(custom_meals={"Breakfast": 450, "Lunch": 800, "Dinner": 700})
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        self.assertAlmostEqual(kcal(plan["Breakfast"]), 450, delta=10)

    def test_any_custom_number_876(self):
        t = targets(custom_meals={"Breakfast": 500, "Lunch": 876, "Dinner": 700})
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        self.assertAlmostEqual(kcal(plan["Lunch"]), 876, delta=10)

    def test_custom_daily_target_is_split_25_40_35(self):
        t = targets(custom_daily=2400)
        mt = calculate_meal_targets(t)
        self.assertAlmostEqual(mt["Lunch"]["calories"], 960)
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        for meal in ("Breakfast", "Lunch", "Dinner"):
            self.assertAlmostEqual(kcal(plan[meal]), mt[meal]["calories"], delta=0.03 * mt[meal]["calories"])

    def test_best_candidate_is_chosen_not_first_acceptable(self):
        """The winner has the smallest calorie error among all ranked candidates."""
        t = targets(custom_meals={"Breakfast": 500, "Lunch": 1000, "Dinner": 700})
        target = calculate_meal_targets(t)["Lunch"]
        ranked = generate_ranked_meals(pantry(), "Lunch", target, max_dishes=3)
        self.assertGreater(len(ranked), 3)
        errors = [abs(calorie_error(c["totals"]["calories"], 1000)) for c in ranked]
        self.assertLessEqual(errors[0], min(errors) + 0.02)
        self.assertTrue(any(e > 0.2 for e in errors))      # weaker candidates exist and were rejected
        self.assertLess(errors[0], 0.02)

    def test_no_faked_percentage_when_infeasible(self):
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        plan = create_meal_plan(pantry(), t, max_dishes=1)         # one dish cannot reach 1000 kcal
        lunch = plan["Lunch"]
        actual = kcal(lunch)
        self.assertLess(actual, 700)
        self.assertAlmostEqual(lunch["coverage_pct"], actual / 1000 * 100, places=6)
        self.assertLess(lunch["coverage_pct"], 70)
        self.assertEqual(lunch["status"], "below target")
        self.assertTrue(any("short" in n for n in lunch["notes"]))   # gap is explained
        self.assertAlmostEqual(lunch["gap_kcal"], actual - 1000, places=6)

    def test_portions_are_realistic(self):
        t = targets(custom_meals={"Breakfast": 600, "Lunch": 1000, "Dinner": 1000})
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        for meal in plan.values():
            for item in meal["foods"]:
                self.assertGreaterEqual(item["quantity_g"], 10)
                self.assertLessEqual(item["quantity_g"], 400)
                self.assertLessEqual(item["calories"], 650.5)    # no single absurd dish

    def test_end_to_end_with_real_pipeline_and_safety(self):
        up = profile(available_foods=["rice", "dal", "paneer", "roti"], available_only=True)
        t = targets(custom_meals={"Breakfast": 500, "Lunch": 876, "Dinner": 700})
        res = generate_meal_plan(up, t, available_foods=["rice", "dal", "paneer", "roti"], max_dishes=3)
        self.assertAlmostEqual(kcal(res["meal_plan"]["Lunch"]), 876, delta=10)


if __name__ == "__main__":
    unittest.main()
