import unittest
import numpy as np
import pandas as pd

from tests.helpers import pantry, targets
from meal_planner import (
    calculate_portion_nutrition, create_food_item, meal_totals, calculate_daily_summary,
    compare_with_targets, calculate_meal_targets, coverage_percent, create_meal_plan,
    verify_meal_plan, NUTRIENTS, MEAL_NAMES,
)


class NutritionMath(unittest.TestCase):

    def test_per_100g_to_portion(self):
        row = {"calories": 130.0, "protein_g": 2.7, "carbs_g": 28.0, "fat_g": 0.3, "fiber_g": 0.4}
        n = calculate_portion_nutrition(row, 250)
        self.assertAlmostEqual(n["calories"], 325.0)
        self.assertAlmostEqual(n["protein_g"], 6.75)
        self.assertAlmostEqual(n["carbs_g"], 70.0)

    def test_missing_and_bad_values_are_safe(self):
        row = {"calories": np.nan, "protein_g": None, "carbs_g": -5, "fat_g": "abc", "fiber_g": 1.0}
        n = calculate_portion_nutrition(row, 100)
        self.assertEqual(n["calories"], 0.0)
        self.assertEqual(n["protein_g"], 0.0)
        self.assertEqual(n["carbs_g"], 0.0)
        self.assertEqual(n["fat_g"], 0.0)
        self.assertEqual(calculate_portion_nutrition(row, -50)["fiber_g"], 0.0)   # negative grams
        self.assertEqual(calculate_portion_nutrition(row, 0)["fiber_g"], 0.0)     # zero grams

    def test_meal_total_equals_sum_of_foods_and_is_not_rounded(self):
        pool = pantry()
        a = create_food_item(pool.iloc[0], 233)
        b = create_food_item(pool.iloc[1], 117)
        total = meal_totals([a, b])
        for nutrient in NUTRIENTS:
            self.assertAlmostEqual(total[nutrient], a[nutrient] + b[nutrient], places=9)
        # kept at full precision (rounding is display-only)
        self.assertNotEqual(a["calories"], round(a["calories"], 1))

    def test_dataset_values_used_directly(self):
        pool = pantry()
        rice = pool[pool["user_food"] == "Rice"].iloc[0]
        item = create_food_item(rice, 200)
        self.assertAlmostEqual(item["calories"], rice["calories"] * 2.0)   # no macro re-estimation

    def test_daily_equals_sum_of_meals_and_meal_targets_sum_to_daily(self):
        t = targets()
        plan = create_meal_plan(pantry(), t, max_dishes=3)
        daily = calculate_daily_summary(plan)
        for nutrient in NUTRIENTS:
            manual = sum(f[nutrient] for m in MEAL_NAMES for f in plan[m]["foods"])
            self.assertAlmostEqual(daily[nutrient], manual, places=9)
        mt = calculate_meal_targets(t)
        self.assertAlmostEqual(sum(v["calories"] for v in mt.values()), t["calorie_target"], places=6)
        self.assertAlmostEqual(sum(v["protein_g"] for v in mt.values()), t["protein_g"], places=6)

    def test_custom_meal_targets_sum_and_coverage_gap(self):
        t = targets(custom_meals={"Breakfast": 500, "Lunch": 876, "Dinner": 700})
        self.assertEqual(t["calorie_target"], 2076)
        self.assertEqual(calculate_meal_targets(t)["Lunch"]["calories"], 876)
        self.assertAlmostEqual(coverage_percent(970, 1000), 97.0)
        self.assertAlmostEqual(coverage_percent(1000, 1000), 100.0)
        self.assertAlmostEqual(coverage_percent(1100, 1000), 110.0)   # never capped at 100

    def test_compare_with_targets(self):
        t = targets()
        summary = {"calories": t["calorie_target"] * 0.5, "protein_g": t["protein_g"],
                   "carbs_g": t["carbs_g"] * 1.5, "fat_g": t["fat_g"], "fiber_g": t["fiber_g"]}
        cmp = compare_with_targets(summary, t)
        self.assertEqual(cmp["calories"]["status"], "below target")
        self.assertEqual(cmp["protein_g"]["status"], "on target")
        self.assertEqual(cmp["carbs_g"]["status"], "above target")
        self.assertAlmostEqual(cmp["calories"]["coverage_percent"], 50.0)

    def test_verification_independent_recalculation(self):
        plan = create_meal_plan(pantry(), targets(), max_dishes=3)
        self.assertEqual(verify_meal_plan(plan, max_dishes=3), {})
        plan["Lunch"]["foods"][0]["calories"] += 5            # tamper
        self.assertIn("Lunch", verify_meal_plan(plan, max_dishes=3))


if __name__ == "__main__":
    unittest.main()
