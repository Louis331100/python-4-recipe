import json
import os


def load_menu(filepath="menu.json"):
    """讀取並檢查選單設定；參數為 JSON 檔路徑，回傳設定字典。"""
    if os.path.isabs(filepath):
        menu_path = filepath
    else:
        menu_path = os.path.join(os.path.dirname(__file__), filepath)

    with open(menu_path, "r", encoding="utf-8") as menu_file:
        menu_data = json.load(menu_file)

    if type(menu_data) is not dict:
        raise ValueError("menu.json 的最外層必須是 JSON 物件。")

    required_keys = [
        "cookware",
        "categories",
        "default_seasonings",
        "recipe_preferences",
    ]
    for key in required_keys:
        if key not in menu_data:
            raise ValueError("menu.json 缺少必要欄位：" + key)

    if type(menu_data["cookware"]) is not list:
        raise ValueError("menu.json 的 cookware 必須是清單。")
    if type(menu_data["categories"]) is not dict:
        raise ValueError("menu.json 的 categories 必須是字典。")
    if type(menu_data["default_seasonings"]) is not list:
        raise ValueError("menu.json 的 default_seasonings 必須是清單。")
    if type(menu_data["recipe_preferences"]) is not list:
        raise ValueError("menu.json 的 recipe_preferences 必須是清單。")

    return menu_data


def parse_manual_ingredients(raw_text):
    """整理逗號分隔的手動食材；參數為輸入字串，回傳清理後的食材清單。"""
    cleaned_ingredients = []
    normalized_text = raw_text.replace("，", ",")
    ingredient_parts = normalized_text.split(",")

    for ingredient in ingredient_parts:
        cleaned_ingredient = ingredient.strip()
        if cleaned_ingredient != "":
            cleaned_ingredients.append(cleaned_ingredient)

    return cleaned_ingredients
