import pandas as pd
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import joblib

INPUT_FILE = Path("data/processed/nutrition_data.csv")

OUTPUT_DIR = Path("data/processed")

OUTPUT_FILE = OUTPUT_DIR / "food_features.csv"

SCALER_FILE = OUTPUT_DIR / "nutrition_scaler.pkl"

data = pd.read_csv(INPUT_FILE)

print("=" * 50)
print("FEATURE ENGINEERING + NORMALIZATION")
print("=" * 50)

print("\nOriginal Shape:")
print(data.shape)

feature_columns = [
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g"
]

features = data[feature_columns].copy()

print("\nSelected Nutrition Features:")
print(feature_columns)

print("\nBefore Normalization:")
print(features.describe().round(2))

scaler = MinMaxScaler()

normalized_features = scaler.fit_transform(features)

normalized = pd.DataFrame(
    normalized_features,
    columns=[
        "calories_norm",
        "protein_norm",
        "carbs_norm",
        "fat_norm",
        "fiber_norm"
    ]
)

result = pd.concat(
    [
        data[["fdc_id", "food_name"]],
        normalized
    ],
    axis=1
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

result.to_csv(
    OUTPUT_FILE,
    index=False
)

joblib.dump(
    scaler,
    SCALER_FILE
)

print("\nAfter Normalization:")
print(
    result[
        [
            "calories_norm",
            "protein_norm",
            "carbs_norm",
            "fat_norm",
            "fiber_norm"
        ]
    ].describe().round(3)
)

print("\nFeature Range Check:")

for column in normalized.columns:
    print(
        f"{column}: "
        f"min={normalized[column].min():.3f}, "
        f"max={normalized[column].max():.3f}"
    )

print("\nFeature Engineering completed successfully.")

print("Foods:", len(result))
print("Features:", len(normalized.columns))
print("Food Features:", OUTPUT_FILE)
print("Scaler:", SCALER_FILE)

print("\nSample:")
print(
    result.head(10).to_string(index=False)
)