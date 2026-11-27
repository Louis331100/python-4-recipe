# 宿舍食譜助手

使用 Streamlit、Gemini API 生成食譜與料理圖片。

## 安裝與執行

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GEMINI_API_KEY="你的 Gemini API 金鑰"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Gemini API 金鑰可從 [Google AI Studio](https://aistudio.google.com/apikey) 取得。
若需要更換模型，可設定 `GEMINI_MODEL`（食譜）或 `GEMINI_IMAGE_MODEL`（圖片）。
選單資料放在 `menu.json`。肉類可先選肉種再勾選型態；也可手動輸入食材。
