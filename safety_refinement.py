import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/processed/food_constraints.csv")
OUTPUT_FILE = Path("data/processed/final_food_constraints.csv")

data = pd.read_csv(INPUT_FILE)

data["food_name_lower"] = (
    data["food_name"]
    .astype(str)
    .str.lower()
)

animal_keywords = [
    "chicken",
    "beef",
    "pork",
    "ham",
    "bacon",
    "sausage",
    "turkey",
    "duck",
    "lamb",
    "veal",
    "goat",
    "meat",
    "fish",
    "salmon",
    "tuna",
    "shrimp",
    "prawn",
    "crab",
    "lobster",
    "oyster",
    "clam",
    "mussel",
    "scallop"
]

dairy_keywords = [
    "milk",
    "buttermilk",
    "cheese",
    "butter",
    "cream",
    "yogurt",
    "yoghurt",
    "whey",
    "casein",
    "curd"
]

egg_keywords = [
    "egg",
    "eggs",
    "egg white",
    "egg yolk",
    "mayonnaise"
]

nut_keywords = [
    "peanut",
    "peanuts",
    "almond",
    "almonds",
    "walnut",
    "walnuts",
    "cashew",
    "cashews",
    "pistachio",
    "pistachios",
    "pecan",
    "pecans",
    "hazelnut",
    "hazelnuts"
]

def contains_keyword(text, keywords):
    return any(keyword in text for keyword in keywords)


data["keyword_animal"] = data["food_name_lower"].apply(
    lambda x: contains_keyword(x, animal_keywords)
)

data["keyword_dairy"] = data["food_name_lower"].apply(
    lambda x: contains_keyword(x, dairy_keywords)
)

data["keyword_egg"] = data["food_name_lower"].apply(
    lambda x: contains_keyword(x, egg_keywords)
)

data["keyword_nuts"] = data["food_name_lower"].apply(
    lambda x: contains_keyword(x, nut_keywords)
)

data["contains_dairy"] = (
    data["contains_dairy"] |
    data["keyword_dairy"]
)

data["contains_egg"] = (
    data["contains_egg"] |
    data["keyword_egg"]
)

data["contains_nuts"] = (
    data["contains_nuts"] |
    data["keyword_nuts"]
)

data["contains_fish"] = (
    data["contains_fish"] |
    data["food_name_lower"].str.contains(
        "fish|salmon|tuna|cod|trout|sardine|anchovy",
        regex=True,
        na=False
    )
)

data["contains_shellfish"] = (
    data["contains_shellfish"] |
    data["food_name_lower"].str.contains(
        "shrimp|prawn|crab|lobster|oyster|clam|mussel|scallop",
        regex=True,
        na=False
    )
)

data["is_vegetarian"] = (
    data["is_vegetarian"] &
    ~data["keyword_animal"]
)

data["is_vegan"] = (
    data["is_vegan"] &
    ~data["keyword_animal"] &
    ~data["contains_dairy"] &
    ~data["contains_egg"]
)

data["food_name_lower"] = data["food_name_lower"].str.strip()

columns = [
    "fdc_id",
    "food_name",
    "food_category_id",
    "category",
    "is_vegetarian",
    "is_vegan",
    "contains_dairy",
    "contains_egg",
    "contains_nuts",
    "contains_fish",
    "contains_shellfish",
    "contains_alcohol"
]

data = data[columns]

data = data.drop_duplicates(
    subset=["fdc_id"]
)

data.to_csv(
    OUTPUT_FILE,
    index=False
)

print("Safety refinement completed.")
print("Foods:", len(data))
print("Output:", OUTPUT_FILE)

print("\nUpdated diet distribution:")
print("Vegetarian:", data["is_vegetarian"].sum())
print("Vegan:", data["is_vegan"].sum())

print("\nSafety flags:")
print("Dairy:", data["contains_dairy"].sum())
print("Egg:", data["contains_egg"].sum())
print("Nuts:", data["contains_nuts"].sum())
print("Fish:", data["contains_fish"].sum())
print("Shellfish:", data["contains_shellfish"].sum())

print("\nChecking sample foods:")

sample_names = [
    "buttermilk",
    "waffle",
    "chicken",
    "peanut",
    "cheese",
    "egg"
]

for word in sample_names:
    matches = data[
        data["food_name"].str.lower().str.contains(
            word,
            na=False
        )
    ]

    if len(matches) > 0:
        print(f"\n{word.upper()}:")
        print(
            matches[
                ["food_name", "is_vegetarian", "is_vegan",
                 "contains_dairy", "contains_egg", "contains_nuts"]
            ].head(3).to_string(index=False)
        )