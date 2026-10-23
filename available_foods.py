"""Match the foods a user types (rice, dal, paneer, roti ...) to USDA rows.

Rules (strict, on purpose):
* ONE USDA row is chosen for each food the user types.
* Only those rows are ever used for meals when "available foods only" is ON.
* Words such as "bread" or "cheese" are normally excluded from matching
  (they pull in snacks / fast food), but NOT when the user typed that word.
* Foods that do not exist in USDA SR Legacy (for example paneer) can use a
  clearly labelled closest-match proxy.  The proxy is shown in the app.
"""
import re
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

NUTRITION_FILE = BASE_DIR / "data" / "processed" / "nutrition_data.csv"


ALIASES = {
    # pulses
    "dal": ["lentil", "lentils"],
    "daal": ["lentil", "lentils"],
    "lentil": ["lentil", "lentils"],
    "lentils": ["lentil", "lentils"],
    "masoor": ["lentil", "lentils"],
    "pulses": ["lentil", "lentils"],
    "chana": ["chickpea", "chickpeas", "garbanzo"],
    "chole": ["chickpea", "chickpeas", "garbanzo"],
    "chickpeas": ["chickpea", "chickpeas", "garbanzo"],
    "rajma": ["kidney"],
    "kidney beans": ["kidney"],
    # grains / breads
    "rice": ["rice"],
    "roti": ["roti", "chapati"],
    "chapati": ["roti", "chapati"],
    "chapatti": ["roti", "chapati"],
    "phulka": ["roti", "chapati"],
    "naan": ["naan"],
    "bread": ["bread"],
    "oats": ["oat", "oats"],
    "oatmeal": ["oat", "oats"],
    "pasta": ["pasta", "spaghetti", "macaroni"],
    # protein
    "chicken": ["chicken"],
    "egg": ["egg", "eggs"],
    "eggs": ["egg", "eggs"],
    "tofu": ["tofu"],
    "paneer": ["paneer"],
    "fish": ["fish"],
    # dairy
    "curd": ["yogurt", "yoghurt", "curd"],
    "dahi": ["yogurt", "yoghurt", "curd"],
    "yogurt": ["yogurt", "yoghurt", "curd"],
    "milk": ["milk"],
    # fruit / veg
    "banana": ["banana", "bananas"],
    "apple": ["apple", "apples"],
    "potato": ["potato", "potatoes"],
    "aloo": ["potato", "potatoes"],
    "palak": ["spinach"],
    "gobi": ["cauliflower"],
    "bhindi": ["okra"],
    "matar": ["peas"],
    "baingan": ["eggplant"],
    "gajar": ["carrot", "carrots"],
    "tamatar": ["tomato", "tomatoes"],
    "pyaz": ["onion", "onions"],
}


# Exclusion words that must NOT be applied for these typed foods.
ALLOW_EXTRA = {
    "roti": ["bread"],
    "chapati": ["bread"],
    "chapatti": ["bread"],
    "phulka": ["bread"],
    "naan": ["bread"],
    "oats": ["cereal"],
    "oatmeal": ["cereal"],
}

# Typed foods where the COOKED USDA entry is the realistic plate portion.
COOKED_PREFERRED = {
    "rice", "dal", "daal", "lentil", "lentils", "masoor", "pulses", "chana",
    "chole", "chickpeas", "rajma", "kidney beans", "oats", "oatmeal", "pasta",
    "potato", "aloo", "chicken", "fish",
}



