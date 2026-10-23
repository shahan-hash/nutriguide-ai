import copy
import unittest

from tests.helpers import pantry, targets, profile, FOUR_FOODS
from meal_planner import (
    create_meal_plan, replace_meal_detailed, replace_meal, calculate_daily_summary,
    compare_with_targets, MEAL_NAMES, NUTRIENTS, verify_meal_plan,
)
from meal_recommendation import generate_meal_plan


class ReplaceMeal(unittest.TestCase):

    def setUp(self):
        self.t = targets(custom_meals={"Breakfast": 500, "Lunch": 876, "Dinner": 700})
        self.up = profile()
        res = generate_meal_plan(
            profile(available_foods=FOUR_FOODS, available_only=True), self.t,
            available_foods=FOUR_FOODS, max_dishes=3,
        )
        self.pool = res["recommendations"]
        self.plan = res["meal_plan"]

    def test_replace_each_meal_leaves_other_two_exactly_unchanged(self):
        for meal in MEAL_NAMES:
            before = copy.deepcopy(self.plan)
            new_plan, changed, message = replace_meal_detailed(
                self.plan, meal, self.pool, self.t, max_dishes=3, user_profile=self.up)
            self.assertTrue(changed, message)
            for other in MEAL_NAMES:
                if other != meal:
                    self.assertEqual(new_plan[other], before[other])        # foods AND portions identical
            self.assertEqual(self.plan, before)                             # input plan not mutated
            old_sig = sorted(f["fdc_id"] for f in before[meal]["foods"])
            new_sig = sorted(f["fdc_id"] for f in new_plan[meal]["foods"])
            self.assertNotEqual(old_sig, new_sig)                           # a different COMBINATION
            self.assertEqual(verify_meal_plan(new_plan, max_dishes=3), {})

    def test_totals_are_recalculated_after_replacement(self):
        new_plan, changed, _ = replace_meal_detailed(
            self.plan, "Lunch", self.pool, self.t, max_dishes=3, user_profile=self.up)
        self.assertTrue(changed)
        lunch = new_plan["Lunch"]
        self.assertAlmostEqual(lunch["totals"]["calories"], sum(f["calories"] for f in lunch["foods"]), places=9)
        self.assertAlmostEqual(lunch["coverage_pct"], lunch["totals"]["calories"] / 876 * 100, places=6)
        daily = calculate_daily_summary(new_plan)
        for n in NUTRIENTS:
            self.assertAlmostEqual(daily[n], sum(f[n] for m in MEAL_NAMES for f in new_plan[m]["foods"]), places=9)
        self.assertIn("calories", compare_with_targets(daily, self.t))
        # still close to the lunch target
        self.assertAlmostEqual(lunch["totals"]["calories"], 876, delta=0.15 * 876)

    def test_repeated_clicks_cycle_through_different_combinations(self):
        plan, seen = self.plan, []
        for _ in range(4):
            plan, changed, _ = replace_meal_detailed(plan, "Lunch", self.pool, self.t, max_dishes=3, user_profile=self.up)
            self.assertTrue(changed)
            seen.append(tuple(sorted(f["fdc_id"] for f in plan["Lunch"]["foods"])))
        self.assertGreaterEqual(len(set(seen)), 3)

    def test_no_alternative_keeps_original_and_explains(self):
        pool = pantry(["rice"])                      # a single food: only one possible combination
        plan = create_meal_plan(pool, self.t, max_dishes=3)
        before = copy.deepcopy(plan)
        for meal in MEAL_NAMES:
            new_plan, changed, message = replace_meal_detailed(plan, meal, pool, self.t, max_dishes=3, user_profile=self.up)
            self.assertFalse(changed)
            self.assertEqual(new_plan, before)
            self.assertIn("No different", message)

    def test_empty_pool_does_not_crash(self):
        new_plan, changed, message = replace_meal_detailed(self.plan, "Lunch", pantry(["dosa"]), self.t)
        self.assertFalse(changed)
        self.assertEqual(new_plan, self.plan)
        self.assertTrue(message)

    def test_compat_wrapper(self):
        new_plan, changed = replace_meal(self.plan, "Dinner", self.pool, self.t, max_dishes=3)
        self.assertTrue(changed)
        self.assertEqual(new_plan["Breakfast"], self.plan["Breakfast"])


if __name__ == "__main__":
    unittest.main()
