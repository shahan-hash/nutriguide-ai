import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

NUTRITION_FILE = Path("data/processed/nutrition_data.csv")
CONSTRAINT_FILE = Path("data/processed/final_food_constraints.csv")
OUTPUT_DIR = Path("data/processed/eda_plots")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

nutrition = pd.read_csv(NUTRITION_FILE)
constraints = pd.read_csv(CONSTRAINT_FILE)

data = nutrition.merge(
    constraints[["fdc_id", "category"]],
    on="fdc_id",
    how="inner"
)

print("=" * 50)
print("EXPLORATORY DATA ANALYSIS")
print("=" * 50)

print("\nDataset Shape:")
print(data.shape)

print("\nColumns:")
print(data.columns.tolist())

print("\nMissing Values:")
print(data.isnull().sum())

print("\nNutritional Statistics:")
print(
    data[
        [
            "calories",
            "protein_g",
            "carbs_g",
            "fat_g",
            "fiber_g"
        ]
    ].describe().round(2)
)

print("\nFood Categories:")
print(
    data["category"]
    .value_counts()
    .to_string()
)

print("\nTop 10 Protein-Rich Foods:")
print(
    data.nlargest(10, "protein_g")[
        ["food_name", "protein_g"]
    ].to_string(index=False)
)

print("\nTop 10 Fiber-Rich Foods:")
print(
    data.nlargest(10, "fiber_g")[
        ["food_name", "fiber_g"]
    ].to_string(index=False)
)

print("\nTop 10 Calorie-Dense Foods:")
print(
    data.nlargest(10, "calories")[
        ["food_name", "calories"]
    ].to_string(index=False)
)


# 1. Calories Distribution
plt.figure(figsize=(10, 6))
plt.hist(data["calories"], bins=50)
plt.title("Distribution of Calories")
plt.xlabel("Calories per 100g")
plt.ylabel("Number of Foods")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "calorie_distribution.png")
plt.close()


# 2. Protein Distribution
plt.figure(figsize=(10, 6))
plt.hist(data["protein_g"], bins=50)
plt.title("Distribution of Protein")
plt.xlabel("Protein (g) per 100g")
plt.ylabel("Number of Foods")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "protein_distribution.png")
plt.close()


# 3. Carbohydrate Distribution
plt.figure(figsize=(10, 6))
plt.hist(data["carbs_g"], bins=50)
plt.title("Distribution of Carbohydrates")
plt.xlabel("Carbohydrates (g) per 100g")
plt.ylabel("Number of Foods")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "carbohydrate_distribution.png")
plt.close()


# 4. Fat Distribution
plt.figure(figsize=(10, 6))
plt.hist(data["fat_g"], bins=50)
plt.title("Distribution of Fat")
plt.xlabel("Fat (g) per 100g")
plt.ylabel("Number of Foods")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "fat_distribution.png")
plt.close()


# 5. Fiber Distribution
plt.figure(figsize=(10, 6))
plt.hist(data["fiber_g"], bins=50)
plt.title("Distribution of Fiber")
plt.xlabel("Fiber (g) per 100g")
plt.ylabel("Number of Foods")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "fiber_distribution.png")
plt.close()


# 6. Food Category Distribution
category_counts = data["category"].value_counts()

plt.figure(figsize=(12, 8))
category_counts.plot(kind="bar")
plt.title("Food Category Distribution")
plt.xlabel("Food Category")
plt.ylabel("Number of Foods")
plt.xticks(rotation=75, ha="right")
plt.tight_layout()
plt.savefig(OUTPUT_DIR / "category_distribution.png")
plt.close()


print("\nEDA completed successfully.")

print("\nPlots saved in:")
print(OUTPUT_DIR)

print("\nGenerated plots:")
for file in OUTPUT_DIR.glob("*.png"):
    print("-", file.name)