# Best USDA representative (exact description) for common typed foods.
# Cooked / plain forms are used because meal portions are weighed as eaten.
_COOKED_VEG = "{}, cooked, boiled, drained, without salt"
CURATED_FOODS = {
    "rice": "Rice, white, long-grain, regular, enriched, cooked",
    "white rice": "Rice, white, long-grain, regular, enriched, cooked",
    "brown rice": "Rice, brown, long-grain, cooked (Includes foods for USDA's Food Distribution Program)",
    "dal": "Lentils, mature seeds, cooked, boiled, without salt",
    "daal": "Lentils, mature seeds, cooked, boiled, without salt",
    "lentil": "Lentils, mature seeds, cooked, boiled, without salt",
    "lentils": "Lentils, mature seeds, cooked, boiled, without salt",
    "masoor": "Lentils, mature seeds, cooked, boiled, without salt",
    "pulses": "Lentils, mature seeds, cooked, boiled, without salt",
    "chana": "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt",
    "chole": "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt",
    "chickpeas": "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt",
    "rajma": "Beans, kidney, all types, mature seeds, cooked, boiled, without salt",
    "kidney beans": "Beans, kidney, all types, mature seeds, cooked, boiled, without salt",
    "roti": "Bread, chapati or roti, plain, commercially prepared",
    "chapati": "Bread, chapati or roti, plain, commercially prepared",
    "chapatti": "Bread, chapati or roti, plain, commercially prepared",
    "phulka": "Bread, chapati or roti, plain, commercially prepared",
    "naan": "Bread, naan, plain, commercially prepared, refrigerated",
    "bread": "Bread, whole-wheat, commercially prepared",
    "oats": "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt",
    "oatmeal": "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt",
    "pasta": "Pasta, cooked, enriched, without added salt",
    "spaghetti": "Pasta, cooked, enriched, without added salt",
    "quinoa": "Quinoa, cooked",
    "egg": "Egg, whole, cooked, hard-boiled",
    "eggs": "Egg, whole, cooked, hard-boiled",
    "chicken": "Chicken, broilers or fryers, breast, meat only, cooked, roasted",
    "fish": "Fish, cod, Atlantic, cooked, dry heat",
    "salmon": "Fish, salmon, Atlantic, farmed, cooked, dry heat",
    "pork": "Pork, fresh, loin, whole, separable lean only, cooked, roasted",
    "tofu": "Tofu, raw, firm, prepared with calcium sulfate",
    "milk": "Milk, whole, 3.25% milkfat, with added vitamin D",
    "curd": "Yogurt, plain, whole milk",
    "dahi": "Yogurt, plain, whole milk",
    "yogurt": "Yogurt, plain, whole milk",
    "potato": "Potatoes, boiled, cooked in skin, flesh, without salt",
    "aloo": "Potatoes, boiled, cooked in skin, flesh, without salt",
    "sweet potato": "Sweet potato, cooked, baked in skin, flesh, without salt",
    "banana": "Bananas, raw",
    "apple": "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)",
    "mango": "Mangos, raw",
    "orange": "Oranges, raw, all commercial varieties",
    "palak": _COOKED_VEG.format("Spinach"),
    "spinach": _COOKED_VEG.format("Spinach"),
    "gobi": _COOKED_VEG.format("Cauliflower"),
    "cauliflower": _COOKED_VEG.format("Cauliflower"),
    "bhindi": _COOKED_VEG.format("Okra"),
    "okra": _COOKED_VEG.format("Okra"),
    "matar": _COOKED_VEG.format("Peas, green"),
    "peas": _COOKED_VEG.format("Peas, green"),
    "baingan": _COOKED_VEG.format("Eggplant"),
    "brinjal": _COOKED_VEG.format("Eggplant"),
    "gajar": _COOKED_VEG.format("Carrots"),
    "carrot": _COOKED_VEG.format("Carrots"),
    "carrots": _COOKED_VEG.format("Carrots"),
    "broccoli": _COOKED_VEG.format("Broccoli"),
    "cabbage": _COOKED_VEG.format("Cabbage"),
    "tamatar": "Tomatoes, red, ripe, raw, year round average",
    "tomato": "Tomatoes, red, ripe, raw, year round average",
    "pyaz": "Onions, raw",
    "onion": "Onions, raw",
    "cucumber": "Cucumber, with peel, raw",
    "almonds": "Nuts, almonds",
    "peanuts": "Peanuts, all types, raw",
}

