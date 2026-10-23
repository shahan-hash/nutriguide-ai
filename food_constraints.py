import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/FoodData_Central_sr_legacy_food_csv_2018-04")
OUTPUT_FILE = Path("data/processed/food_constraints.csv")

food = pd.read_csv(
    DATA_DIR / "food.csv",
    usecols=["fdc_id", "description", "food_category_id"]
)

categories = pd.read_csv(
    DATA_DIR / "food_category.csv",
    usecols=["id", "description"]
)

categories = categories.rename(
    columns={"id": "food_category_id", "description": "category"}
)

data = food.merge(
    categories,
    on="food_category_id",
    how="left"
)

data = data.rename(
    columns={"description": "food_name"}
)

data["food_name_lower"] = (
    data["food_name"]
    .astype(str)
    .str.lower()
)

data["category_lower"] = (
    data["category"]
    .astype(str)
    .str.lower()
)

animal_categories = [
    "beef products",
    "pork products",
    "poultry products",
    "finfish and shellfish products",
    "lamb, veal, and game products",
    "sausages and luncheon meats"
]

data["is_animal_food"] = data["category_lower"].isin(
    animal_categories
)

data["is_vegetarian"] = ~data["is_animal_food"]

vegan_exclude_categories = [
    "dairy and egg products"
]

data["is_vegan"] = (
    data["is_vegetarian"] &
    ~data["category_lower"].isin(vegan_exclude_categories)
)

data["contains_dairy"] = (
    data["category_lower"] == "dairy and egg products"
)

data["contains_egg"] = (
    data["category_lower"] == "dairy and egg products"
)

data["contains_nuts"] = (
    data["category_lower"] == "nut and seed products"
)

data["contains_fish"] = (
    data["category_lower"] == "finfish and shellfish products"
)

data["contains_shellfish"] = (
    data["food_name_lower"].str.contains(
        "shrimp|prawn|crab|lobster|shellfish|clam|oyster|mussel|scallop",
        regex=True,
        na=False
    )
)

data["contains_alcohol"] = (
    data["category_lower"] == "alcoholic beverages"
)

exclude_categories = [
    "baby foods",
    "quality control materials",
    "alcoholic beverages"
]

data = data[
    ~data["category_lower"].isin(exclude_categories)
]

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

print("Food constraint mapping completed.")
print("Foods:", len(data))
print("Output:", OUTPUT_FILE)

print("\nDiet distribution:")
print("Vegetarian:", data["is_vegetarian"].sum())
print("Vegan:", data["is_vegan"].sum())

print("\nConstraint columns:")
print(data.columns.tolist())

print("\nSample:")
print(data.head(10).to_string(index=False))