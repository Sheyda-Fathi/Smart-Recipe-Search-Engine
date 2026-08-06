import streamlit as st  # type: ignore
import os
import re
import hashlib
from search_engine import search

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Smart Recipe Search Engine",
    page_icon="🍳",
    layout="wide"
)

#CSS STYLING
st.markdown("""
<style>

/* Header */
.header-title {
    text-align:center;
    font-size:48px;
    font-weight:800;
    color:#e63e75;
}

/* Card container - the border color itself is fixed (see module
    docstring for why); the per-card theme shows up via .color-line
   and every other themed element inside the card instead. */
[data-testid="stVerticalBlockBorderWrapper"] {
    width: 85%;
    margin: 0 auto 30px auto;
    border-radius: 24px;
    padding: 24px 28px;
    background: white;
    border: 2px solid #f4a6b8;
    box-shadow: 0 4px 18px rgba(230,62,117,0.10);
    transition: all 0.25s ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 8px 28px rgba(230,62,117,0.16);
}

/* Colored strip at the top of every card - the per-card theme's
    most visible signature, and our workaround for not being able
   to recolor the container's own border (see module docstring). */
.color-line {
    height: 8px;
    width: 100%;
    border-radius: 999px;
    margin-bottom: 18px;
}

.recipe-title {
    font-size: 22px;
    font-weight: 800;
    color: #111827;
    margin-bottom: 10px;
}

/* Badges */
.badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 10px;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    border-radius: 14px;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.3;
    border: 1px solid transparent;
}

.time-badge { background: #FCE4EC; color: #C2185B; }
.rating-badge { background: #FFF6DA; color: #B8860B; }
.country-badge { background: #E3F2FD; color: #0D47A1; }
.published-badge { background: #E8F5E9; color: #2E7D32; }
.similarity-badge { background: #E3F2FD; color: #1565C0; }
.popularity-badge { background: #FFF0E5; color: #D84315; }
.total-badge { background: #F3E5F5; color: #6A1B9A; }

/* Calorie badge - colors are set inline per-card (theme-driven) */
.calorie-badge {
    font-weight: 800;
}

/* Description text */
.recipe-description {
    color: #374151;
    font-size: 15px;
    line-height: 1.8;
    margin: 0 0 18px 0;
    padding: 16px 0;
    white-space: normal;
    word-wrap: break-word;
}

/* Total score progress bar */
.total-score-title {
    margin-top: 4px;
    margin-bottom: 8px;
    font-size: 16px;
    font-weight: 800;
    color: #C2185B;
}

.score-progress {
    width: 100%;
    height: 12px;
    border-radius: 999px;
    background: #F1E4E8;
    overflow: hidden;
    margin-bottom: 18px;
}

.score-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
}

/* Key Ingredients box - colors set inline per-card (theme-driven) */
.ingredient-names-box {
    padding: 16px 20px;
    border-radius: 16px;
    margin-bottom: 16px;
    border-left: 4px solid;
}

.ingredient-names-box .box-title {
    font-weight: 800;
    font-size: 16px;
    margin-bottom: 12px;
}

.ingredient-chip {
    display: inline-block;
    background: white;
    border: 1px solid;
    font-size: 13px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 999px;
    margin: 0 6px 6px 0;
    transition: all 0.2s;
}

/* Full Ingredients box - colors set inline per-card (theme-driven) */
.ingredients-box {
    padding: 18px 20px;
    border-radius: 16px;
    height: 100%;
    background: white;
    border-left: 4px solid;
}

.ingredients-box .box-title {
    font-weight: 800;
    font-size: 16px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.ingredient-line {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    font-size: 14px;
    color: #374151;
    line-height: 1.6;
    margin-bottom: 8px;
}

.ingredient-dot {
    font-size: 18px;
    line-height: 1.3;
}

/* Preparation Steps box - colors set inline per-card (theme-driven) */
.instructions-box {
    padding: 18px 20px;
    border-radius: 16px;
    height: 100%;
    background: white;
    border-left: 4px solid;
}

.instructions-box .box-title {
    font-weight: 800;
    font-size: 16px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.step-card {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: white;
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 10px;
    font-size: 14px;
    color: #374151;
    line-height: 1.6;
}

.step-pill {
    flex-shrink: 0;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
    white-space: nowrap;
    color: white;
}

/* Show more / show less button */
.show-more-btn {
    width: 100%;
    margin-top: 8px;
}

/* Items past the initial preview count are hidden until "Show more" */
.hidden-item {
    display: none !important;
}

/* Image */
img {
    border-radius: 18px !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    aspect-ratio: 1/1;
    object-fit: cover;
    max-height: 280px !important;
    max-width: 100% !important;
    display: block !important;
    margin: 0 auto !important;
}

.no-image {
    width: 100%;
    height: 280px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #f3f4f6;
    border-radius: 18px;
    color: #9ca3af;
    font-size: 14px;
    margin: 0 auto;
}

/* Search-keyword highlight - color is set inline per-card (theme-driven) */
.highlight-word {
    font-weight: 900;
    padding: 1px 4px;
    border-radius: 4px;
}

</style>
""", unsafe_allow_html=True)

