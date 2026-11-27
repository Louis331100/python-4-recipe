import os

import streamlit as st

from data_loader import load_menu, parse_manual_ingredients
from image_generator import generate_recipe_image
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
    seasonings = st.multiselect(
        "基本調味料（預設全選，請取消沒有的項目）",
        menu_data["default_seasonings"],
        default=menu_data["default_seasonings"],
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


def render_recipe_result(recipe_data, recipe_image=None, image_error=None):
    """分區顯示食譜；參數為食譜字典，直接輸出到 Streamlit 頁面。"""
    st.divider()
    st.subheader("4. 專屬食譜")
    st.title(recipe_data["dish_name"])
    st.caption(
        "份量：" + str(recipe_data["servings"]) + " 人份　｜　"
        + "預估時間：" + str(recipe_data["time_minutes"]) + " 分鐘　｜　"
        + "偏好：" + recipe_data["preference"]
    )

    if recipe_image is not None:
        st.image(recipe_image, caption="AI 生成料理圖片", width=600)
    elif image_error is not None:
        st.warning("食譜已生成，但圖片生成失敗：" + image_error)
    else:
        st.info("尚未生成料理圖片。")

    left_column, right_column = st.columns(2)
    with left_column:
        st.markdown("#### 使用的現有食材")
        if recipe_data["existing_ingredients"]:
            for ingredient in recipe_data["existing_ingredients"]:
                st.write("- " + ingredient)
        else:
            st.write("本食譜沒有使用已選食材。")

        st.markdown("#### 使用的已選調味料")
        if recipe_data["used_seasonings"]:
            for seasoning in recipe_data["used_seasonings"]:
                st.write("- " + seasoning)
        else:
            st.write("沒有使用已選調味料。")

    with right_column:
        st.markdown("#### 建議加買")
        if recipe_data["suggested_purchases"]:
            for item in recipe_data["suggested_purchases"]:
                st.write("- " + item)
        else:
            st.write("不需要額外採買。")

        st.markdown("#### 使用廚具")
        for cookware in recipe_data["cookware_used"]:
            st.write("- " + cookware)

    st.markdown("#### 料理步驟")
    for step in recipe_data["steps"]:
        st.markdown(
            "**步驟 " + str(step["step_number"]) + "｜"
            + step["cookware"] + "**"
        )
        st.write(step["instruction"])

    if recipe_data["reminders"]:
        st.markdown("#### 小提醒")
        for reminder in recipe_data["reminders"]:
            st.write("- " + reminder)


def main():
    """載入選單並控制輸入、生成與顯示流程；無參數，沒有回傳值。"""
    st.set_page_config(page_title="宿舍食譜助手", page_icon="🍳", layout="wide")
    st.title("🍳 宿舍食譜助手")
    st.write("用手邊的食材和廚具，快速找到一道適合現在的料理。")
    st.caption("選好食材、口感偏好與採買方式，再生成專屬食譜。")
    st.caption("每次生成食譜也會呼叫 OpenAI 圖片生成 API，並額外計費。")

    menu_filepath = os.path.join(os.path.dirname(__file__), "menu.json")
    try:
        menu_data = load_menu(menu_filepath)
    except (OSError, ValueError) as error:
        st.error("讀取 menu.json 失敗：" + str(error))
        st.stop()

    # 使用表單集中輸入，避免每次點選都重新呼叫 AI。
    with st.form("recipe_input_form"):
        cookware = render_cookware_ui(menu_data)
        ingredients, seasonings = render_ingredients_ui(menu_data)
        preference, allow_extra_buy = render_preference_ui(menu_data)
        submitted = st.form_submit_button("✨ 生成食譜", type="primary")

    if submitted:
        st.session_state["recipe_image"] = None
        st.session_state["recipe_image_error"] = None
        if len(cookware) == 0:
            st.error("請至少選擇一項可用廚具。")
            st.session_state["recipe_data"] = None
        elif len(ingredients) == 0:
            st.error("請至少選擇或輸入一項食材。")
            st.session_state["recipe_data"] = None
        else:
            prompt = build_recipe_prompt(
                cookware,
                ingredients,
                seasonings,
                preference,
                allow_extra_buy,
            )
            st.session_state["recipe_data"] = None
            try:
                with st.spinner("正在依照你的食材和廚具設計食譜…"):
                    st.session_state["recipe_data"] = generate_recipe(prompt)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))
            else:
                try:
                    with st.spinner("正在生成料理圖片…"):
                        st.session_state["recipe_image"] = generate_recipe_image(
                            st.session_state["recipe_data"]["dish_name"],
                            st.session_state["recipe_data"]["existing_ingredients"],
                        )
                except (RuntimeError, ValueError) as error:
                    st.session_state["recipe_image_error"] = str(error)

    recipe_data = st.session_state.get("recipe_data")
    if recipe_data is not None:
        render_recipe_result(
            recipe_data,
            st.session_state.get("recipe_image"),
            st.session_state.get("recipe_image_error"),
        )


if __name__ == "__main__":
    main()
