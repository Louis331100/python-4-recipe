import os

import streamlit as st

from data_loader import load_menu, parse_manual_ingredients
from prompt_builder import build_recipe_prompt, generate_recipe


def render_inventory_ui(menu_data):
    """顯示廚具與食材盤點介面。

    參數：menu_data 為選單設定字典。
    回傳：已選廚具、食材及調味料的三個清單。
    """
    st.subheader("1. 選擇現有廚具")
    cookware = st.multiselect(
        "請勾選可以使用的廚具",
        menu_data["cookware"],
        key="cookware",
    )

    st.subheader("2. 選擇現有食材")
    ingredients = []

    # 依 JSON 分類建立摺疊選單；肉類額外使用肉種與型態兩段式選取。
    for category, choices in menu_data["categories"].items():
        with st.expander(category):
            if isinstance(choices, dict):
                for meat_type, forms in choices.items():
                    selected_forms = st.multiselect(
                        meat_type,
                        forms,
                        key="meat_" + meat_type,
                    )
                    for form in selected_forms:
                        ingredients.append(meat_type + "（" + form + "）")
            else:
                ingredients.extend(
                    st.multiselect(
                        "勾選已有項目",
                        choices,
                        key="category_" + category,
                    )
                )

    manual_text = st.text_input("其他食材（以逗號分隔）", key="manual_ingredients")
    ingredients.extend(parse_manual_ingredients(manual_text))

    st.subheader("3. 基本調味料")
    seasonings = st.multiselect(
        "已預設全選，可依實際庫存取消勾選",
        menu_data["default_seasonings"],
        default=menu_data["default_seasonings"],
        key="seasonings",
    )

    return cookware, ingredients, seasonings


def render_preference_ui(menu_data):
    """顯示食譜偏好與微採買設定。

    參數：menu_data 為選單設定字典。
    回傳：偏好字串與是否允許加買食材的布林值。
    """
    st.subheader("4. 食譜偏好")
    preference = st.selectbox(
        "選擇料理方向",
        menu_data["recipe_preferences"],
        key="recipe_preference",
    )
    allow_extra_buy = st.checkbox(
        "允許建議加買 1～2 樣食材",
        value=False,
        key="allow_extra_buy",
    )
    return preference, allow_extra_buy


def render_recipe_result(recipe_data):
    """將食譜資料分區顯示於 Streamlit 頁面。

    參數：recipe_data 為解析後的食譜字典。
    回傳：無。
    """
    st.header(recipe_data["name"])

    # 分開顯示現有食材與建議加買項目，避免混淆。
    st.subheader("現有食材與調味料")
    if recipe_data["existing_ingredients"]:
        for ingredient in recipe_data["existing_ingredients"]:
            st.write("- " + ingredient)
    else:
        st.write("無")

    st.subheader("建議加買")
    if recipe_data["suggested_purchases"]:
        for ingredient in recipe_data["suggested_purchases"]:
            st.write("- " + ingredient)
    else:
        st.write("不需要加買")

    st.subheader("料理步驟")
    for step_number, step in enumerate(recipe_data["steps"], start=1):
        st.write(str(step_number) + ". " + step)

    if recipe_data["reminders"]:
        st.subheader("小提醒")
        for reminder in recipe_data["reminders"]:
            st.write("- " + reminder)


def main():
    """載入選單並控制食譜生成流程。

    參數：無。
    回傳：無。
    """
    st.set_page_config(page_title="食譜建議助手", page_icon="🍳")
    st.title("食譜建議助手")
    st.write("勾選手邊的廚具與食材，快速找到今天可以煮的料理。")

    # 從程式所在資料夾讀取本地選單，避免受啟動位置影響。
    menu_filepath = os.path.join(os.path.dirname(__file__), "menu.json")
    try:
        menu_data = load_menu(menu_filepath)
    except (OSError, ValueError) as error:
        st.error("讀取 menu.json 失敗：" + str(error))
        return

    cookware, ingredients, seasonings = render_inventory_ui(menu_data)
    preference, allow_extra_buy = render_preference_ui(menu_data)

    if st.button("生成食譜", type="primary"):
        if not cookware:
            st.warning("請至少選擇一項可使用的廚具。")
        elif not ingredients:
            st.warning("請至少選擇或輸入一項食材。")
        else:
            prompt = build_recipe_prompt(
                cookware,
                ingredients,
                seasonings,
                preference,
                allow_extra_buy,
            )
            try:
                with st.spinner("正在依照你的條件設計食譜..."):
                    recipe_data = generate_recipe(prompt)
                # 在顯示前再次檢查 API 回傳的現有食材是否都由使用者提供。
                available_ingredients = ingredients + seasonings
                for ingredient in recipe_data["existing_ingredients"]:
                    if ingredient not in available_ingredients:
                        raise ValueError(
                            "食譜列出未勾選的現有食材「"
                            + ingredient
                            + "」，請重新生成。"
                        )
                if not allow_extra_buy and recipe_data["suggested_purchases"]:
                    raise ValueError("食譜違反零採買設定，請重新生成。")
                if allow_extra_buy and len(recipe_data["suggested_purchases"]) > 2:
                    raise ValueError("食譜建議加買超過 2 樣食材，請重新生成。")
                render_recipe_result(recipe_data)
            except (RuntimeError, ValueError) as error:
                st.error(str(error))


if __name__ == "__main__":
    main()
