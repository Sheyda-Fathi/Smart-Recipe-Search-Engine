import json
import math
import pickle
import re
import os

# PATHS
CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "index.pkl")
DATA_FILE = os.path.join("data", "recipes_images.json")

# STOPWORDS / SYNONYMS
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "in", "on", "at",
    "to", "for", "with", "from", "by", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it",
    "its", "he", "she", "they", "them", "their", "my", "your", "our"
}

QUERY_SYNONYMS = {
    "chicken": ["poultry"],
    "rice": ["grain"],
    "beef": ["meat"],
    "potato": ["potatoes"],
    "tomato": ["tomatoes"],
    "pepper": ["bell", "capsicum"],
    "onion": ["onions"],
    "garlic": ["garlics"],
    "cheese": ["cheddar", "mozzarella"],
    "pasta": ["noodle", "spaghetti"],
}

# Country-name synonyms used only to normalize the display label
NATION_SYNONYMS = {
    "Iranian": ["Persian"],
    "American": ["United States"],
    "British": ["English", "UK"],
}


# TEXT PREPROCESSING PIPELINE
def tokenize(text):
    if not isinstance(text, str):
        return []
    text = text.lower()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    return text.split()


def manual_stem(word):
    if len(word) < 5:
        return word
    suffixes = ["ingly", "edly", "ation", "ment", "ness", "ing", "ed", "ly"]
    for suffix in suffixes:
        if word.endswith(suffix):
            if len(word) > len(suffix) + 2:
                return word[:-len(suffix)]
    return word


def preprocess_document(text):
    tokens = tokenize(text)
    return [manual_stem(t) for t in tokens if t not in STOP_WORDS]


# INDEX BUILDING (TF-IDF)
def load_or_build_index():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)

    os.makedirs(CACHE_DIR, exist_ok=True)

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"Dataset file '{DATA_FILE}' not found!")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw_recipes = json.load(f)

    # Build the clean recipe records
    recipes = []
    for r in raw_recipes:
        title = str(r.get("title", ""))
        description = r.get("description")
        description = "" if not description else str(description)

        ingredients_names = [str(i) for i in r.get("ingredients_names", []) if i is not None]
        ingredients_full = [str(i) for i in r.get("ingredients_full", []) if i is not None]

        # search_text drives similarity: title + ingredient names + steps + keywords.
        search_text = f"{title} {' '.join(ingredients_names)}"

        instructions = r.get("instructions", {})
        if isinstance(instructions, dict):
            for step_desc in instructions.values():
                if isinstance(step_desc, str):
                    search_text += " " + step_desc

        tags = r.get("tags", {})
        if isinstance(tags, dict):
            for tag_list in tags.values():
                if isinstance(tag_list, list):
                    clean_tags = [str(t) for t in tag_list if t is not None]
                    search_text += " " + " ".join(clean_tags)

        recipes.append({
            "title": title,
            "description": description,
            "ingredients_names": ingredients_names,
            "ingredients_full": ingredients_full,
            "instructions": instructions,
            "cooking_time": r.get("cooking_time"),
            "published": r.get("published"),
            "servings": r.get("servings"),
            "ratings": r.get("ratings"),
            "tags": tags,
            "image_filename": r.get("image_filename"),
            "calories": r.get("calories"),
            "search_text": search_text
        })

    # Manual TF-IDF construction
    docs = [preprocess_document(r["search_text"]) for r in recipes]

    N = len(docs)
    doc_freq = {}
    for doc in docs:
        for word in set(doc):
            doc_freq[word] = doc_freq.get(word, 0) + 1

    # Smoothed IDF : log((1+N)/(1+df)) + 1, always >= 1
    idf = {}
    for word, df in doc_freq.items():
        idf[word] = math.log((1 + N) / (1 + df)) + 1

    # TF-IDF vector (dict: term -> weight) per recipe
    tfidf_matrix = []
    for doc in docs:
        total_words = len(doc)
        if total_words == 0:
            tfidf_matrix.append({})
            continue
        word_counts = {}
        for word in doc:
            word_counts[word] = word_counts.get(word, 0) + 1

        vector = {}
        for word, count in word_counts.items():
            tf = count / total_words
            vector[word] = tf * idf.get(word, 0)
        tfidf_matrix.append(vector)

    # Popularity score: rating weighted by log(review count), normalized
    max_popularity = 0
    for r in recipes:
        ratings = r.get("ratings")
        if ratings and isinstance(ratings, dict) and ratings.get("rating") is not None:
            count = ratings.get("count", 1)
            if isinstance(count, (int, float)) and count > 0:
                r["popularity_raw"] = ratings["rating"] * math.log(count + 1)
                max_popularity = max(max_popularity, r["popularity_raw"])
            else:
                r["popularity_raw"] = 0.0
        else:
            r["popularity_raw"] = 0.0

    for r in recipes:
        r["popularity"] = (r["popularity_raw"] / max_popularity) if max_popularity > 0 else 0.0

    # Export the vocabulary
    vocabulary = sorted(list(doc_freq.keys()))
    vocab_file = os.path.join(CACHE_DIR, "vocabulary.json")
    with open(vocab_file, "w", encoding="utf-8") as f:
        json.dump(vocabulary, f, indent=2)
    print(f"Vocabulary exported to {vocab_file} (Size: {len(vocabulary)} words)")

    index_data = {
        "recipes": recipes,
        "tfidf_matrix": tfidf_matrix,
        "idf": idf
    }
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(index_data, f)

    return index_data


