import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

from tests.helpers import pantry, targets, profile, ROOT
import history_store as hs
from meal_planner import create_meal_plan, generate_ranked_meals, calculate_meal_targets
from meal_recommendation import generate_meal_plan

POOL_FOODS = ["rice", "dal", "paneer", "roti", "chicken", "egg", "potato", "curd", "oats", "banana"]


def days_ago(n):
    return (datetime.now() - timedelta(days=n)).isoformat(timespec="seconds")


class ProfilesAndHistory(unittest.TestCase):

    def setUp(self):
        self._old = os.environ.get("NUTRIGUIDE_DB")
        os.environ["NUTRIGUIDE_DB"] = os.path.join(tempfile.mkdtemp(), "h.db")

    def tearDown(self):
        if self._old is not None:
            os.environ["NUTRIGUIDE_DB"] = self._old

    def _plan(self, foods=None, dishes=3):
        return create_meal_plan(pantry(foods or POOL_FOODS), targets(), max_dishes=dishes)

    def test_missing_database_and_empty_history_are_safe(self):
        self.assertFalse(os.path.exists(os.environ["NUTRIGUIDE_DB"]))
        self.assertEqual(hs.list_profiles(), [])
        self.assertEqual(hs.get_recent_plans("nobody"), [])
        self.assertEqual(hs.get_recent_food_names("nobody"), [])
        self.assertEqual(hs.get_recent_meals("nobody"), {"Breakfast": [], "Lunch": [], "Dinner": []})
        self.assertIsNone(hs.load_profile_settings("nobody"))
        self.assertEqual(hs.count_plans("nobody"), 0)

    def test_new_profile_settings_roundtrip(self):
        hs.save_profile_settings("Rahul", {"age": 22, "available": "rice, dal", "max_dishes": 2}, display_name="Rahul")
        self.assertEqual(hs.load_profile_settings("  rahul "), {"age": 22, "available": "rice, dal", "max_dishes": 2})
        self.assertEqual(hs.list_profiles(), [("rahul", "Rahul")])

    def test_history_survives_application_restart(self):
        plan = self._plan()
        row = hs.save_meal_plan("rahul", plan)
        self.assertIsNotNone(row)
        code = (
            "import history_store as h, json; "
            "print(json.dumps({'n': h.count_plans('rahul'), 'foods': len(h.get_recent_food_names('rahul', 10))}))"
        )
        out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True,
                             env=dict(os.environ)).stdout
        data = json.loads(out)
        self.assertEqual(data["n"], 1)
        self.assertGreater(data["foods"], 3)

    def test_two_profiles_never_mix(self):
        a = self._plan(["rice", "dal"])
        b = self._plan(["chicken", "egg", "oats"])
        hs.save_meal_plan("alice", a)
        hs.save_meal_plan("bob", b)
        alice = " ".join(hs.get_recent_food_names("alice", 10))
        bob = " ".join(hs.get_recent_food_names("bob", 10))
        self.assertIn("rice", alice); self.assertNotIn("chicken", alice)
        self.assertIn("chicken", bob); self.assertNotIn("rice", bob)
        hs.save_profile_settings("alice", {"diet": "Vegan"})
        hs.save_profile_settings("bob", {"diet": "Non-Vegetarian"})
        self.assertEqual(hs.load_profile_settings("alice")["diet"], "Vegan")
        self.assertEqual(hs.load_profile_settings("bob")["diet"], "Non-Vegetarian")
        hs.clear_history("alice")
        self.assertEqual(hs.count_plans("alice"), 0)
        self.assertEqual(hs.count_plans("bob"), 1)

    def test_10_and_15_day_windows(self):
        plan = self._plan()
        hs.save_meal_plan("sam", plan, created_at=days_ago(3))
        hs.save_meal_plan("sam", plan, created_at=days_ago(12))
        hs.save_meal_plan("sam", plan, created_at=days_ago(20))
        self.assertEqual(len(hs.get_recent_plans("sam", days=10)), 1)
        self.assertEqual(len(hs.get_recent_plans("sam", days=15)), 2)
        self.assertEqual(len(hs.get_recent_meals("sam", 10)["Lunch"]), 1)
        self.assertEqual(len(hs.get_recent_meals("sam", 15)["Lunch"]), 2)

    def test_update_plan_replaces_row_not_duplicates(self):
        plan = self._plan()
        row = hs.save_meal_plan("sam", plan)
        plan2 = dict(plan); plan2["Lunch"] = plan["Dinner"]
        self.assertTrue(hs.update_meal_plan(row, "sam", plan2))
        self.assertEqual(hs.count_plans("sam"), 1)
        self.assertFalse(hs.update_meal_plan(row, "someone-else", plan2))   # wrong profile cannot overwrite

    def test_history_encourages_variety_without_harming_fit(self):
        t = targets(custom_meals={"Breakfast": 500, "Lunch": 876, "Dinner": 700})
        up = profile()
        first = create_meal_plan(pantry(POOL_FOODS), t, max_dishes=3, user_profile=up)
        hs.save_meal_plan("v", first, created_at=days_ago(1))

        for days in (10, 15):
            up2 = profile()
            up2["recent_meals"] = hs.get_recent_meals("v", days)
            second = create_meal_plan(pantry(POOL_FOODS), t, max_dishes=3, user_profile=up2)
            for meal in ("Breakfast", "Lunch", "Dinner"):
                old = sorted(f["fdc_id"] for f in first[meal]["foods"])
                new = sorted(f["fdc_id"] for f in second[meal]["foods"])
                self.assertNotEqual(old, new, f"{meal} repeated with {days}-day history")
                gap_first = abs(first[meal]["coverage_pct"] - 100)
                gap_second = abs(second[meal]["coverage_pct"] - 100)
                self.assertLess(gap_second, gap_first + 6, f"{meal} fit got worse than 6 points")

    def test_history_cannot_force_unavailable_or_unsafe_foods(self):
        """With only two foods, history must allow reusing them."""
        t = targets()
        pool = pantry(["rice", "dal"])
        first = create_meal_plan(pool, t, max_dishes=2)
        up = profile()
        up["recent_meals"] = {m: [[f["food_name"] for f in first[m]["foods"]]] for m in first}
        second = create_meal_plan(pool, t, max_dishes=2, user_profile=up)
        allowed = set(pool["fdc_id"])
        self.assertTrue({f["fdc_id"] for m in second.values() for f in m["foods"]} <= allowed)
        self.assertTrue(all(m["foods"] for m in second.values()))


if __name__ == "__main__":
    unittest.main()
