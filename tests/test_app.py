"""End-to-end tests of app.py using Streamlit's own AppTest runner
(runs the real app script headlessly with the real USDA data)."""
import copy
import os
import tempfile
import unittest

from tests.helpers import ROOT

try:
    from streamlit.testing.v1 import AppTest
    HAVE_STREAMLIT = True
except Exception:          # streamlit not importable in this environment
    HAVE_STREAMLIT = False

APP = str(ROOT / "app.py")
NEW = "➕ Create new profile"


def foods_of(plan, meal):
    return [(f["fdc_id"], f["quantity_g"]) for f in plan[meal]["foods"]]


@unittest.skipUnless(HAVE_STREAMLIT, "streamlit not installed")
class AppFlow(unittest.TestCase):

    def setUp(self):
        self._old = os.environ.get("NUTRIGUIDE_DB")
        os.environ["NUTRIGUIDE_DB"] = os.path.join(tempfile.mkdtemp(), "app.db")

    def tearDown(self):
        if self._old is not None:
            os.environ["NUTRIGUIDE_DB"] = self._old

    def _start(self, name="Rahul", foods="rice, dal, paneer, roti"):
        at = AppTest.from_file(APP, default_timeout=180)
        at.run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        at.sidebar.selectbox(key="profile_choice").select(NEW).run()
        at.sidebar.text_input(key="new_profile_name").set_value(name).run()
        at.sidebar.text_area(key="w_available").set_value(foods).run()
        return at

    def _generate(self, at):
        at.sidebar.button[0].click().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        return at.session_state["result"]

    def test_first_load_without_history_or_database(self):
        at = AppTest.from_file(APP, default_timeout=120).run()
        self.assertFalse(at.exception)

    def test_generate_custom_876_and_strict_foods(self):
        at = self._start()
        at.sidebar.selectbox(key="w_cal_mode").select("Custom calories per meal").run()
        at.sidebar.number_input(key="w_cal_l").set_value(876).run()
        result = self._generate(at)
        lunch = result["meal_plan"]["Lunch"]
        self.assertAlmostEqual(lunch["totals"]["calories"], 876, delta=10)
        allowed = set(result["recommendations"]["fdc_id"])
        for meal in result["meal_plan"].values():
            self.assertTrue({f["fdc_id"] for f in meal["foods"]} <= allowed)
        self.assertTrue(at.session_state["availability_mode"])

    def test_replace_each_meal_no_nameerror_and_others_unchanged(self):
        at = self._start()
        self._generate(at)
        for meal in ("Breakfast", "Lunch", "Dinner"):
            before = copy.deepcopy(at.session_state["result"]["meal_plan"])
            at.button(key=f"replace_{meal.lower()}").click().run()
            self.assertFalse(at.exception, [e.value for e in at.exception])      # no NameError / crash
            after = at.session_state["result"]["meal_plan"]
            self.assertNotEqual(foods_of(before, meal), foods_of(after, meal))
            for other in ("Breakfast", "Lunch", "Dinner"):
                if other != meal:
                    self.assertEqual(before[other], after[other])
            allowed = set(at.session_state["result"]["recommendations"]["fdc_id"])
            self.assertTrue({f["fdc_id"] for m in after.values() for f in m["foods"]} <= allowed)

    def test_dish_limit_selector(self):
        at = self._start()
        at.sidebar.selectbox(key="w_max_dishes").select(2).run()
        result = self._generate(at)
        for meal in result["meal_plan"].values():
            self.assertLessEqual(len(meal["foods"]), 2)

    def test_profiles_keep_separate_settings_and_history(self):
        at = self._start("Alice", "rice, dal")
        self._generate(at)
        alice_foods = at.session_state["result"]["meal_plan"]["Lunch"]["foods"]

        at.sidebar.selectbox(key="profile_choice").select(NEW).run()
        at.sidebar.text_input(key="new_profile_name").set_value("Bob").run()
        self.assertFalse(at.session_state["generated"])                    # Alice's plan is not shown for Bob
        self.assertEqual(at.session_state["w_available"], "")             # Bob starts from defaults
        at.sidebar.text_area(key="w_available").set_value("chicken, egg, oats").run()
        self._generate(at)

        at.sidebar.selectbox(key="profile_choice").select("alice").run()
        self.assertEqual(at.session_state["w_available"], "rice, dal")    # Alice's own settings came back
        self.assertFalse(at.exception)

        import history_store as hs
        self.assertEqual(hs.count_plans("alice"), 1)
        self.assertEqual(hs.count_plans("bob"), 1)
        self.assertNotIn("chicken", " ".join(hs.get_recent_food_names("alice", 10)))

    def test_history_period_10_and_15_and_variety_on_regenerate(self):
        at = self._start(foods="rice, dal, paneer, roti, chicken, egg, potato, curd")
        at.sidebar.radio(key="w_history_days").set_value(15).run()
        first = copy.deepcopy(self._generate(at)["meal_plan"])
        self.assertEqual(at.session_state["user_profile"]["history_days"], 15)
        second = self._generate(at)["meal_plan"]                          # regenerate: history now contains plan 1
        changed = [m for m in first if foods_of(first, m) != foods_of(second, m)]
        self.assertTrue(changed, "regenerating with history produced an identical plan")
        at.sidebar.radio(key="w_history_days").set_value(10).run()
        self._generate(at)
        self.assertEqual(at.session_state["user_profile"]["history_days"], 10)

    def test_strict_mode_off_ignores_typed_list_and_says_so(self):
        at = self._start()
        at.sidebar.checkbox(key="w_avail_only").uncheck().run()
        self._generate(at)
        self.assertFalse(at.session_state["availability_mode"])
        self.assertTrue(any("NOT used as a limit" in i.value for i in at.info))


if __name__ == "__main__":
    unittest.main()