INDEX = load_or_build_index()

# SIMILARITY
def cosine_similarity(vec_a, vec_b):
    dot = 0.0
    for word, val in vec_a.items():
        if word in vec_b:
            dot += val * vec_b[word]

    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# NATION LABEL HELPERS
def normalize_nation_name(nation):
    for main_country, syn_list in NATION_SYNONYMS.items():
        if nation in syn_list or nation == main_country:
            return main_country
    return nation


def get_all_nations():
    nations = set()
    for recipe in INDEX["recipes"]:
        tags = recipe.get("tags", {})
        if isinstance(tags, dict):
            cuisines = tags.get("cuisine", [])
            if isinstance(cuisines, list):
                for c in cuisines:
                    if isinstance(c, str):
                        nations.add(normalize_nation_name(c))
    return sorted(list(nations))


# INGREDIENT MATCH SCORE (display-only signal)
def calculate_ingredient_match(query_keywords, ingredient_names):
    if not query_keywords:
        return 0.0

    recipe_names = {manual_stem(name.lower()) for name in ingredient_names if name}
    query_cleaned = {kw for kw in query_keywords if kw not in STOP_WORDS}

    if not query_cleaned or not recipe_names:
        return 0.0

    matches = len(query_cleaned.intersection(recipe_names))
    return (matches / len(query_cleaned)) * 100


# MAIN SEARCH FUNCTION
def search(query, top_k=5, calorie_filter=None):
    """
    Steps:
      1. Expand the raw query using QUERY_SYNONYMS.
      2. Preprocess it into the same tokenize/stopword/stem pipeline as the index.
      3. Build a TF-IDF query vector.
      4. Filter recipes by calorie range (if calorie_filter is given).
      5. Score each candidate: final_score = 0.9 * cosine_similarity + 0.1 * popularity.
      6. Sort, keep the top_k, and attach display fields.
      
    """
    recipes = INDEX["recipes"]
    tfidf_matrix = INDEX["tfidf_matrix"]
    idf = INDEX["idf"]

    # Query expansion
    expanded_query = query
    for q_word in query.lower().split():
        if q_word in QUERY_SYNONYMS:
            expanded_query += " " + " ".join(QUERY_SYNONYMS[q_word])

    # Query preprocessing + TF-IDF vector
    query_tokens = preprocess_document(expanded_query)
    query_vec = {}
    if query_tokens:
        total = len(query_tokens)
        counts = {}
        for t in query_tokens:
            counts[t] = counts.get(t, 0) + 1
        for t, c in counts.items():
            if t in idf:
                query_vec[t] = (c / total) * idf[t]

    # Calorie filtering
    filtered_indices = []
    for i, r in enumerate(recipes):
        if calorie_filter:
            min_cal, max_cal = calorie_filter
            calories = r.get("calories")
            if calories is None:
                continue
            if max_cal is None:
                if calories < min_cal:
                    continue
            elif not (min_cal <= calories < max_cal):
                continue

        filtered_indices.append(i)

    # Scoring
    scored = []
    for i in filtered_indices:
        sim = cosine_similarity(query_vec, tfidf_matrix[i]) if query_vec else 0.0
        pop = recipes[i].get("popularity", 0.0)
        final_score = (0.9 * sim) + (0.1 * pop)
        scored.append((i, sim, pop, final_score))

    scored.sort(key=lambda x: x[3], reverse=True)

    #final result
    results = []
    for idx, sim, pop, final_score in scored[:top_k]:
        if sim <= 0.001:
            continue

        r = recipes[idx].copy()
        r.pop("search_text", None)
        r["similarity"] = round(sim * 100, 2)
        r["popularity"] = round(pop * 100, 2)
        r["final_score"] = round(final_score * 100, 2)
        r["ingredient_match"] = round(
            calculate_ingredient_match(query_tokens, r.get("ingredients_names", [])), 2
        )

        tags = r.get("tags", {})
        cuisines = tags.get("cuisine", []) if isinstance(tags, dict) else []
        r["nation"] = normalize_nation_name(cuisines[0]) if cuisines else "International"

        results.append(r)

    return results