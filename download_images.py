import json
import os
import re
import requests  # type: ignore
from concurrent.futures import ThreadPoolExecutor, as_completed


# PATHS & CONFIGURATION
DATA_DIR = "data"
INPUT_PATH = os.path.join(DATA_DIR, "recipes_clean.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "recipes_images.json")
IMAGES_DIR = os.path.join(DATA_DIR, "images", "images")

MAX_WORKERS = 8
TIMEOUT = 10


def slugify(text, max_len=60):
    """Turns a recipe title into a filesystem-safe slug for the image filename."""
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:max_len] if text else "recipe"


# PER-RECIPE DOWNLOAD WORKER
def download_one(recipe):
    urls = recipe.get("image_urls", [])
    filename = f'{recipe["id"]}-{slugify(recipe["title"])}.jpg'
    filepath = os.path.join(IMAGES_DIR, filename)

    if os.path.exists(filepath):
        recipe["image_filename"] = filename
        return recipe

    if not urls:
        recipe["image_filename"] = None
        return recipe

    for url in urls:
        try:
            resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200 and resp.content:
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                recipe["image_filename"] = filename
                return recipe
        except requests.RequestException:
            # This particular URL failed (dead link, timeout, etc.) - try the next one.
            continue

    # None of the candidate URLs worked.
    recipe["image_filename"] = None
    return recipe


# MAIN: PARALLEL DOWNLOAD PIPELINE
def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    print(f"Downloading images for {len(recipes)} recipes with {MAX_WORKERS} parallel workers...")
    print("(already-downloaded images are skipped automatically)")

    results = []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_one, r) for r in recipes]
        for future in as_completed(futures):
            results.append(future.result())
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(recipes)} processed...")

    with_image = sum(1 for r in results if r.get("image_filename"))
    print(f"Done. {with_image}/{len(results)} recipes now have a local image "
          f"({len(results) - with_image} had dead/missing links).")

    for r in results:
        r.pop("image_urls", None)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    print(f"Saved final dataset -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()