# CALORIE COLOR THEME SYSTEM
def get_calorie_color(calories):
    if calories < 200:
        return "#F9A825"  # Yellow
    elif calories < 400:
        return "#43A047"  # Green
    elif calories < 600:
        return "#EC407A"  # Pink
    elif calories < 800:
        return "#7B1FA2"  # Purple
    else:
        return "#E53935"  # Red


def get_calorie_light_color(calories, title):
    base_color = get_calorie_color(calories)

    h = int(hashlib.md5(str(title).encode()).hexdigest(), 16)
    offset = (h % 25) - 12

    base_color = base_color.lstrip("#")
    r, g, b = (int(base_color[i:i+2], 16) for i in (0, 2, 4))

    r = max(0, min(255, r + offset * 2))
    g = max(0, min(255, g + offset * 2))
    b = max(0, min(255, b + offset * 2))

    light_r = int(r + (255 - r) * 0.82)
    light_g = int(g + (255 - g) * 0.82)
    light_b = int(b + (255 - b) * 0.82)

    return f"#{light_r:02x}{light_g:02x}{light_b:02x}"


def make_soft_background(hex_color):
    hex_color = hex_color.replace("#", "")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    r = int(r + (255 - r) * 0.88)
    g = int(g + (255 - g) * 0.88)
    b = int(b + (255 - b) * 0.88)

    return f"#{r:02x}{g:02x}{b:02x}"


def get_accent_color(calories):
    base = get_calorie_color(calories)
    base = base.lstrip("#")
    r, g, b = (int(base[i:i+2], 16) for i in (0, 2, 4))
    r = max(0, r - 40)
    g = max(0, g - 40)
    b = max(0, b - 40)
    return f"#{r:02x}{g:02x}{b:02x}"


# theme calorie=unknown
UNKNOWN_CALORIE_THEME_COLOR = "#9CA3AF"
UNKNOWN_CALORIE_LIGHT_COLOR = "#F3F4F6"
UNKNOWN_CALORIE_ACCENT_COLOR = "#6B7280"


def get_card_theme(recipe):
    calories = recipe.get("calories")  # None if unknown

    if calories is None:
        return {
            "calories": None,
            "theme_color": UNKNOWN_CALORIE_THEME_COLOR,
            "light_color": UNKNOWN_CALORIE_LIGHT_COLOR,
            "accent_color": UNKNOWN_CALORIE_ACCENT_COLOR,
            "soft_background": make_soft_background(UNKNOWN_CALORIE_THEME_COLOR),
        }

    theme_color = get_calorie_color(calories)
    return {
        "calories": calories,
        "theme_color": theme_color,
        "light_color": get_calorie_light_color(calories, recipe.get("title", "")),
        "accent_color": get_accent_color(calories),
        "soft_background": make_soft_background(theme_color),
    }

# TEXT HIGHLIGHTING
def highlight_keywords(text, keywords, color, light_color):
    if not text or not keywords:
        return text
    for kw in keywords:
        pattern = re.compile(rf'\b({re.escape(kw)})\b', flags=re.IGNORECASE)
        text = pattern.sub(
            rf'<span class="highlight-word" style="background:{light_color}; color:{color};">\g<1></span>',
            text
        )
    return text

# HEADER
st.markdown("""
<h1 class="header-title">
🍲 Smart Recipe Search Engine
</h1>
""", unsafe_allow_html=True)

st.markdown(
    """
    <center>
    Search recipes by ingredients and discover dishes from around the world 🌍
    </center>
    """,
    unsafe_allow_html=True
)

st.divider()

# SEARCH FORM
c1, c2, c3 = st.columns([1, 2, 1])

