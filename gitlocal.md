# 🚀 GitLocal 遠端指令列工具 (CLI Client) 完整使用指南

GitLocal 是一款無須依賴官方 Git 程式的遠端版本控制終端機客戶端。透過本工具，您可以在任何開發機（本地端）優雅地遙控、比對並推送程式碼至 GitLocal 伺服器。

## ⚙️ 基本語法

```bash
python gitlocal.py <專案名稱> <指令> [參數]

```

*(💡 提示：若您已完成本文下方的 Alias 設定，可直接將 `python gitlocal.py` 替換為 `gitlocal` 以加速操作。)*

---

## 🛠️ [基礎操作]

### 1. status

純粹查看本地工作目錄與遠端伺服器的檔案差異狀態，**不會上傳任何檔案**。可藉此確認哪些檔案被新增、修改或刪除。

* **語法**：`gitlocal <專案> status [-d 目錄]`
* **範例**：
```bash
gitlocal my_repo status

```



### 2. commit

智慧比對本地端與伺服器端的差異，並將變更的檔案精準上傳到伺服器。

* **語法**：`gitlocal <專案> commit -m "<說明>" <檔案或.> [-d 目錄]`
* **範例**：
* 單檔上傳：`gitlocal my_repo commit -m "更新首頁" templates/index.html`
* 全目錄智慧比對：`gitlocal my_repo commit -m "大改版" .`



---

## 🌿 [分支管理]

### 3. branch

建立新分支。您可以從當前最新進度建立，也可以指定從某個歷史節點建立。

* **語法**：`gitlocal <專案> branch <新分支名> [commit_sha]`
* **範例**：
* 從目前進度建立：`gitlocal my_repo branch feature-3d`
* 從歷史點建立：`gitlocal my_repo branch old-ui 650195a`



### 4. checkout

讓伺服器的工作目錄切換至指定分支。

* **語法**：`gitlocal <專案> checkout <分支名>`
* **範例**：
```bash
gitlocal my_repo checkout master

```



### 5. delete-branch

永久刪除伺服器上的特定分支。

* **語法**：`gitlocal <專案> delete-branch <分支名>`
* **範例**：
```bash
gitlocal my_repo delete-branch test-bug

```



### 6. merge

將來源分支的進度合併至當前分支，系統會自動處理檔案覆蓋並產生一個 Y 型匯流 Commit。

* **語法**：`gitlocal <專案> merge <來源分支名>`
* **範例**：
```bash
gitlocal my_repo merge feature-3d

```



---

## ☁️ [雲端與下載]

### 7. push

將伺服器目前的進度與歷史紀錄，推送到遠端的 GitHub 倉庫。

* **語法**：`gitlocal <專案> push <遠端網址> <PAT_Token>`
* **範例**：
```bash
gitlocal my_repo push https://github.com/user/repo.git ghp_123456789...

```



### 8. get-file

穿越時空，下載歷史紀錄中的「單一檔案」到本地端。

* **語法**：`gitlocal <專案> get-file <commit_sha> <伺服器檔案路徑> <存檔路徑>`
* **範例**：
```bash
gitlocal my_repo get-file 650195a app.py ./old_app.py

```



### 9. zip

下載特定歷史時間點的「完整專案打包檔 (ZIP)」。

* **語法**：`gitlocal <專案> zip <commit_sha> <儲存檔名.zip>`
* **範例**：
```bash
gitlocal my_repo zip cdd0f39 backup_v1.zip

```



---

## 💻 環境設定與 Alias (將指令全域化)

為了提升操作效率，建議將 `gitlocal.py` 設定為系統的全域指令（Alias），讓您在任何資料夾都能直接呼叫 `gitlocal`。

### 🐧 Linux / macOS 環境設定

在 Linux 底下，我們通常會將 alias 寫入使用者的終端機設定檔（如 `~/.bashrc` 或 `~/.zshrc`），這樣每次打開終端機都會自動生效。

**步驟：**

1. 找出 `gitlocal.py` 在您電腦上的「絕對路徑」（例如 `/home/user/scripts/gitlocal.py`）。
2. 打開終端機，執行以下指令將 alias 寫入設定檔（請自行替換路徑）：
```bash
# 如果您使用的是 Bash (大多數 Linux 預設)
echo "alias gitlocal='python3 /您的/絕對路徑/gitlocal.py'" >> ~/.bashrc
source ~/.bashrc

# 如果您使用的是 Zsh (macOS 預設或進階 Linux 使用者)
echo "alias gitlocal='python3 /您的/絕對路徑/gitlocal.py'" >> ~/.zshrc
source ~/.zshrc

```



**✅ 完成測試：**
現在您在任何資料夾底下，只要直接輸入：

```bash
gitlocal my_project commit -m "更新" .

```

系統就會自動幫您代入 `python3 /.../gitlocal.py` 並順利執行！

---

### 🪟 Windows 環境設定 (全域全端通吃 Alias)

Windows 的終端機較為複雜（分為傳統 CMD、PowerShell 等）。**最穩健、且能同時讓 CMD、PowerShell 甚至 VS Code 內建終端機都看懂的專業做法，是建立一個「批次檔 (.bat)」並放入系統路徑 (PATH) 中。**

#### 🏆 終極推薦做法：建立 `.bat` 執行檔 + PATH

**步驟 1：建立批次檔 (Batch Wrapper)**

1. 在存放 `gitlocal.py` 的同一個資料夾內，建立一個新的純文字檔，命名為 **`gitlocal.bat`**。
2. 用記事本打開它，貼入以下兩行程式碼：
```bat
@echo off
python "C:\您的\絕對路徑\gitlocal.py" %*

```


*(註：`%*` 的意思是把您在終端機打的所有後續參數，原封不動地傳遞給 Python 腳本)*

**步驟 2：將資料夾加入系統環境變數 (PATH)**

1. 按下鍵盤 `Win + S`，搜尋「**編輯系統環境變數**」並打開。
2. 點擊右下角的「**環境變數(N)...**」。
3. 在上半部「使用者的變數」中，找到 `Path`，點擊「**編輯**」。
4. 點擊「**新增**」，然後把存放 `gitlocal.bat` 的「資料夾路徑」貼上去（例如 `C:\my_scripts\`）。
5. 一路按「確定」關閉所有視窗。

**✅ 完成測試：**
重新打開您的 Windows 命令提示字元 (CMD) 或 PowerShell，在任何路徑下直接輸入：

```cmd
gitlocal

```

系統就會成功執行並跳出完整的指令說明選單！

#### 💡 備用做法：僅限 PowerShell 的 Alias 設定

*(注意：此方法設定的 Alias **無法**在 CMD 中使用)*

1. 以系統管理員身分打開 PowerShell。
2. 輸入以下指令建立或打開設定檔：
```powershell
if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
notepad $PROFILE

```


3. 在彈出的記事本中，貼上這個 Function：
```powershell
function gitlocal {
    python "C:\您的\絕對路徑\gitlocal.py" $args
}

```


4. 存檔並重開 PowerShell 即可生效。