import json


def load_menu(filepath="menu.json"):
    """讀取選單設定檔。

    參數：filepath 為 JSON 檔案路徑。
    回傳：讀取後的設定字典。
    """
    # 以 UTF-8 讀取本地選單，保留繁體中文內容。
    with open(filepath, "r", encoding="utf-8") as menu_file:
        menu_data = json.load(menu_file)

    return menu_data


def parse_manual_ingredients(raw_text):
    """整理使用者手動輸入的食材。

    參數：raw_text 為以逗號分隔的文字。
    回傳：去除前後空白與空字串後的食材列表。
    """
    ingredients = []

    # 支援中英文逗號，並略過空白項目。
    for ingredient in raw_text.replace("，", ",").split(","):
        ingredient = ingredient.strip()
        if ingredient:
            ingredients.append(ingredient)

    return ingredients