with c2:
    query = st.text_input(
        "Ingredients ...",
        placeholder="example: chicken rice tomato onion"
    )

    calorie_ranges = {
        "All": None,
        "0-200 kcal": (0, 200),
        "200-400 kcal": (200, 400),
        "400-600 kcal": (400, 600),
        "600-800 kcal": (600, 800),
        "800+ kcal": (800, None),
    }

    calorie_filter_label = st.selectbox(
        "🔥 Calorie Range",
        list(calorie_ranges.keys())
    )

    top_k = st.slider("📊 Number of Recipes", 1, 20, 5)

    search_clicked = st.button(
        "🔍 SEARCH RECIPES",
        use_container_width=True,
        type="primary"
    )

# SEARCH EXECUTION & RESULT RENDERING
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'search_keywords' not in st.session_state:
    st.session_state.search_keywords = []

if search_clicked:
    if not query.strip():
        st.warning("⚠️ Please enter ingredients.")
    else:
        with st.spinner("Searching delicious recipes..."):
            calorie_filter = calorie_ranges[calorie_filter_label]

            results = search(
                query=query,
                top_k=top_k,
                calorie_filter=calorie_filter
            )

            st.session_state.search_results = results
            st.session_state.search_query = query

            STOP_WORDS = {"a", "an", "the", "and", "or", "of", "with", "for", "in", "on"}
            st.session_state.search_keywords = [w for w in query.lower().split() if w not in STOP_WORDS]

