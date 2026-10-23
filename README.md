# NutriGuide AI - AI-Based Personalized Nutrition Recommendation System Using Health Analytics

B.Tech project. Python, Pandas, NumPy, SciPy, Scikit-learn, Streamlit and the
USDA FoodData Central **SR Legacy** dataset.

The app builds a Breakfast / Lunch / Dinner plan whose **real calories come as close as
possible to the calorie target** (for example Lunch = 876 kcal), using only safe foods,
only the foods you say you have, and no more dishes than you allow.

---

## 1. How to run (Windows PowerShell, from scratch)

1. Install **Python 3.10 or 3.11** from python.org. On the first installer screen tick
   **"Add python.exe to PATH"**. Check it:

```powershell
python --version
```

2. Extract the ZIP (for example to `D:\projects`) and open PowerShell in the project folder
   (the folder that contains `app.py`):

```powershell
cd D:\projects\nutrition_health_analytics
dir
```

3. Create and activate a virtual environment (do NOT copy an old `venv` from another PC):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell says scripts are disabled, run this once and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

4. Install the libraries and start the app:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The browser opens at `http://localhost:8501`. Stop with `Ctrl + C`.

**Next time** only:

```powershell
cd D:\projects\nutrition_health_analytics
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

### Run the tests

```powershell
python -m unittest discover -s tests -t . -v
```

(You can also use `pip install pytest` and run `pytest`.) The tests use the real CSV files
in `data/processed` and a temporary database, so your own history is never touched.

### Data files

`data/processed/` (already included) holds `nutrition_data.csv`, `final_food_constraints.csv`
and `food_features.csv`, which the app needs. `data/raw/FoodData_Central_sr_legacy_food_csv_2018-04`
is only needed if you want to re-run `preprocess.py` / `food_constraints.py` /
`feature_engineering.py`. The history database `data/processed/meal_history.db` is created
automatically on first use and is ignored by Git.

---

## 2. Using the app

1. **Profile** (top of the sidebar): choose a profile or "Create new profile". Each profile has its
   own saved settings and its own meal history. It is a **local nickname, not a secure login**.
2. Fill in age, gender, height, weight, activity, goal, diet, allergies, restrictions, likes, dislikes.
3. **Calorie target**
   - *Auto*: from BMR/TDEE and your goal.
   - *Custom daily calories*: split 25% / 40% / 35%.
   - *Custom calories per meal*: for example Lunch = 876. The meal targets add up to the daily target.
4. **Foods you have** + **"Use ONLY these foods"**: type foods like `rice, dal, paneer, roti`.
   With strict mode ON every meal, replacement and regenerated plan uses only those foods
   (if they pass your diet/allergy filters).
5. **Maximum dishes per meal** (1-4) and **history period** (10 or 15 days).
6. Press **Generate**. Each meal card shows dishes, grams, kcal per dish, meal kcal, protein, carbs, fat,
   fibre, the target, the coverage % and the remaining/excess kcal.
7. **Replace Breakfast / Lunch / Dinner** changes only that meal (the other two stay exactly the same).

"Planned" values are what the plan contains. They are **not** food that was actually eaten.

Typed-food notes: `paneer` is not in USDA SR Legacy, so whole-milk mozzarella is used as a clearly
labelled approximate proxy. Foods that do not exist in the dataset (for example `dosa`, `idli`,
`paratha`) are reported as "not found" and are never replaced by something else.

---

## 3. How the algorithm works (viva-friendly)

| Stage | What happens | File |
|---|---|---|
| A. Eligibility & safety | Diet, allergies, restrictions first. Strict mode keeps only typed foods that survive the filters. | `safety_filter.py`, `recommendation_engine.py`, `available_foods.py` |
| B. Candidate generation | Every combination of 1..N distinct foods (N = dish limit). A bigger portion is not a new dish. | `meal_planner.py` |
| C. Portion solving + evaluation | For each combination, gram portions are solved by **bounded least squares** (calories weighted most), rounded to 5 g, refined to 1 g for the finalists. Complete meal nutrition is computed from per-100 g values. | `meal_planner.py` |
| D. Ranking | Score of the *complete meal*: calorie gap first, then protein/carbs/fat/fibre fit, realistic portions, sensible composition, simplicity, likes/dislikes, recent history. Cosine similarity is only a small tie-breaker. | `meal_planner.py` |
| E. Verification | The chosen meal is recalculated from the original USDA CSV and compared. | `verify_meal_plan()` |

Realistic portion limits are in `PORTION_RULES` at the top of `meal_planner.py`
(minimum grams, maximum grams, maximum kcal one dish may give). Change them there.

Calorie coverage = planned kcal / target kcal x 100. It is never capped or faked. When the
foods cannot reach the target (dish limit, available foods, portion limits) the best valid meal is
shown with the real numbers and a plain explanation.

**Broad mode** (no foods typed): a short list of everyday USDA foods is used (about 60 entries,
from `CURATED_FOODS` in `available_foods.py`), not all 7,400 USDA entries, because ranking every entry
by nutrient similarity gives odd foods (for example chicken feet).

**History**: plans are saved per profile in SQLite. When you generate again, meals equal or similar to your
recent ones (10 or 15 days) get a small, capped penalty. It can never beat safety, available-food mode,
the dish limit or a clearly better calorie fit, and foods may be reused when needed.
Plans do **not** change automatically each day; variety applies when you generate a new plan.

---

## 4. What was wrong and what was fixed (root causes)

| Problem | Root cause found in the uploaded code | Fix |
|---|---|---|
| `NameError: name 'user_profile' is not defined` on Replace buttons | `user_profile` was created only inside `if generate:`. Clicking Replace reruns the script with `generate = False`, and the results block read `user_profile["recent_foods"]` (old `app.py` line ~1767). | The profile, targets, result and food pool are stored in `st.session_state`; the profile is created before history is loaded; nothing reads an undefined variable. |
| Meals far below target (e.g. 430 vs 1000 kcal) | Portions came from a fixed grid (50-300 g, only 5 sampled values per food) and candidates were ranked mainly by nutrient/composition scores, with no strong preference for reaching the calorie target. | New solver + scoring described above; calorie gap dominates the rank; shortfalls are explained. |
| Percentages looked better than reality | Meal card bar and percent were capped at 100%; the Target-vs-Planned panel received dictionaries without the keys it read, so it showed nothing; meal targets were rounded separately so they did not add up to the daily target. | Real coverage is shown (can exceed 100%); unified `compare_with_targets`; meal targets are unrounded and always sum to the daily target; rounding is display-only. |
| Typed foods not found (`paneer`, `roti`, `bread`, `cheese`, `oats`) | Matching excluded words such as bread/cheese/cereal even when the user typed them; no aliases for roti/paneer; raw dry entries were picked. | Curated cooked-form matches, aliases, labelled proxy for paneer, exclusion words lifted for words the user typed, duplicates collapsed. |
| Available-food list could be truncated or bypassed | Candidate pool went through `top_k` and diversity rules; replacement could fall back to "same foods, different portions". | Strict mode returns every matched food and nothing else; replacement only accepts a genuinely different food combination. |
| Replace could add nothing useful | Replace regenerated from the top-30 pool, saved a new history row on every click, and did not report why it failed. | Replace changes one meal, recalculates everything, updates the same history row, and gives a message when no alternative exists. |
| History penalty had no effect | In `recommendation_engine.py` the recent-food penalty was applied after the final score was computed. | Applied before the final score, plus a meal-level history penalty in the planner. |
| History mixed / path problems | Database path was relative to the working directory; one global history for all. | Path relative to the project; per-profile rows and settings; `NUTRIGUIDE_DB` override for tests. |
| Vegetarian users could get eggs | The dataset flags eggs as `is_vegetarian`, and "eggetarian" also accepted any food containing egg (even with meat). | Vegetarian now also excludes egg; eggetarian = vegetarian-flagged foods. |
| Machine-specific virtual environment in the ZIP | `venv` pointed to another user's `C:\Users\...` Python. | `venv` removed; create your own (section 1). |

### Files changed / added

Changed: `app.py`, `meal_planner.py`, `meal_recommendation.py`, `recommendation_engine.py`,
`available_foods.py`, `history_store.py`, `nutrition_targets.py`, `user_profile.py`, `requirements.txt`.
Added: `food_labels.py`, `evaluate.py`, `tests/`, `.streamlit/config.toml`, `.gitignore`, `README.md`, `TEST_RESULTS.md`.
Unchanged: `preprocess.py`, `food_constraints.py`, `feature_engineering.py`, `safety_filter.py`,
`safety_refinement.py`, `eda.py`, `inspect_dataset.py`.

---

## 5. Calorie accuracy: old code vs new code (measured)

`evaluate.py` creates random profiles (fixed seed 2026: age 18-60, both genders, different activity,
goals and diets), builds a plan for each, and compares each meal's planned kcal with its target
(25% / 40% / 35% of the daily target). I ran the **same script on the original uploaded code and on
the new code**, 12 profiles x 3 meals = 36 meals per row:

| Mode | Code | Mean error | Median error | Meals within 5% of target |
|---|---|---|---|---|
| Common foods (no list typed) | original | 16.4% | 17.6% | 25.0% |
| Common foods (no list typed) | **new** | **0.1%** | **0.1%** | **100%** |
| 8 typed foods (rice, dal, chicken, egg, oats, milk, potato, banana) | original | 6.7% | 5.0% | 52.8% |
| 8 typed foods (rice, dal, chicken, egg, oats, milk, potato, banana) | **new** | **1.1%** | **0.2%** | **94.4%** |

Run it yourself (about a minute): `python evaluate.py --profiles 12`.
Caveats: only 12 profiles, calories only (not macros), the new planner is limited to 3 dishes per
meal in this test, and "error" is measured against the same meal targets for both versions.
Results will differ a little with other seeds or foods; small targets or few foods can still fall short
(the app then explains why).

## 6. Small features added in this version

- **Household measures** under each dish, for example "about 5 roti" or "about 1.5 katori"
  (approximate standard sizes, display only; all calculations use grams).
- **Download this plan (CSV)** button.
- **Calorie split bars**: target vs planned share of protein / carbs / fat.
- **Always-light input boxes** in the sidebar (`.streamlit/config.toml` forces the light theme).

---

## 7. Limitations (please read before the viva)

- **Allergen safety is not guaranteed.** USDA SR Legacy has no complete allergen data. Filters work from
  food categories and keywords in `final_food_constraints.csv`. Do not present this as medical advice.
- Gluten-free and nut-related filters are deliberately conservative (whole categories can be removed).
- Portion rules are reasonable defaults, not clinical guidance. Gram weights follow the USDA entry
  (mostly cooked weight).
- Dal, roti, rice etc. are USDA approximations of home-cooked food; paneer is a proxy.
- Meal targets of 25/40/35% and macro targets (1.2 g/kg protein, 30% fat) are simple project rules.
- Very low custom targets (a few hundred kcal) can conflict with the minimum portion of some foods; the
  planner then shows the closest valid meal and says so.
- Profiles are local nicknames, **not authentication**. Anyone using the computer can open any profile.
- The app has been tested headlessly (see `TEST_RESULTS.md`); it was not clicked through in a real browser by the author of this fix.
