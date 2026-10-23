# NutriGuide AI

**An AI-based personalized nutrition recommendation system using health analytics.**

NutriGuide AI builds a daily Breakfast / Lunch / Dinner plan from your health profile, your diet
and allergy settings, and the foods you actually have at home. Each meal is searched and portioned
so that its real calories come as close as possible to the target, for example a 876 kcal lunch
made only from rice, dal, paneer and roti.

[**Open the live app**](https://nutriguide-ai-5.streamlit.app)

> Educational project. Not medical advice. See [Limitations](#limitations).

---

## Features

- **Calorie-target matching** - set calories automatically, per day, or per meal. The planner searches
  food combinations and gram portions and reports the real planned kcal, coverage and any gap.
- **Use only the foods you have** - strict pantry mode never adds a food you did not list.
- **Dish limit** - choose 1 to 4 dishes per meal. A larger portion is not counted as a new dish.
- **Safety filters** - diet (vegetarian, vegan, eggetarian, non-vegetarian), supported allergies and
  restrictions are applied before any ranking.
- **Replace one meal** - Breakfast, Lunch or Dinner can be replaced on its own; the other two stay unchanged.
- **Profiles and history** - separate settings and meal history per profile (SQLite), with a 10 or 15 day
  window that encourages variety when you generate a new plan.
- **Readable output** - clean dish names, grams, household measures (for example "about 2 roti"),
  macros, fibre, target-versus-planned table and a CSV download.

## How it works

| Stage | What happens |
|---|---|
| 1. Targets | BMI, BMR and TDEE (Mifflin-St Jeor) give daily calories and macros; meal targets are 25% / 40% / 35% unless you set your own. |
| 2. Eligibility | Diet, allergies and restrictions remove foods first. In pantry mode only the foods you typed remain. |
| 3. Candidates | Every combination of up to N distinct foods is generated. |
| 4. Portions | Gram portions per combination are solved with bounded least squares (calories weighted most), rounded to practical grams, within realistic per-food limits. |
| 5. Ranking | The complete meal is scored: calorie gap, protein / carbs / fat / fibre fit, portion realism, meal composition, simplicity, preferences and recent history. Content-based (cosine) similarity is a small tie-breaker. |
| 6. Verification | The chosen meal is recalculated from the original USDA CSV and compared. |

Coverage is always `planned kcal / target kcal x 100`. It is never capped or adjusted. When the
selected foods, dish limit or portion limits cannot reach the target, the best valid meal is shown
together with the reason.

**Tech stack:** Python, Pandas, NumPy, SciPy, scikit-learn, Streamlit, SQLite.
**Data:** USDA FoodData Central, SR Legacy (April 2018).

---

## Run it locally

Requires Python 3.10 or newer.

**Windows (PowerShell)**

```powershell
git clone https://github.com/shahan-hash/nutriguide-ai.git
cd nutriguide-ai
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` once and activate again.

**macOS / Linux**

```bash
git clone https://github.com/shahan-hash/nutriguide-ai.git
cd nutriguide-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. No raw data download is needed: the processed files are
included in `data/processed/`.

### Quick start in the app

1. Create a profile in the sidebar and enter your details.
2. Leave **Calorie target** on *Auto*, or choose a custom daily or per-meal target.
3. Optionally type the foods you have (for example `rice, dal, paneer, roti`) and keep
   **Use ONLY these foods** ticked.
4. Choose the maximum dishes per meal and the history period, then press **Generate My Meal Plan**.

Typed foods are matched to USDA entries (cooked forms where relevant). Paneer is not in USDA SR Legacy,
so whole-milk mozzarella is used as a clearly labelled approximate proxy. Foods missing from the dataset
(for example dosa or idli) are reported as not found and are never silently replaced.

---

## Project structure

```
app.py                     Streamlit app (UI, profiles, replace buttons)
meal_planner.py            Combination search, portion solver, ranking, verification, replacement
recommendation_engine.py   Safety filtering and content-based scoring
available_foods.py         Matching typed foods to USDA entries
meal_recommendation.py     Connects the recommender and the planner
nutrition_targets.py       BMR / TDEE, calorie and macro targets
history_store.py           SQLite profiles and per-profile history
food_labels.py             Readable names and household measures (display only)
user_profile.py            Profile dictionary
evaluate.py                Calorie-accuracy check on random profiles
preprocess.py, food_constraints.py, safety_refinement.py, feature_engineering.py
                           Data preparation pipeline (see below)
tests/                     Automated tests
data/processed/            Processed USDA data used by the app
.streamlit/config.toml     Light theme
```

## Data

`data/processed/` contains everything the app needs (`nutrition_data.csv`, `final_food_constraints.csv`,
`food_features.csv`, `nutrition_scaler.pkl`).

The raw USDA download (`data/raw/`) is **not** included in this repository because of file-size limits
and it is not needed to run the app. To rebuild the processed files:

1. Download **FoodData Central, SR Legacy (April 2018), CSV** from <https://fdc.nal.usda.gov/download-datasets>.
2. Extract it to `data/raw/FoodData_Central_sr_legacy_food_csv_2018-04/`.
3. From the project folder run, in this order:

```bash
python preprocess.py
python food_constraints.py
python safety_refinement.py
python feature_engineering.py
```

(`eda.py` additionally needs `pip install matplotlib` and writes plots to `data/processed/eda_plots/`.)

## Tests and evaluation

```bash
python -m unittest discover -s tests -t . -v
python evaluate.py --profiles 12
```

The tests use the real processed data and a temporary database. `evaluate.py` generates random
profiles (fixed seed) and compares each meal's planned kcal with its target. On 12 profiles x 3 meals
the mean calorie error was 0.1% with common foods and 1.1% with a typed list of 8 foods
(94% of meals within 5% of target). This is a small, calories-only check, not a clinical validation.
Details are in [TEST_RESULTS.md](TEST_RESULTS.md).

## Deploying your own copy (Streamlit Community Cloud)

1. Fork this repository.
2. Sign in at <https://share.streamlit.io> with GitHub and choose **Create app**.
3. Select your fork, branch `main`, main file `app.py`, and deploy.

In the hosted demo each visitor's profile and history are private to their browser session and are not
kept after the page is closed or refreshed.

## Limitations

- **Allergen safety is not guaranteed.** USDA SR Legacy has no complete allergen data. Filters use food
  categories and keywords, and the gluten-free and nut filters are deliberately conservative.
- Nutrition values and portions are estimates for education and demonstration, not dietary or medical advice.
  Consult a qualified professional for health conditions.
- Dal, roti, rice and similar foods are USDA approximations of home-cooked food; paneer is a proxy.
- Targets (25/40/35 meal split, 1.2 g/kg protein, 30% fat) are simple project rules.
- Profiles are local nicknames, not authentication.
- "Planned" values describe the generated plan, not food actually eaten.

## Author

Built by [shahan-hash](https://github.com/shahan-hash) as a B.Tech project.
