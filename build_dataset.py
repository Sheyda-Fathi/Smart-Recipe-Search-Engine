import pandas as pd
import numpy as np
import json
import re
import os

# PATHS & CONFIGURATION
DATA_DIR = "data"
RECIPES_PATH = os.path.join(DATA_DIR, "recipes.parquet")
OUTPUT_PATH = os.path.join(DATA_DIR, "recipes_clean.json")

# Tunable filters
MIN_REVIEW_COUNT = 3
MAX_RECIPES = 30000


KNOWN_CUISINES = [
    "Mexican", "Chinese", "Italian", "French", "Indian", "Thai", "Japanese",
    "Greek", "Spanish", "German", "Moroccan", "Lebanese", "Turkish",
    "Vietnamese", "Korean", "Caribbean", "Cajun", "Creole", "Cuban",
    "Brazilian", "Argentine", "Peruvian", "Ethiopian", "Nigerian",
    "Egyptian", "Iranian", "Persian", "Russian", "Polish", "Hungarian",
    "Swedish", "Norwegian", "Dutch", "Austrian", "Swiss", "Portuguese",
    "Filipino", "Indonesian", "Malaysian", "Australian", "Canadian",
    "Hawaiian", "Scottish", "Irish", "English", "Welsh", "African",
    "Chilean", "Colombian", "Polynesian", "Scandinavian",
]


# HELPERS
def parse_iso8601_duration_to_minutes(value):
    """Converts strings 'PT1H30M' / 'PT45M' / 'PT2H' = integer minutes."""
    if not isinstance(value, str) or not value.startswith("PT"):
        return None
    hours = re.search(r"(\d+)H", value)
    minutes = re.search(r"(\d+)M", value)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total if total > 0 else None


def to_list(value):
    """Parquet list-columns come back as numpy arrays; normalize to plain lists."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return []


def normalize_fraction_chars(text):
    """Fixes unicode fraction slashes like '1⁄4' -> '1/4' for cleaner display."""
    return text.replace("\u2044", "/") if isinstance(text, str) else text


def extract_cuisine(keywords):
    """Returns the first recognized cuisine found inside a recipe's Keywords list."""
    for kw in keywords:
        if kw in KNOWN_CUISINES:
            return kw
    return None


# MAIN BUILD PIPELINE
def build():
    print("Loading recipes.parquet ...")
    df = pd.read_parquet(RECIPES_PATH)
    print(f"Loaded {len(df)} raw recipes.")

    # --- Quality filter: keep only recipes with real content and proof of use ---
    df = df[df["ReviewCount"].fillna(0) >= MIN_REVIEW_COUNT]
    df = df[df["AggregatedRating"].notna()]
    df = df[df["RecipeIngredientParts"].apply(lambda x: len(to_list(x)) > 0)]
    df = df[df["RecipeInstructions"].apply(lambda x: len(to_list(x)) > 0)]
    df = df[df["Images"].apply(lambda x: len(to_list(x)) > 0)]
    print(f"{len(df)} recipes remain after quality filtering.")

    if MAX_RECIPES:
        df = df.sort_values("ReviewCount", ascending=False).head(MAX_RECIPES)
        print(f"Capped to top {MAX_RECIPES} recipes by review count.")

    records = []
    calories_found = 0
    calories_not_found = 0

    for _, row in df.iterrows():
        # --- Ingredients: two parallel views, exactly as the source provides them ---
        names = [normalize_fraction_chars(str(n)) for n in to_list(row["RecipeIngredientParts"])]
        quantities = [normalize_fraction_chars(str(q)) for q in to_list(row["RecipeIngredientQuantities"])]

        full_ingredients = []
        for i, name in enumerate(names):
            qty = quantities[i] if i < len(quantities) else ""
            qty = "" if qty in ("nan", "None") else qty
            full_ingredients.append(f"{qty} {name}".strip())

        # --- Instructions: turned into a {"1": step, "2": step, ...} dict ---
        instructions_list = [str(s) for s in to_list(row["RecipeInstructions"])]
        instructions = {str(i + 1): step for i, step in enumerate(instructions_list)}

        images = to_list(row["Images"])
        keywords = [str(k) for k in to_list(row["Keywords"])]
        cuisine = extract_cuisine(keywords)
        cook_minutes = (
            parse_iso8601_duration_to_minutes(row.get("TotalTime"))
            or parse_iso8601_duration_to_minutes(row.get("CookTime"))
        )

        date_published = row.get("DatePublished")
        published = date_published.strftime("%B %d, %Y") if pd.notna(date_published) else None

        # unknown calories are stored as None, NOT 0.
        calories = row.get("Calories")
        if calories is not None and not pd.isna(calories) and calories > 0:
            calories_found += 1
            calories_value = float(calories)
        else:
            calories_not_found += 1
            calories_value = None

        records.append({
            "id": int(row["RecipeId"]) if pd.notna(row["RecipeId"]) else None,
            "title": str(row["Name"]),
            "description": "" if pd.isna(row.get("Description")) else str(row["Description"]),
            "ingredients_names": names,
            "ingredients_full": full_ingredients,
            "instructions": instructions,
            "published": published,
            "cooking_time": cook_minutes,
            "servings": None if pd.isna(row.get("RecipeServings")) else row["RecipeServings"],
            "ratings": {
                "rating": float(row["AggregatedRating"]),
                "count": int(row["ReviewCount"]) if pd.notna(row["ReviewCount"]) else 0,
            },
            "tags": {
                "cuisine": [cuisine] if cuisine else [],
                "keywords": keywords,
                "category": None if pd.isna(row.get("RecipeCategory")) else str(row["RecipeCategory"]),
            },
            "image_urls": images,
            "calories": calories_value,
        })

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)

    # --- Summary printout ---
    with_cuisine = sum(1 for r in records if r["tags"]["cuisine"])
    with_calories = sum(1 for r in records if r.get("calories") is not None)

    print(f"\n Saved {len(records)} clean recipes -> {OUTPUT_PATH}")
    print(f"   ({with_cuisine} of them got a recognized cuisine tag)")
    print(f" Calories found: {with_calories} recipes")
    print(f" Calories unknown: {len(records) - with_calories} recipes")

    if with_calories > 0:
        sample_records = [r for r in records if r.get("calories") is not None][:5]
        print("\n Sample calorie values:")
        for r in sample_records:
            print(f" {r['title'][:50]}... -> {r['calories']:.0f} kcal")


if __name__ == "__main__":
    build()