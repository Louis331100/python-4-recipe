# 食譜建議助手

以 Streamlit 製作的食譜建議 MVP。使用者可盤點廚具與食材、選擇料理偏好，
並透過 Gemini API 生成食譜。

## 安裝與執行

```powershell
python -m pip install -r requirements.txt
$env:GEMINI_API_KEY="你的 Gemini API 金鑰"
streamlit run app.py
```

選單資料放在 `menu.json`。肉類可先選肉種再勾選型態；也可用逗號手動輸入其他
食材。未勾選「允許建議加買」時，系統會要求食譜不列出任何加買項目。Gemini API
金鑰可從 Google AI Studio 取得。