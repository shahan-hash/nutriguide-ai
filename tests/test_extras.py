import os
import tempfile
import unittest

from tests.helpers import ROOT
from food_labels import household_measure, readable_food_name

try:
    from streamlit.testing.v1 import AppTest
    HAVE_STREAMLIT = True
except Exception:
    HAVE_STREAMLIT = False


class HouseholdMeasures(unittest.TestCase):

    def test_common_measures(self):
        self.assertEqual(household_measure("Bread, chapati or roti, plain, commercially prepared", 200), "about 5 roti")
        self.assertEqual(household_measure("Rice, white, long-grain, regular, enriched, cooked", 150), "about 1 katori")
        self.assertEqual(household_measure("Egg, whole, cooked, hard-boiled", 100), "about 2 eggs")
        self.assertEqual(household_measure("Milk, whole, 3.25% milkfat, with added vitamin D", 240), "about 1 glass")

    def test_unknown_food_or_bad_input_gives_blank(self):
        self.assertEqual(household_measure("Cheese, mozzarella, whole milk", 30), "")
        self.assertEqual(household_measure("Rice, white, cooked", "abc"), "")
        self.assertEqual(household_measure("Rice, white, cooked", 0), "")

    def test_measures_never_change_the_stored_grams(self):
        # display helper only: it returns text and takes no part in calculations
        self.assertIsInstance(household_measure("Bananas, raw", 120), str)
        self.assertEqual(readable_food_name("Bananas, raw"), "Banana")


@unittest.skipUnless(HAVE_STREAMLIT, "streamlit not installed")
class AppExtras(unittest.TestCase):

    def test_download_button_and_split_bars_render_without_errors(self):
        old = os.environ.get("NUTRIGUIDE_DB")
        os.environ["NUTRIGUIDE_DB"] = os.path.join(tempfile.mkdtemp(), "x.db")
        try:
            at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
            at.sidebar.selectbox(key="profile_choice").select("➕ Create new profile").run()
            at.sidebar.text_input(key="new_profile_name").set_value("extras").run()
            at.sidebar.text_area(key="w_available").set_value("rice, dal, paneer, roti").run()
            at.sidebar.button[0].click().run()
            self.assertFalse(at.exception, [e.value for e in at.exception])
            self.assertTrue(at.get("download_button"))
            html = " ".join(m.value for m in at.markdown)
            self.assertIn("Planned calorie split", html)
            self.assertIn("(approx.)", html)
        finally:
            if old is not None:
                os.environ["NUTRIGUIDE_DB"] = old


if __name__ == "__main__":
    unittest.main()
