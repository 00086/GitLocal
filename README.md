# 🗂️ GitLocal - 輕量級本地 Git 視覺化管理與高效能 CLI 生態系統

GitLocal 是一個基於 Python 與 Flask 打造的輕量級、無依賴（無需安裝系統 Git）的本地端 Git 倉庫管理系統。本專案不僅提供直覺、現代化的 Web 視覺化操作介面，更配備了專屬的 **高效能遠端指令列工具 (CLI Client)**，讓開發者在終端機與網頁之間無縫穿梭，享受流暢的版本控制體驗。

---

## ✨ 核心特色 (Features)

### 1. 視覺化版本控制 (Web UI)
* **歷史時光機**：清晰的 Commit 紀錄列表，支援單一檔案或整個專案 (ZIP) 的歷史版本下載。
* **專業級 Diff 差異比對**：內建 Highlight.js 語法高亮，精準標示程式碼增刪（防複製 `+` `-` 符號設計）。
* **平行宇宙 (分支系統)**：一鍵建立、切換分支，並支援「雙親節點合併 (Merge)」，在網頁上視覺化呈現分支匯流。
* **Git 樹狀圖**：整合 GitGraph.js，完美渲染出拓撲結構，直覺呈現複雜的分支交錯與歷史脈絡。

### 2. 強大的檔案管理與內建 IDE
* **全端檔案總管**：支援多層級資料夾瀏覽、拖曳式批次上傳 (Staging 暫存區預覽)。
* **CodeMirror 編輯器**：支援 Python、JavaScript、HTML/CSS 等多語言語法高亮、行號顯示與快捷鍵，網頁即是工作區。
* **即時 Markdown 預覽**：編輯 `.md` 檔案時可一鍵切換至優雅的 GitHub 樣式排版預覽模式。
* **二進位檔案防護**：優雅攔截 Office 文件、圖片等無法進行文字比對的特殊檔案，提供安全備份與無損下載。

### 3. 🚀 遠端指令列工具 (CLI Client - gitlocal)
* **全功能遙控**：無須開啟網頁，即可在本地開發機直接對遠端伺服器下達 `status`、`commit`、`branch`、`checkout`、`merge`、`push` 等 9 大核心指令。
* **智慧層級化組態 (.gitlocal)**：支援專案級設定檔、系統環境變數（`GITLOCAL_SERVER_URL`）與防呆預設值，擺脫硬編碼 IP 的災難。
* **自動化多行備註**：執行 CLI `commit` 時，工具會自動將受異動的檔案清單拼接成多行詳細內容塞入備註，網頁端一鍵展開、歷歷在目。

### 4. ⚡ 伺服器清單優先比對法 (極致效能優化)
* **顛覆傳統的 Diff 引擎**：本系統的 CLI 客戶端採用**「伺服器清單主導」**機制。掃描本地時，若發現檔案路徑不在遠端清單內，直接判定為新檔案，**絕對不讀取實體檔案、不浪費 CPU 計算雜湊值 (Hash)**。
* **極低硬碟 I/O 損耗**：只有當檔案確實存在於伺服器上，為了確認內容是否修改，才進行輕量雜湊計算。即使本地堆積了數 GB 的未追蹤垃圾檔案，比對依然能在毫秒內瞬間完成！

---

## 🛠️ 系統架構 (Architecture)

