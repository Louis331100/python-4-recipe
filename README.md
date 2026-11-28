# 宿舍食譜助手

使用 Streamlit、Gemini API 生成食譜與料理圖片。

生成食譜後會切換到獨立的結果畫面，可重新生成，或返回食材選擇；返回時會保留原本選項。
食材選擇畫面右上方的「隨機食材挑戰」會隨機選出 6～10 種食材或調味料，其中至少 4 種為食材。

## 安裝與執行

### Windows 一鍵啓動（建議）

在檔案總管中雙擊 `start_app.vbs`。啓動器會隱藏終端，並以獨立的 Edge App 視窗開啓程式；關閉該視窗後，伺服器會自動結束。

首次啓動會：
1. 建立 `.venv` 虛擬環境。
2. 安裝 `requirements.txt` 中的套件。
3. 以密碼欄位詢問 Gemini API 金鑰。
4. 啓動 App 並開啓獨立瀏覽器視窗。

金鑰只保存在啓動器的程序環境中，不會寫入專案檔案。關閉視窗後，下次啓動會再次詢問；若已設定 `GEMINI_API_KEY` 環境變數，啓動器會直接使用該值。

也可以雙擊 `start_app.bat` 啓動；它會呼叫相同的隱藏式啓動器。

也可在終端機執行：

```powershell
wscript.exe .\start_app.vbs
```

### 手動執行

手動執行時伺服器會持續執行，需在終端機按 `Ctrl+C` 停止；只有使用上方的啓動器才會在關閉 Edge App 視窗時自動結束。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:GEMINI_API_KEY="你的 Gemini API 金鑰"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Gemini API 金鑰可從 [Google AI Studio](https://aistudio.google.com/apikey) 取得。
若需要更換模型，可設定 `GEMINI_MODEL`（食譜）或 `GEMINI_IMAGE_MODEL`（圖片）。
選單資料放在 `menu.json`。肉類可先選肉種再勾選型態；也可手動輸入食材。
