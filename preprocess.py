import pandas as pd
from pathlib import Path

DATA_DIR = Path("data/raw/FoodData_Central_sr_legacy_food_csv_2018-04")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "nutrition_data.csv"

food = pd.read_csv(
    DATA_DIR / "food.csv",
    usecols=["fdc_id", "description"]
)

food_nutrient = pd.read_csv(
    DATA_DIR / "food_nutrient.csv",
    usecols=["fdc_id", "nutrient_id", "amount"]
)

nutrient = pd.read_csv(
    DATA_DIR / "nutrient.csv",
    usecols=["id", "name"]
)

# Use exact USDA nutrient IDs
# 1008 = Energy in kcal
# 1003 = Protein
# 1005 = Carbohydrate
# 1004 = Total lipid (fat)
# 1079 = Fiber

nutrient_map = {
    1008: "calories",
    1003: "protein_g",
    1005: "carbs_g",
    1004: "fat_g",
    1079: "fiber_g"
}

fn = food_nutrient[
    food_nutrient["nutrient_id"].isin(nutrient_map.keys())
].copy()

fn["nutrient_name"] = fn["nutrient_id"].map(nutrient_map)

# If duplicate records exist for the same food/nutrient,
# use the first valid value instead of mixing different energy units.
fn = (
    fn.sort_values(["fdc_id", "nutrient_id"])
    .drop_duplicates(
        subset=["fdc_id", "nutrient_id"],
        keep="first"
    )
)

pivot = fn.pivot(
    index="fdc_id",
    columns="nutrient_name",
    values="amount"
).reset_index()

result = food.merge(
    pivot,
    on="fdc_id",
    how="left"
)

columns = [
    "fdc_id",
    "food_name",
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g"
]

result = result.rename(
    columns={"description": "food_name"}
)

result = result[columns]

# Core nutrients are required
result = result.dropna(
    subset=[
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g"
    ]
)

# Fiber can be missing
result["fiber_g"] = result["fiber_g"].fillna(0)

numeric_columns = [
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g"
]

for column in numeric_columns:
    result[column] = pd.to_numeric(
        result[column],
        errors="coerce"
    )

result = result.dropna(
    subset=numeric_columns
)

# Remove invalid negative nutrition values
result = result[
    (result["calories"] >= 0) &
    (result["protein_g"] >= 0) &
    (result["carbs_g"] >= 0) &
    (result["fat_g"] >= 0) &
    (result["fiber_g"] >= 0)
]

result["food_name"] = (
    result["food_name"]
    .astype(str)
    .str.strip()
)

result = result[
    (result["food_name"] != "") &
    (result["food_name"] != "nan")
]

# Keep one record per food name
result = result.drop_duplicates(
    subset=["food_name"],
    keep="first"
)

result = result.sort_values(
    "food_name"
).reset_index(drop=True)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False
)

print("Preprocessing completed successfully.")
print("Final foods:", len(result))
print("Columns:", list(result.columns))
print("Output:", OUTPUT_FILE)

print("\nFirst 10 foods:")
print(
    result.head(10).to_string(index=False)
)

print("\nEnergy check:")
print(
    result[
        result["food_name"].str.contains(
            "Rice, white, medium-grain, raw",
            case=False,
            na=False
        )
    ][
        [
            "food_name",
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g"
        ]
    ].to_string(index=False)
)