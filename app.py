import os
import random

import streamlit as st

from data_loader import load_menu, parse_manual_ingredients
from prompt_builder import build_recipe_prompt, generate_recipe


def render_cookware_ui(menu_data):
    """顯示廚具選單；參數為選單字典，回傳廚具清單。"""
    st.subheader("1. 選擇手邊廚具")
    cookware = st.multiselect(
        "目前可使用的廚具（至少選一項）",
        menu_data["cookware"],
        key="selected_cookware",
    )
    return cookware


def render_ingredients_ui(menu_data):
    """顯示食材與調味料選單；參數為選單字典，回傳兩者清單。"""
    st.subheader("2. 選擇手邊食材")
    selected_ingredients = []
    for category, items in menu_data["categories"].items():
        with st.expander(category):
            # 肉類先選肉種，再選肉品型態，避免一次顯示過多選項。
            if category == "肉類" and type(items) is dict:
                for meat_type, forms in items.items():
                    selected_forms = st.multiselect(
                        meat_type,
                        forms,
                        key="meat_" + meat_type,
                    )
                    for form in selected_forms:
                        selected_ingredients.append(meat_type + "（" + form + "）")
            elif type(items) is list:
                category_items = st.multiselect(
                    "選擇" + category,
                    items,
                    key="category_" + category,
                )
                for item in category_items:
                    selected_ingredients.append(item)

    raw_manual_ingredients = st.text_input(
        "其他食材（可用逗號分隔）",
        placeholder="例如：剩飯，冷凍玉米",
        key="manual_ingredients",
    )
    manual_ingredients = parse_manual_ingredients(raw_manual_ingredients)
    for ingredient in manual_ingredients:
        if ingredient not in selected_ingredients:
            selected_ingredients.append(ingredient)

    # 基本調味料預設全選，使用者可取消不具備的項目。
    seasonings_default = None
    if "selected_default_seasonings" not in st.session_state:
        seasonings_default = menu_data["default_seasonings"]
    seasonings = st.multiselect(
        "基本調味料（預設全選，請取消沒有的項目）",
        menu_data["default_seasonings"],
        default=seasonings_default,
        key="selected_default_seasonings",
    )
    return selected_ingredients, seasonings


def render_preference_ui(menu_data):
    """顯示料理偏好和微採買開關；參數為選單字典，回傳偏好與布林值。"""
    st.subheader("3. 設定食譜偏好")
    preference = st.selectbox(
        "想做哪一類料理？",
        menu_data["recipe_preferences"],
        key="recipe_preference",
    )
    allow_extra_buy = st.checkbox(
        "允許建議加買 1～2 樣超商常見食材",
        value=False,
        key="allow_extra_buy",
    )
    return preference, allow_extra_buy


def _form_widget_keys(menu_data):
    """回傳表單中所有 widget 的 session state key。"""
    keys = [
        "selected_cookware",
        "manual_ingredients",
        "selected_default_seasonings",
        "recipe_preference",
        "allow_extra_buy",
    ]
    for category, items in menu_data["categories"].items():
        if category == "肉類" and type(items) is dict:
            for meat_type in items:
                keys.append("meat_" + meat_type)
        elif type(items) is list:
            keys.append("category_" + category)
    return keys


def _random_challenge_values(menu_data):
    """產生隨機挑戰選項，回傳表單值、總數與食材數。"""
    ingredient_options = []
    seasoning_options = []
    selection_keys = [
        key
        for key in _form_widget_keys(menu_data)
        if key not in (
            "selected_cookware",
            "manual_ingredients",
            "recipe_preference",
            "allow_extra_buy",
        )
    ]
    form_values = {key: [] for key in selection_keys}
    form_values["manual_ingredients"] = ""
    form_values["selected_default_seasonings"] = list(
        menu_data["default_seasonings"]
    )

    for category, items in menu_data["categories"].items():
        if category == "肉類" and type(items) is dict:
            for meat_type, forms in items.items():
                for form in forms:
                    ingredient_options.append(("meat_" + meat_type, form))
        elif type(items) is list:
            option_list = (
                seasoning_options
                if category == "其他調味料"
                else ingredient_options
            )
            option_list.extend(
                ("category_" + category, item) for item in items
            )

    if len(ingredient_options) < 4:
        raise ValueError("隨機食材挑戰需要至少 4 種可選食材。")
    if len(ingredient_options) + len(seasoning_options) < 6:
        raise ValueError("隨機食材挑戰需要至少 6 種可選食材或調味料。")

    total_count = random.randint(
        6,
        min(10, len(ingredient_options) + len(seasoning_options)),
    )
    minimum_ingredients = max(4, total_count - len(seasoning_options))
    maximum_ingredients = min(len(ingredient_options), total_count)
    ingredient_count = random.randint(minimum_ingredients, maximum_ingredients)
    seasoning_count = total_count - ingredient_count

    for key, item in random.sample(ingredient_options, ingredient_count):
        form_values[key].append(item)
    for key, item in random.sample(seasoning_options, seasoning_count):
        form_values[key].append(item)

    return form_values, total_count, ingredient_count


