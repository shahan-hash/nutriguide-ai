"""Readable food names for the UI.

IMPORTANT: these labels are for DISPLAY only.  Filtering, history, joins and
replacement always use the original USDA ``food_name`` / ``fdc_id``.
"""
import re

# Friendly names for the foods the project matches most often.
KNOWN_LABELS = {
    "Rice, white, long-grain, regular, enriched, cooked": "Cooked White Rice",
    "Rice, brown, long-grain, cooked (Includes foods for USDA's Food Distribution Program)": "Cooked Brown Rice",
    "Lentils, mature seeds, cooked, boiled, without salt": "Cooked Lentils (Dal)",
    "Chickpeas (garbanzo beans, bengal gram), mature seeds, cooked, boiled, without salt": "Cooked Chickpeas (Chana)",
    "Beans, kidney, all types, mature seeds, cooked, boiled, without salt": "Cooked Kidney Beans (Rajma)",
    "Bread, chapati or roti, plain, commercially prepared": "Roti / Chapati",
    "Bread, naan, plain, commercially prepared, refrigerated": "Naan",
    "Bread, whole-wheat, commercially prepared": "Whole-Wheat Bread",
    "Cereals, oats, regular and quick, unenriched, cooked with water (includes boiling and microwaving), without salt": "Cooked Oats (Porridge)",
    "Cereals, oats, regular and quick, not fortified, dry": "Dry Oats",
    "Cereals, corn grits, white, regular and quick, enriched, cooked with water, with salt": "Cooked Corn Grits",
    "Cereals, corn grits, white, regular and quick, enriched, cooked without salt": "Cooked Corn Grits",
    "Egg, whole, cooked, hard-boiled": "Boiled Egg",
    "Chicken, broilers or fryers, breast, meat only, cooked, roasted": "Roasted Chicken Breast",
    "Fish, cod, Atlantic, cooked, dry heat": "Cooked Cod Fish",
    "Fish, salmon, Atlantic, farmed, cooked, dry heat": "Cooked Salmon",
    "Milk, whole, 3.25% milkfat, with added vitamin D": "Whole Milk",
    "Yogurt, plain, whole milk": "Plain Yogurt (Curd)",
    "Tofu, raw, firm, prepared with calcium sulfate": "Firm Tofu",
    "Cheese, mozzarella, whole milk": "Paneer (mozzarella proxy)",
    "Potatoes, boiled, cooked in skin, flesh, without salt": "Boiled Potato",
    "Sweet potato, cooked, baked in skin, flesh, without salt": "Baked Sweet Potato",
    "Bananas, raw": "Banana",
    "Apples, raw, with skin (Includes foods for USDA's Food Distribution Program)": "Apple (with skin)",
    "Pasta, cooked, enriched, without added salt": "Cooked Pasta",
    "Quinoa, cooked": "Cooked Quinoa",
    "Spinach, cooked, boiled, drained, without salt": "Cooked Spinach (Palak)",
    "Cauliflower, cooked, boiled, drained, without salt": "Cooked Cauliflower (Gobi)",
    "Okra, cooked, boiled, drained, without salt": "Cooked Okra (Bhindi)",
    "Peas, green, cooked, boiled, drained, without salt": "Cooked Green Peas (Matar)",
    "Eggplant, cooked, boiled, drained, without salt": "Cooked Eggplant (Baingan)",
    "Carrots, cooked, boiled, drained, without salt": "Cooked Carrots",
    "Broccoli, cooked, boiled, drained, without salt": "Cooked Broccoli",
    "Cabbage, cooked, boiled, drained, without salt": "Cooked Cabbage",
}

_SKIP_TOKENS = {
    "with salt", "without salt", "enriched", "unenriched", "regular", "all types",
    "commercially prepared", "year round average", "drained", "mature seeds",
    "not fortified", "fortified", "includes foods for usda's food distribution program",
    "with added vitamin d", "large or small curd", "prepared with calcium sulfate",
}

