import json
import os


def build_recipe_prompt(cookware, ingredients, seasonings, preference, allow_extra_buy):
    """依使用者條件組合防止憑空增加食材的食譜 Prompt。

    參數：cookware、ingredients、seasonings 為清單；preference 為偏好字串；
    allow_extra_buy 為是否允許建議加買的布林值。
    回傳：包含規則與 JSON 格式要求的 Prompt 字串。
    """
    if allow_extra_buy:
        purchase_rule = (
            "可建議加買最多 2 樣超商常見食材，並且只能列在 "
            "suggested_purchases。若不需要加買，回傳空清單。"
        )
    else:
        purchase_rule = (
            "嚴格禁止建議加買任何食材，suggested_purchases 必須是空清單。"
        )

    conditions = {
        "available_cookware": cookware,
        "available_ingredients": ingredients,
        "available_seasonings": seasonings,
        "recipe_preference": preference,
        "allow_extra_buy": allow_extra_buy,
    }

    return (
        "你是食譜建議助手，請根據提供的條件設計一份可實際操作的食譜。\n"
        "防幻覺規則：現有食材與調味料只能使用清單內項目，不可假設使用者還有"
        "其他食材、調味料或廚具。食譜步驟只能使用已提供的廚具。"
        "existing_ingredients 中的名稱必須逐字對應提供的食材或調味料清單。"
        + purchase_rule
        + "\n不要把建議加買的食材列為現有食材。步驟請清楚、具體並符合偏好。"
        "\n只輸出有效 JSON，不要使用 Markdown 或額外文字。格式如下："
        '\n{"name":"菜名","existing_ingredients":["現有食材與調味料"],'
        '"suggested_purchases":["建議加買食材"],'
        '"steps":["步驟一","步驟二"],"reminders":["提醒"]}'
        "\n使用者條件：\n"
        + json.dumps(conditions, ensure_ascii=False)
    )


def generate_recipe(prompt):
    """呼叫 Gemini API 並解析食譜 JSON。

    參數：prompt 為完整的食譜生成 Prompt。
    回傳：包含菜名、食材、步驟與提醒的食譜字典。
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("尚未設定 GEMINI_API_KEY 環境變數。")

    # 延後載入 API 套件，讓未設定金鑰或單獨使用其他函式時仍可正常匯入。
    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as error:
        raise RuntimeError(
            "找不到 google-genai 套件，請先執行 pip install -r requirements.txt。"
        ) from error

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-4-hydrogen",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
    except errors.APIError as error:
        raise RuntimeError("呼叫 Gemini API 失敗：" + str(error)) from error

    if not response.text:
        raise RuntimeError("Gemini API 沒有回傳食譜內容。")

    try:
        recipe_data = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise ValueError("API 回傳的內容不是有效 JSON。") from error

    if not isinstance(recipe_data, dict):
        raise ValueError("API 回傳的食譜必須是 JSON 物件。")

    required_fields = [
        "name",
        "existing_ingredients",
        "suggested_purchases",
        "steps",
        "reminders",
    ]
    for field in required_fields:
        if field not in recipe_data:
            raise ValueError("API 回傳的食譜缺少欄位：" + field)

    if not isinstance(recipe_data["name"], str):
        raise ValueError("食譜的 name 欄位必須是文字。")
    if not isinstance(recipe_data["existing_ingredients"], list):
        raise ValueError("食譜的 existing_ingredients 欄位必須是清單。")
    if not isinstance(recipe_data["suggested_purchases"], list):
        raise ValueError("食譜的 suggested_purchases 欄位必須是清單。")
    if not isinstance(recipe_data["steps"], list):
        raise ValueError("食譜的 steps 欄位必須是清單。")
    if not isinstance(recipe_data["reminders"], list):
        raise ValueError("食譜的 reminders 欄位必須是清單。")

    for field in ["existing_ingredients", "suggested_purchases", "steps", "reminders"]:
        for item in recipe_data[field]:
            if not isinstance(item, str):
                raise ValueError(field + " 清單中的每個項目都必須是文字。")

    return recipe_data