def _save_form_values(menu_data):
    """保存表單選項，供切換頁面後恢復。"""
    st.session_state["recipe_form_values"] = {
        key: st.session_state[key]
        for key in _form_widget_keys(menu_data)
        if key in st.session_state
    }


def _restore_form_values():
    """在建立表單 widget 前恢復先前保存的選項。"""
    form_values = st.session_state.pop("recipe_form_values", {})
    for key, value in form_values.items():
        st.session_state[key] = value


def _generate_recipe_for_inputs(recipe_inputs):
    """依已保存的輸入生成食譜；回傳食譜是否生成成功。"""
    prompt = build_recipe_prompt(
        recipe_inputs["cookware"],
        recipe_inputs["ingredients"],
        recipe_inputs["seasonings"],
        recipe_inputs["preference"],
        recipe_inputs["allow_extra_buy"],
    )
    try:
        with st.spinner("正在依照你的食材和廚具設計食譜…"):
            recipe_data = generate_recipe(prompt)
    except (RuntimeError, ValueError) as error:
        st.session_state["recipe_generation_error"] = str(error)
        return False

    st.session_state.pop("recipe_generation_error", None)
    st.session_state["recipe_data"] = recipe_data
    return True


def _format_quantity(amount):
    """格式化克重與液體容積。"""
    quantity = str(amount["grams"]) + " g"
    if amount["is_liquid"]:
        quantity += " · " + str(amount["milliliters"]) + " mL"
    return quantity


def _render_measured_items(items, quantities, empty_message):
    """顯示項目名稱與分量。"""
    if not items:
        st.caption(empty_message)
        return

    for item in items:
        item_column, quantity_column = st.columns([3, 1])
        with item_column:
            st.write(item)
        with quantity_column:
            st.markdown("**" + _format_quantity(quantities[item]) + "**")


