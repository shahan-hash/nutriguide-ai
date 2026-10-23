import pandas as pd

DATA_DIR = "data/raw/FoodData_Central_sr_legacy_food_csv_2018-04"

food = pd.read_csv(
    f"{DATA_DIR}/food.csv",
    usecols=["fdc_id", "data_type", "description"]
)

food_nutrient = pd.read_csv(
    f"{DATA_DIR}/food_nutrient.csv",
    usecols=["fdc_id", "nutrient_id", "amount"]
)

nutrient = pd.read_csv(
    f"{DATA_DIR}/nutrient.csv",
    usecols=["id", "name"]
)

required_names = [
    "Energy",
    "Protein",
    "Carbohydrate, by difference",
    "Total lipid (fat)",
    "Fiber, total dietary"
]

required = nutrient[
    nutrient["name"].isin(required_names)
].copy()

print("Required nutrients found:")
print(required.to_string(index=False))

fn = food_nutrient[
    food_nutrient["nutrient_id"].isin(required["id"])
].copy()

pivot = fn.pivot_table(
    index="fdc_id",
    columns="nutrient_id",
    values="amount",
    aggfunc="mean"
)

name_map = dict(zip(required["id"], required["name"]))
pivot = pivot.rename(columns=name_map)

result = food.merge(
    pivot,
    on="fdc_id",
    how="left"
)

features = [name for name in required_names if name in result.columns]

complete = result.dropna(subset=features)

print("\nTotal SR Legacy Foods:", len(result))
print("Foods with all 5 core nutrients:", len(complete))
print("Foods missing at least one core nutrient:", len(result) - len(complete))

print("\nCore nutrient availability:")
print(result[features].notna().sum())

print("\nCore nutrient missing values:")
print(result[features].isna().sum())