### 後端技術棧 (Backend Server)
* **核心框架**：[Flask](https://flask.palletsprojects.com/) (輕量級 Web 框架)
* **伺服器引擎**：[Waitress](https://docs.pylonsproject.org/projects/waitress/en/stable/) (生產級 WSGI 伺服器，提供安全、多線程並發能力)
* **Git 底層引擎**：[Dulwich](https://www.dulwich.io/) (純 Python 實作的 Git 函式庫，**不依賴作業系統的 Git 執行檔**)
* **線程安全機制**：實作全域 `threading.Lock()` 互斥鎖，阻絕 Waitress 多線程並發寫入時造成的 `.git/index.lock` 崩潰。

### 客戶端技術棧 (CLI Client)
* **網路通訊**：`requests` (負責輕量化的 JSON Manifest 握手與二進位串流傳輸)
* **參數解析**：`argparse` (內建防呆語法攔截與客製化進階範例選單)
* **封裝工具**：`PyInstaller` (支援編譯為無 Python 環境相容的單一獨立二進位執行檔)

---

## 📂 專案結構 (Directory Structure)

```text
GitLocal/
├── app.py               # 伺服器進入點 (啟動 Waitress 服務)
├── routes.py            # 前端網頁 API 路由與請求攔截器
├── database.py          # Git 核心操作邏輯 (Dulwich 封裝與線程鎖、Manifest 生成)
├── gitlocal.py          # 遠端指令列工具 (CLI 客戶端腳本)
├── .gitlocal            # (使用者自建) 存放遠端伺服器 URL 的純文字設定檔
├── my_git_repos/        # (伺服器自動生成) 所有本地 Git 倉庫的存放地
└── templates/           # 前端畫面模板 (Jinja2)
    ├── index.html       # 首頁 (倉庫清單)
    ├── repo.html        # 倉庫主頁 (檔案總管、歷史紀錄、分支管理)
    ├── edit.html        # 程式碼編輯器與 Markdown 預覽
    └── commit.html      # 歷史版本詳細差異 (Diff) 視窗

```

---

## 🚀 快速啟動 (Quick Start)

### 1. 啟動 GitLocal 伺服器 (B 電腦 / 伺服器端)

請確保伺服器端已安裝 Python 3.8+，執行以下指令：

```bash
pip install flask waitress dulwich
python app.py

```

打開瀏覽器，前往 `http://127.0.0.1:5001` 即可進入視覺化管理首頁。

### 2. 設定 CLI 客戶端 (A 電腦 / 開發機)

在您的實際開發專案資料夾根目錄下，建立一個名為 `.gitlocal` 的純文字檔，填入伺服器的實體網址：

```text
[http://192.168.1.100:5001](http://192.168.1.100:5001)

```

*(未設定時，系統將自動安全退回本機 `http://127.0.0.1:5001` 作為基準。)*

---

## 💻 CLI 指令完全手冊 (CLI Reference)

完成下方的 Alias 全域化設定後，您可以直接使用 `gitlocal` 指令。若未設定，請使用原生語法 `python gitlocal.py <專案名稱> <指令> [參數]`。

### 🛠️ [一、基礎操作]

#### 1. status (查看狀態)

純粹比對本地與伺服器的檔案差異狀態，**絕對不上傳任何資料**。

* **語法**：`gitlocal <專案> status [-d 目錄]`
* **範例**：`gitlocal snmp_topology status`

#### 2. commit (提交變更)

智慧比對差異並精準批次上傳。自動在網頁端留下多行異動履歷。

* **語法**：`gitlocal <專案> commit -m "<說明>" <檔案或.> [-d 目錄]`
* **範例 (全目錄自動比對)**：`gitlocal snmp_topology commit -m "修正路由" .`
* **範例 (單檔案精準提交)**：`gitlocal snmp_topology commit -m "改網頁" templates/index.html`

### 🌿 [二、分支管理]

#### 3. branch (建立分支)

建立平行宇宙。可選擇從最新進度建立，或指定 Commit SHA 進行歷史回溯建立。

* **語法**：`gitlocal <專案> branch <新分支名> [commit_sha]`
* **範例**：`gitlocal snmp_topology branch feature-3d`

#### 4. checkout (切換分支)

遙控伺服器的工作目錄切換至指定分支。

* **語法**：`gitlocal <專案> checkout <分支名>`
* **範例**：`gitlocal snmp_topology checkout master`

#### 5. delete-branch (刪除分支)

永久刪除伺服器上的特定分支（無法刪除當前使用中的分支）。

* **語法**：`gitlocal <專案> delete-branch <分支名>`
* **範例**：`gitlocal snmp_topology delete-branch test-bug`

#### 6. merge (合併分支)

將來源分支進度融合進當前分支，在樹狀圖上自動繪製出 Y 字型雙親節點。

* **語法**：`gitlocal <專案> merge <來源分支名>`
* **範例**：`gitlocal snmp_topology merge feature-3d`

### ☁️ [三、雲端同步與時空下載]

#### 7. push (同步至 GitHub)

安全地將伺服器進度推送到 GitHub 倉庫。記憶體直接授權，**不在伺服器磁碟留下個人 Token**。

* **語法**：`gitlocal <專案> push <遠端網址> <PAT_Token>`
* **範例**：`gitlocal snmp_topology push https://github.com/a/b.git ghp_123...`

#### 8. get-file (時空單檔下載)

單獨抽取、下載某個歷史 Commit 版本的「單一檔案」到本地指定位置。

* **語法**：`gitlocal <專案> get-file <commit_sha> <伺服器路徑> <本地路徑>`
* **範例**：`gitlocal snmp_topology get-file 650195a app.py ./old_app.py`

#### 9. zip (完整專案打包)

將指定歷史時間點的完整專案，打包為 ZIP 壓縮檔下載。

* **語法**：`gitlocal <專案> zip <commit_sha> <儲存檔名.zip>`
* **範例**：`gitlocal snmp_topology zip cdd0f39 backup.zip`

---

## ⚙️ 環境設定與 全域全端通吃 Alias

為了不需要每次都輸入冗長的 `python gitlocal.py`，請依照您的作業系統選用以下全域快捷設定：

### 🪟 Windows 環境設定 (🏆 推薦：批次檔 + PATH 終極做法)

*PowerShell 內部設定的 Alias 無法在傳統 CMD 或其他工具下使用。本做法是 Windows 下最完美的終極解決方案，能讓所有終端機（CMD、PowerShell、VS Code）都完美認得 `gitlocal` 指令。*

1. **建立批次檔 (Batch Wrapper)**：
在存放 `gitlocal.py` 的同一個資料夾內，建立一個新的純文字檔，命名為 **`gitlocal.bat`**，貼入以下代碼：
```bat
@echo off
python "C:\您的\絕對路徑\gitlocal.py" %*

```


*(💡 `%*` 能夠將您輸入的所有後續參數與備註，原封不動地傳遞給 Python 腳本。)*
2. **將資料夾加入系統環境變數 (PATH)**：
* 按下鍵盤 `Win + S`，搜尋「**編輯系統環境變數**」並打開。
* 點擊右下角的「**環境變數(N)...**」。
* 在上半部「使用者的變數」中，找到 **`Path`**，點擊「**編輯**」。
* 點擊「**新增**」，把存放 `gitlocal.bat` 的「資料夾路徑」貼上去（例如 `C:\my_scripts\`）。
* 一路按「確定」關閉所有視窗，並重開終端機即可生效！



### 🐧 Linux / macOS 環境設定

Linux/macOS 系統原生支援在 Shell 組態設定檔（如 `~/.bashrc` 或 `~/.zshrc`）中直接設定全域 Alias。

1. 打開終端機，依據您使用的 Shell 執行對應指令（請將路徑替換為 `gitlocal.py` 的絕對路徑）：
```bash
# 如果您使用的是 Bash (大多數 Linux 預設)
echo "alias gitlocal='python3 /您的/絕對路徑/gitlocal.py'" >> ~/.bashrc
source ~/.bashrc

# 如果您使用的是 Zsh (macOS 預設或進階 Linux 使用者)
echo "alias gitlocal='python3 /您的/絕對路徑/gitlocal.py'" >> ~/.zshrc
source ~/.zshrc

```



---

## 📦 獨立執行檔打包 (免 Python 環境發布)

如果您需要將 `gitlocal` 客戶端部署到完全沒有安裝 Python、沒有 `requests` 套件的乾淨機器上，可以使用 `PyInstaller` 將其編譯為純原生二進位檔案。

*注意：PyInstaller 不支援跨平台編譯。若要產生 `.exe` 請在 Windows 上打包；若要產生 Linux 二進位檔請在 Linux 上打包。*

1. 安裝打包工具：
```bash
pip install pyinstaller requests

```


2. 執行單一檔案極簡編譯（將直譯器與依賴庫壓縮進單一檔案）：
```bash
pyinstaller --onefile gitlocal.py

```


3. 打包完成後，走進自動生成的 **`dist/`** 資料夾：
* **Windows**：獲得 **`gitlocal.exe`**。直接將它放入前文設定好的 `PATH` 資料夾，即可取代並刪除舊的 `.bat` 檔。
* **Linux**：獲得 **`gitlocal`**。賦予權限並移動至公共目錄即可全域盲打：
```bash
chmod +x dist/gitlocal
sudo mv dist/gitlocal /usr/local/bin/

```





---

## 📄 授權條款 (License)

本專案採用 **[MIT 授權條款](https://www.google.com/search?q=LICENSE)** 進行開源授權。您可以自由地複製、修改、分發及商業化使用本專案，唯須在所有副本中包含原作者的版權聲明與許可聲明。
``