def render_recipe_result(recipe_data):
    """以分區卡片顯示食譜；參數為食譜字典。"""
    st.markdown(
        """
        <style>
        .st-key-recipe_ingredients_card,
        .st-key-recipe_notes_card {
            padding: 1rem 1.2rem;
            border-radius: 14px;
            border: 1px solid;
            margin-bottom: 0.75rem;
        }
        .st-key-recipe_ingredients_card,
        .st-key-recipe_notes_card {
            background: #3b3733;
            border-color: #ffffff;
            color: #f5f0e9;
        }
        .st-key-recipe_ingredients_card [data-testid="stMarkdownContainer"] *,
        .st-key-recipe_ingredients_card [data-testid="stCaptionContainer"] *,
        .st-key-recipe_notes_card [data-testid="stMarkdownContainer"] *,
        .st-key-recipe_notes_card [data-testid="stCaptionContainer"] * {
            color: #f5f0e9 !important;
        }
        .st-key-recipe_ingredients_card hr {
            border-color: #766d64;
        }
        .st-key-recipe_steps [data-testid="stMarkdownContainer"] p {
            font-size: 1.1rem;
            line-height: 1.65;
        }
        .st-key-recipe_steps hr {
            border-color: #ffffff;
            opacity: 0.9;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title(recipe_data["dish_name"])
    st.caption(
        "份量：" + str(recipe_data["servings"]) + " 人份　｜　"
        + "預估時間：" + str(recipe_data["time_minutes"]) + " 分鐘　｜　"
        + "偏好：" + recipe_data["preference"]
    )

    st.divider()
    st.subheader("使用食材")
    with st.container(key="recipe_ingredients_card"):
        ingredient_column, seasoning_column = st.columns(2)
        with ingredient_column:
            st.markdown("#### 現有食材")
            _render_measured_items(
                recipe_data["existing_ingredients"],
                recipe_data["ingredient_quantities"],
                "本食譜沒有使用已選食材。",
            )
        with seasoning_column:
            st.markdown("#### 調味料")
            _render_measured_items(
                recipe_data["used_seasonings"],
                recipe_data["seasoning_quantities"],
                "本食譜沒有使用已選調味料。",
            )

        st.divider()
        purchase_column, cookware_column = st.columns(2)
        with purchase_column:
            st.markdown("#### 建議加買")
            if recipe_data["suggested_purchases"]:
                for item in recipe_data["suggested_purchases"]:
                    st.write("- " + item)
            else:
                st.caption("不需要額外採買。")
        with cookware_column:
            st.markdown("#### 使用廚具")
            for cookware in recipe_data["cookware_used"]:
                st.write("- " + cookware)

    st.divider()
    st.subheader("食譜步驟")
    with st.container(key="recipe_steps"):
        for index, step in enumerate(recipe_data["steps"]):
            step_title_column, cookware_column = st.columns([3, 1])
            with step_title_column:
                st.markdown("#### 步驟 " + str(step["step_number"]))
            with cookware_column:
                st.caption("廚具：" + step["cookware"])
            st.write(step["instruction"])
            if index < len(recipe_data["steps"]) - 1:
                st.divider()

    st.divider()
    st.subheader("注意事項")
    with st.container(key="recipe_notes_card"):
        if recipe_data["reminders"]:
            for reminder in recipe_data["reminders"]:
                st.write("- " + reminder)
        else:
            st.caption("暫無額外注意事項。")


def main():
    """載入選單並控制輸入、生成與顯示流程；無參數，沒有回傳值。"""
    st.set_page_config(page_title="宿舍食譜助手", page_icon="🍳", layout="wide")
    st.title("🍳 宿舍食譜助手")
    st.write("用手邊的食材和廚具，快速找到一道適合現在的料理。")
    st.caption("選好食材、口感偏好與採買方式，再生成專屬食譜。")

    menu_filepath = os.path.join(os.path.dirname(__file__), "menu.json")
    try:
        menu_data = load_menu(menu_filepath)
    except (OSError, ValueError) as error:
        st.error("讀取 menu.json 失敗：" + str(error))
        st.stop()

    selection_view = st.empty()

    if st.session_state.get("current_view") == "recipe":
        selection_view.empty()
        first_column, second_column = st.columns(2)
        with first_column:
            regenerate = st.button(
                "重新生成",
                type="primary",
                key="regenerate_recipe",
            )
        with second_column:
            return_to_form = st.button(
                "返回選擇食材",
                key="return_to_recipe_form",
            )

        if return_to_form:
            st.session_state["current_view"] = "form"
            st.rerun()
        if regenerate:
            if not _generate_recipe_for_inputs(
                st.session_state["recipe_inputs"]
            ):
                st.error(st.session_state.pop("recipe_generation_error"))

        recipe_data = st.session_state.get("recipe_data")
        if recipe_data is not None:
            render_recipe_result(recipe_data)
        return

    if st.session_state.get("current_view") == "generating":
        selection_view.empty()
        if _generate_recipe_for_inputs(st.session_state["recipe_inputs"]):
            st.session_state["current_view"] = "recipe"
        else:
            st.session_state["current_view"] = "form"
        st.rerun()

    _restore_form_values()
    generation_error = st.session_state.pop("recipe_generation_error", None)
    if generation_error is not None:
        st.error(generation_error)

    with selection_view.container():
        _, challenge_column = st.columns([5, 1])
        with challenge_column:
            random_challenge = st.button(
                "🎲 隨機食材挑戰",
                key="random_ingredient_challenge",
                use_container_width=True,
            )
        if random_challenge:
            try:
                challenge_values, total_count, ingredient_count = (
                    _random_challenge_values(menu_data)
                )
            except ValueError as error:
                st.error(str(error))
            else:
                for key, value in challenge_values.items():
                    st.session_state[key] = value
                st.success(
                    "已隨機挑選 " + str(total_count) + " 種，其中食材 "
                    + str(ingredient_count) + " 種。"
                )

        # 使用表單集中輸入，避免每次點選都重新呼叫 AI。
        with st.form("recipe_input_form"):
            cookware = render_cookware_ui(menu_data)
            ingredients, seasonings = render_ingredients_ui(menu_data)
            preference, allow_extra_buy = render_preference_ui(menu_data)
            submitted = st.form_submit_button("✨ 生成食譜", type="primary")

    if submitted:
        if len(cookware) == 0:
            st.error("請至少選擇一項可用廚具。")
            st.session_state["recipe_data"] = None
        elif len(ingredients) == 0:
            st.error("請至少選擇或輸入一項食材。")
            st.session_state["recipe_data"] = None
        else:
            st.session_state["recipe_inputs"] = {
                "cookware": cookware,
                "ingredients": ingredients,
                "seasonings": seasonings,
                "preference": preference,
                "allow_extra_buy": allow_extra_buy,
            }
            st.session_state["recipe_data"] = None
            _save_form_values(menu_data)
            selection_view.empty()
            st.session_state["current_view"] = "generating"
            st.rerun()

    if st.session_state.get("current_view") == "recipe":
        st.rerun()


if __name__ == "__main__":
    main()