_KEEP_TOKENS = {
    "cooked", "raw", "boiled", "roasted", "baked", "grilled", "dry", "whole",
    "plain", "white", "brown", "skim", "lowfat", "low fat", "nonfat", "fresh",
    "breast", "thigh", "meat only", "with skin", "without skin",
}


def readable_food_name(raw_name, user_food=None):
    """Short human-friendly label for a USDA description."""
    name = str(raw_name or "Food").strip()

    if name in KNOWN_LABELS:
        return KNOWN_LABELS[name]

    clean = re.sub(r"\s*\([^)]*\)", "", name)
    parts = [part.strip() for part in clean.split(",") if part.strip()]
    if not parts:
        return name[:60]

    head = parts[0]
    details = []
    for part in parts[1:]:
        low = part.lower()
        if low in _SKIP_TOKENS:
            continue
        if low in _KEEP_TOKENS and low not in details:
            details.append(low)

    label = head[:1].upper() + head[1:]
    if details:
        label += " (" + ", ".join(details[:3]) + ")"

    if user_food:
        typed = str(user_food).strip().lower()
        if typed and typed not in label.lower():
            label += f" [{str(user_food).strip().title()}]"

    return label


def portion_basis(raw_name):
    """Tell the user what the gram weight refers to."""
    name = str(raw_name or "").lower()

    if any(word in name for word in ["cooked", "boiled", "roasted", "baked", "grilled"]):
        return "cooked weight"
    if any(word in name for word in [" dry", "uncooked", "dried"]):
        return "dry weight"
    if "raw" in name:
        return "raw weight"
    return "weight as listed"


def food_meaning(raw_name):
    """One short sentence explaining a confusing USDA term."""
    name = str(raw_name or "").lower()

    if "proxy" in name or "mozzarella" in name:
        return "Paneer is not in USDA data; mozzarella is used as the closest approximate match."
    if "enriched" in name or "fortified" in name:
        return "Enriched/fortified means selected vitamins or minerals were added."
    if "grits" in name:
        return "Grits are a porridge-like food made from ground corn."
    if "lentil" in name:
        return "Lentils are the pulse used to make dal."
    if "chapati" in name or "roti" in name:
        return "Chapati/roti is Indian flatbread (commercially prepared USDA entry)."
    if "oat" in name:
        return "Oats are a whole grain, usually eaten as porridge."
    if "raw" in name:
        return "Raw means the food is listed before cooking."
    if "cooked" in name or "boiled" in name:
        return "This entry describes the food after cooking."
    return ""


# ---------------------------------------------------------------------------
# Household measures (approximate, for readability only - never used in maths)
# (keyword in USDA name, grams per unit, unit word)
# ---------------------------------------------------------------------------
HOUSEHOLD_UNITS = [
    ("chapati", 40, "roti"),
    ("naan", 90, "naan"),
    ("bread, whole-wheat", 30, "slice"),
    ("egg, whole", 50, "egg"),
    ("bananas", 120, "banana"),
    ("apples", 180, "apple"),
    ("milk, whole", 240, "glass"),
    ("yogurt", 150, "katori"),
    ("lentils", 150, "katori"),
    ("chickpeas", 150, "katori"),
    ("beans", 150, "katori"),
    ("rice", 150, "katori"),
    ("oats", 200, "bowl"),
    ("pasta", 150, "katori"),
    ("potatoes", 150, "potato"),
]


def household_measure(raw_name, grams):
    """'about 4 roti' / 'about 1.5 katori' (or '' when no sensible unit)."""
    name = str(raw_name or "").lower()
    try:
        grams = float(grams)
    except (TypeError, ValueError):
        return ""

    for keyword, unit_grams, unit in HOUSEHOLD_UNITS:
        if keyword in name:
            count = round(grams / unit_grams * 2) / 2      # nearest half
            if count <= 0:
                return ""
            number = f"{count:g}"
            plural = "" if count == 1 else ("s" if unit in {"egg", "banana", "apple", "potato", "slice", "glass", "bowl"} else "")
            return f"about {number} {unit}{plural}"
    return ""