if st.session_state.search_results is not None:
    results = st.session_state.search_results
    keywords = st.session_state.search_keywords

    if len(results) == 0:
        st.warning("No recipes found. Try different ingredients or calorie range.")
    else:
        st.success(f"Found {len(results)} recipes!")

        for idx, recipe in enumerate(results):
            country = recipe.get("nation") or "International"
            total_score = recipe["final_score"]
            sim_score = recipe["similarity"]
            pop_score = recipe["popularity"]

            #Per-card calorie theme
            theme = get_card_theme(recipe)
            calories = theme["calories"]
            theme_color = theme["theme_color"]
            light_color = theme["light_color"]
            accent_color = theme["accent_color"]
            soft_background = theme["soft_background"]

            #Show more/less state
            ingredients_expand_key = f"ingredients_expand_{idx}_{recipe['title']}"
            steps_expand_key = f"steps_expand_{idx}_{recipe['title']}"

            if ingredients_expand_key not in st.session_state:
                st.session_state[ingredients_expand_key] = False
            if steps_expand_key not in st.session_state:
                st.session_state[steps_expand_key] = False

            with st.container(border=True):
                # Colored top strip
                st.markdown(
                    f'<div class="color-line" style="background:{theme_color};"></div>',
                    unsafe_allow_html=True
                )

                # Two-column layout
                top_text, top_img = st.columns([65, 35])

                with top_text:
                    st.markdown(
                        f'<div class="recipe-title">{idx+1}. {recipe["title"]}</div>',
                        unsafe_allow_html=True
                    )

                    #Row 1: time / rating / calories / country / published
                    row1 = []
                    if recipe.get("cooking_time"):
                        row1.append(f'<span class="badge time-badge">⏱️ {recipe["cooking_time"]} min</span>')

                    ratings = recipe.get("ratings") or {}
                    if ratings.get("rating") is not None:
                        count = ratings.get("count", 0)
                        row1.append(
                            f'<span class="badge rating-badge">⭐ {ratings["rating"]} ({count} reviews)</span>'
                        )

                    calorie_text = f"{calories:.0f} kcal" if calories is not None else "N/A"
                    row1.append(
                        f'<span class="badge calorie-badge" '
                        f'style="background:{light_color}; color:{theme_color}; border-color:{accent_color};">'
                        f'🔥 {calorie_text}</span>'
                    )

                    row1.append(f'<span class="badge country-badge">🌎 {country}</span>')

                    if recipe.get("published"):
                        row1.append(f'<span class="badge published-badge">📅 Published: {recipe["published"]}</span>')

                    st.markdown(f'<div class="badge-row">{"".join(row1)}</div>', unsafe_allow_html=True)

                    #Row 2: similarity / popularity / total score
                    row2 = [
                        f'<span class="badge similarity-badge">📈 Similarity: {sim_score:.2f}%</span>',
                        f'<span class="badge popularity-badge">🔥 Popularity: {pop_score:.2f}%</span>',
                        f'<span class="badge total-badge">🏆 Total Score: {total_score:.2f}%</span>',
                    ]
                    st.markdown(f'<div class="badge-row">{"".join(row2)}</div>', unsafe_allow_html=True)

                    # Total score progress bar
                    st.markdown(
                        f"""
                        <div class="total-score-title">
                            🏆 Total Score: {total_score:.2f}%
                        </div>
                        <div class="score-progress">
                            <div class="score-fill" style="width:{total_score}%; background: linear-gradient(90deg, {light_color}, {theme_color});"></div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with top_img:
                    img_filename = recipe.get("image_filename")
                    img_path = os.path.join("data", "images", "images", img_filename) if img_filename else None

                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.markdown('<div class="no-image">🍲<br>No Image</div>', unsafe_allow_html=True)


                # DESCRIPTION
                description = recipe.get("description")
                if description:
                    clean_desc = ' '.join(description.split())
                    st.markdown(
                        f'<div class="recipe-description">📖 {highlight_keywords(clean_desc, keywords, theme_color, light_color)}</div>',
                        unsafe_allow_html=True
                    )

                # KEY INGREDIENTS
                ingredient_names = recipe.get("ingredients_names", [])
                chips = "".join(
                    f'<span class="ingredient-chip" style="border-color:{accent_color}; color:{theme_color};">'
                    f'{highlight_keywords(name, keywords, theme_color, light_color)}</span>'
                    for name in ingredient_names
                )
                if chips:
                    st.markdown(
                        f"""
                        <div class="ingredient-names-box"
                             style="border-left-color:{theme_color}; background:{soft_background};">
                            <div class="box-title" style="color:{theme_color};">🥬 Key Ingredients</div>
                            {chips}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


                # FULL INGREDIENTS + PREPARATION STEPS
                ing_col, instr_col = st.columns([1, 1])

                with ing_col:
                    ingredients_full = recipe.get("ingredients_full", [])
                    show_count = 3  # preview size before "Show more"
                    total_items = len(ingredients_full)

                    lines_html = ""
                    for i, item in enumerate(ingredients_full):
                        is_hidden = (i >= show_count) and (not st.session_state[ingredients_expand_key])
                        display_class = "hidden-item" if is_hidden else ""
                        lines_html += f'''
                        <div class="ingredient-line {display_class}">
                            <span class="ingredient-dot" style="color:{theme_color};">•</span>
                            <span>{highlight_keywords(item, keywords, theme_color, light_color)}</span>
                        </div>
                        '''

                    if total_items > show_count:
                        button_label = (
                            "📖 Show Less" if st.session_state[ingredients_expand_key]
                            else f"📖 Show All ({total_items} items)"
                        )
                        if st.button(button_label, key=f"ing_btn_{idx}", use_container_width=True):
                            st.session_state[ingredients_expand_key] = not st.session_state[ingredients_expand_key]
                            st.rerun()

                    st.markdown(
                        f"""
                        <div class="ingredients-box"
                             style="border-left-color:{theme_color}; background:{soft_background};">
                            <div class="box-title" style="color:{theme_color};">📦 Full Ingredients</div>
                            {lines_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with instr_col:
                    instructions = recipe.get("instructions", {})
                    try:
                        step_keys = sorted(instructions.keys(), key=lambda x: int(x))
                    except (TypeError, ValueError):
                        step_keys = instructions.keys()

                    show_count_steps = 2  # preview size before "Show more"
                    total_steps = len(step_keys)

                    step_html = ""
                    for i, k in enumerate(step_keys):
                        is_hidden = (i >= show_count_steps) and (not st.session_state[steps_expand_key])
                        display_class = "hidden-item" if is_hidden else ""
                        step_html += f'''
                        <div class="step-card {display_class}">
                            <span class="step-pill" style="background:{theme_color};">Step {i+1}</span>
                            <span>{highlight_keywords(instructions[k], keywords, theme_color, light_color)}</span>
                        </div>
                        '''

                    if total_steps > show_count_steps:
                        button_label = (
                            "📖 Show Less" if st.session_state[steps_expand_key]
                            else f"📖 Show All ({total_steps} steps)"
                        )
                        if st.button(button_label, key=f"step_btn_{idx}", use_container_width=True):
                            st.session_state[steps_expand_key] = not st.session_state[steps_expand_key]
                            st.rerun()

                    st.markdown(
                        f"""
                        <div class="instructions-box"
                            style="border-left-color:{theme_color}; background:{soft_background};">
                            <div class="box-title" style="color:{theme_color};">🍳 Preparation Steps</div>
                            {step_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

else:
    st.markdown(
        """
        <div style="text-align:center; color:#6b7280; font-size:18px; padding:60px;">
        🍳 <b>Smart Recipe Search Engine</b><br><br>
        Powered by TF-IDF + Popularity Ranking
        </div>
        """,
        unsafe_allow_html=True
    )