# Foods that are NOT in USDA SR Legacy: exact USDA description used as proxy.
PROXY_FOODS = {
    "paneer": (
        "Cheese, mozzarella, whole milk",
        "Paneer is not in USDA SR Legacy. Closest proxy used: whole-milk "
        "mozzarella (similar protein and fat). Values are approximate.",
    ),
}


EXCLUDE_WORDS = [
    "baby",
    "alcohol",
    "alcoholic",
    "restaurant",
    "applebee",
    "burger king",
    "mcdonald",
    "pizza hut",
    "oil",
    "bran",
    "flour",
    "spread",
    "soup",
    "juice",
    "beverage",
    "cracker",
    "chips",
    "sandwich",
    "patty",
    "tender",
    "tenders",
    "strip",
    "strips",
    "fat",
    "meatless",
    "strudel",
    "bread",
    "cake",
    "cookie",
    "pie",
    "muffin",
    "pudding",
    "cereal",
    "dessert",
    "shake",
    "smoothie",
    "cheese",
]


def load_food_data():
    return pd.read_csv(NUTRITION_FILE)


def clean_food_name(name):
    name = str(name).lower().strip()
    name = re.sub(r"[^a-z0-9\s,]", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def get_words(name):
    return set(re.findall(r"\b[a-z]+\b", clean_food_name(name)))


def search_terms(user_food):
    """Terms searched for a typed food (aliases + simple plural handling)."""
    user_food = clean_food_name(user_food)
    terms = list(ALIASES.get(user_food, [user_food]))
    extra = []
    for term in terms:
        if " " in term:
            continue
        if term.endswith("s"):
            extra.append(term[:-1])
        else:
            extra.append(term + "s")
    return list(dict.fromkeys(terms + extra))


def is_excluded(food_name, allowed_words=()):
    """True when a USDA name looks like snack / fast food / ingredient.

    ``allowed_words`` are words the user typed themselves (for example
    "bread" or "cheese"); they are not used as exclusion words.
    """
    name = clean_food_name(food_name)
    words = get_words(name)
    allowed = set(allowed_words)

    for word in EXCLUDE_WORDS:
        if word in allowed:
            continue
        if word in words or word in name:
            return True

    return False


def _term_in_words(term, words):
    parts = term.split()
    return bool(parts) and all(part in words for part in parts)


def get_candidates(user_food, data):

    user_food_clean = clean_food_name(user_food)
    terms = search_terms(user_food_clean)

    typed_words = set(get_words(user_food_clean))
    for term in terms:
        typed_words |= get_words(term)
    typed_words |= set(ALLOW_EXTRA.get(user_food_clean, []))

    candidates = []

    for _, row in data.iterrows():

        food_name = clean_food_name(row["food_name"])

        if is_excluded(food_name, allowed_words=typed_words):
            continue

        words = get_words(food_name)

        if any(_term_in_words(term, words) for term in terms):
            candidates.append(row)

    if not candidates:
        return pd.DataFrame()

    return pd.DataFrame(candidates).drop_duplicates(subset=["fdc_id"])


def score_candidate(user_food, food_name):

    user_food = clean_food_name(user_food)
    name = clean_food_name(food_name)
    words = get_words(name)

    score = 0

    terms = ALIASES.get(
        user_food,
        [user_food]
    )

    if any(term in words for term in terms):
        score += 50

    score += max(
        0,
        25 - len(name) * 0.15
    )

    if "raw" in words:
        score += 20

    if "plain" in words:
        score += 15

    if "whole" in words:
        score += 10

    if user_food == "rice":

        if name.startswith("rice,") or name == "rice":
            score += 80

        if "white" in words:
            score += 20

        if "brown" in words:
            score += 15

        if "wild" in words:
            score -= 100

        if "flour" in words:
            score -= 100

        if "fried" in words:
            score -= 40

    elif user_food == "apple":

        if name.startswith("apples,") or name == "apple":
            score += 80

        if "raw" in words:
            score += 30

        if "rose" in words:
            score -= 100

        if "cooked" in words:
            score -= 25

        if "boiled" in words:
            score -= 25

        if "juice" in words:
            score -= 60

        if "pie" in words:
            score -= 60

    elif user_food == "oats":

        if "oats" in words or "oat" in words:
            score += 40

        if "whole" in words:
            score += 25

        if "oil" in words:
            score -= 100

    elif user_food == "milk":

        if "cow" in words:
            score += 40

        if "fluid" in words:
            score += 20

        if "sheep" in words:
            score -= 40

        if "goat" in words:
            score -= 35

        if "soy" in words:
            score -= 25

        if "almond" in words:
            score -= 25

    elif user_food in ["curd", "dahi"]:

        if "yogurt" in words or "yoghurt" in words:
            score += 25

        if "plain" in words:
            score += 30

        if "greek" in words:
            score -= 10

        if "blueberry" in words:
            score -= 50

        if "strawberry" in words:
            score -= 50

        if "vanilla" in words:
            score -= 50

        if "flavored" in words:
            score -= 50

        if "chobani" in words:
            score -= 40

    elif user_food == "chicken":

        if "breast" in words:
            score += 25

        if "meat" in words:
            score += 25

        if "deli" in words:
            score -= 60

        if "rotisserie" in words:
            score -= 40

        if "seasoned" in words:
            score -= 25

        if "fried" in words:
            score -= 25

        if "breaded" in words:
            score -= 40

    elif user_food in ["roti", "chapati", "chapatti", "phulka"]:

        if "chapati" in words or "roti" in words:
            score += 60

        if "plain" in words:
            score += 20

        if "frozen" in words:
            score -= 15

    elif user_food == "bread":

        if name.startswith("bread,"):
            score += 60

        if "whole" in words or "wheat" in words:
            score += 20

        if "toasted" in words or "crumbs" in words or "stuffing" in words:
            score -= 40

    elif user_food in ["chana", "chole", "chickpeas"]:

        if "cooked" in words and "boiled" in words:
            score += 40

        if "canned" in words:
            score -= 20

        if "flour" in words or "hummus" in words:
            score -= 100

    elif user_food in ["rajma", "kidney beans"]:

        if "cooked" in words and "boiled" in words:
            score += 40

        if "canned" in words:
            score -= 20

    elif user_food == "tofu":

        if "raw" in words and "firm" in words:
            score += 30

        if "fried" in words or "dried" in words or "frozen" in words:
            score -= 40

    elif user_food == "egg":

        if "hard" in words and "boiled" in words:
            score += 45

        if "dried" in words or "dehydrated" in words or "powder" in words:
            score -= 80

        if "whole" in words:
            score += 30

        if "raw" in words:
            score += 20

        if "fried" in words:
            score -= 20

        if "omelet" in words:
            score -= 20

    elif user_food == "potato":

        if "raw" in words:
            score += 30

        if "fried" in words:
            score -= 35

        if "chips" in words:
            score -= 60

    elif user_food == "banana":

        if "raw" in words:
            score += 35

        if "juice" in words:
            score -= 50

        if "chips" in words:
            score -= 50

    elif user_food in ["dal", "daal", "pulses"]:

        if "lentils" in words or "lentil" in words:
            score += 35

        if "cooked" in words:
            score += 20

        if "boiled" in words:
            score += 15

        if "soup" in words:
            score -= 30

    # ---- realism adjustments (cooked, plain, common cut) -------------
    if user_food in COOKED_PREFERRED:

        if "cooked" in words or "boiled" in words:
            score += 70

        if "raw" in words or "dry" in words or "uncooked" in words:
            score -= 50

    if user_food == "rice":

        if "glutinous" in words or "instant" in words:
            score -= 40

        if "long" in words and "regular" in words:
            score += 25

    if user_food == "chicken":

        if "breast" in words and "cooked" in words:
            score += 30

        if "roasted" in words:
            score += 10

        if "broilers" in words or "fryers" in words:
            score += 20

        if "stewing" in words:
            score -= 20

        for bad in ["feet", "wing", "wings", "neck", "giblets", "liver",
                    "heart", "gizzard", "back"]:
            if bad in words:
                score -= 60

    if user_food == "milk":

        if "buttermilk" in words or "dried" in words or "dry" in words:
            score -= 80

        if name.startswith("milk, whole"):
            score += 60

    if user_food == "tofu" and ("yogurt" in words or "yoghurt" in words):
        score -= 80

    if user_food == "bread":

        for bad in ["pita", "naan", "chapati", "sprouted"]:
            if bad in words:
                score -= 30

    if user_food in ["tamatar", "tomato", "tomatoes"]:

        if "red" in words and "ripe" in words:
            score += 30

        if "green" in words:
            score -= 20

    if user_food in ["oats", "oatmeal"] and "unenriched" in words:
        score += 10

    if "without" in words and "salt" in words:
        score += 5

    negative_words = [
        "flavored",
        "flavoured",
        "chocolate",
        "blueberry",
        "strawberry",
        "vanilla",
        "sweetened",
        "candy",
        "dessert",
        "restaurant",
        "brand"
    ]

    for word in negative_words:
        if word in words:
            score -= 30

    return score


def find_proxy_match(user_food, data):
    """Return (row, note) for foods that only exist as a labelled proxy."""
    key = clean_food_name(user_food)
    if key not in PROXY_FOODS:
        return None, ""

    usda_name, note = PROXY_FOODS[key]
    rows = data[data["food_name"] == usda_name]

    if rows.empty:
        return None, ""

    return rows.iloc[0].copy(), note


def find_best_match(user_food, data, full_data=None):
    """Best USDA row for one typed food, or None.

    ``data``      : the (safety-filtered) rows that may be used.
    ``full_data`` : optional unfiltered rows.  When a curated food exists
                    there but was removed by a diet / allergy filter, the
                    food is reported as unavailable instead of silently
                    swapping in a different food.
    """

    key = clean_food_name(user_food)

    proxy_row, _ = find_proxy_match(user_food, data)
    if proxy_row is not None:
        proxy_row["match_score"] = 999
        return proxy_row

    if key in PROXY_FOODS:
        return None

    if key in CURATED_FOODS:
        usda_name = CURATED_FOODS[key]
        rows = data[data["food_name"] == usda_name]

        if not rows.empty:
            row = rows.iloc[0].copy()
            row["match_score"] = 1000
            return row

        reference = full_data if full_data is not None else data
        if not reference[reference["food_name"] == usda_name].empty:
            return None  # blocked by diet / allergy filter

    candidates = get_candidates(user_food, data)

    if candidates.empty:
        return None

    candidates = candidates.copy()

    candidates["match_score"] = candidates["food_name"].apply(
        lambda x: score_candidate(user_food, x)
    )

    candidates = candidates.sort_values(
        ["match_score", "food_name"],
        ascending=[False, True],
    )

    return candidates.iloc[0].copy()


def match_available_foods(available_foods, data=None, full_data=None):
    """Return (matched_rows, not_found).

    matched_rows has one row per distinct USDA food, plus the columns
    ``user_food`` (what the user typed), ``match_score`` and ``match_note``.
    """

    if data is None:
        data = load_food_data()

    matches = []
    not_found = []
    used_ids = set()

    for user_food in available_foods or []:

        user_food = str(user_food).strip()

        if not user_food:
            continue

        row = find_best_match(user_food, data, full_data=full_data)

        if row is None:
            not_found.append(user_food)
            continue

        if row["fdc_id"] in used_ids:
            # same USDA food typed twice (for example dal + lentils):
            # keep it once so a meal can never contain it twice.
            continue

        used_ids.add(row["fdc_id"])

        row["user_food"] = user_food
        _, note = find_proxy_match(user_food, data)
        row["match_note"] = note

        matches.append(row)

    if matches:
        matched_data = pd.DataFrame(matches)
    else:
        matched_data = pd.DataFrame(
            columns=list(data.columns) + ["user_food", "match_score", "match_note"]
        )

    return matched_data.reset_index(drop=True), not_found
