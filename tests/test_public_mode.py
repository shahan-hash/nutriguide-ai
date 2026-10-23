"""Public demo mode: visitors must never see each other's profiles."""
import os
import tempfile
import unittest

from tests.helpers import ROOT

try:
    from streamlit.testing.v1 import AppTest
    HAVE_STREAMLIT = True
except Exception:
    HAVE_STREAMLIT = False

NEW = "➕ Create new profile"


@unittest.skipUnless(HAVE_STREAMLIT, "streamlit not installed")
class PublicMode(unittest.TestCase):

    def setUp(self):
        self._old = {k: os.environ.get(k) for k in ("NUTRIGUIDE_DB", "NUTRIGUIDE_PUBLIC")}
        os.environ["NUTRIGUIDE_DB"] = os.path.join(tempfile.mkdtemp(), "pub.db")
        os.environ["NUTRIGUIDE_PUBLIC"] = "1"

    def tearDown(self):
        for key, value in self._old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _visitor(self, name):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
        at.sidebar.selectbox(key="profile_choice").select(NEW).run()
        at.sidebar.text_input(key="new_profile_name").set_value(name).run()
        at.sidebar.text_area(key="w_available").set_value("rice, dal, paneer, roti").run()
        at.sidebar.button[0].click().run()
        self.assertFalse(at.exception, [e.value for e in at.exception])
        return at

    def test_two_visitors_do_not_see_each_other(self):
        import history_store as hs
        alice = self._visitor("alice")
        bob = AppTest.from_file(str(ROOT / "app.py"), default_timeout=180).run()
        options = list(bob.sidebar.selectbox(key="profile_choice").options)
        self.assertEqual(options, [NEW])                       # Bob sees no profiles at all
        token = alice.session_state["session_token"]
        stored = [pid for pid, _ in hs.list_profiles()]
        self.assertEqual(len(stored), 1)
        self.assertTrue(stored[0].startswith(token + "~"))     # saved under Alice's private prefix
        self.assertNotEqual(token, bob.session_state["session_token"])
        self.assertTrue(any("Public demo" in c.value for c in alice.sidebar.caption))

    def test_same_visitor_keeps_own_profile_in_session(self):
        alice = self._visitor("alice")
        alice.run()                                            # next rerun lists her saved profile
        options = list(alice.sidebar.selectbox(key="profile_choice").options)
        self.assertEqual(len(options), 2)                      # "Create new" + her own profile


if __name__ == "__main__":
    unittest.main()
