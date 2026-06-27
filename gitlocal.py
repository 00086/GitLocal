import os
import sys
import argparse
import hashlib
import requests

def get_server_url():
    """動態取得伺服器 URL"""
    config_file = '.gitlocal'
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            url = f.read().strip()
            if url: return url

    env_url = os.environ.get('GITLOCAL_SERVER_URL')
    if env_url: return env_url

    print("⚠️  警告：未設定伺服器位址！")
    print("💡 建議做法：在當前資料夾建立一個名為 '.gitlocal' 的純文字檔，寫入伺服器網址 (例如 http://192.168.1.100:5001)。")
    print("🔌 系統將暫時退回預設值：http://127.0.0.1:5001\n")
    return "http://127.0.0.1:5001"

SERVER_URL = get_server_url()

# ==========================================
# 工具函式區塊
# ==========================================
def get_local_hash(file_path):
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        sha1.update(f.read())
    return sha1.hexdigest()

def get_server_manifest(repo_name):
    url = f"{SERVER_URL}/api/repo/{repo_name}/manifest"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 無法連線至伺服器 ({SERVER_URL}): {e}")
        sys.exit(1)

def simple_post(url, data, success_msg, loading_msg="⏳ 執行中..."):
    """共用的 POST 請求處理器"""
    print(loading_msg)
    try:
        response = requests.post(url, data=data, allow_redirects=True)
        if response.ok:
            print(f"🎉 {success_msg}")
        else:
            print(f"❌ 執行失敗 ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")

# ==========================================
# 核心指令執行區塊
# ==========================================
def command_status(repo_name, work_dir):
    """🌟 優化版：以伺服器清單為基準，避免無謂讀取本地未上傳檔案"""
    abs_work_dir = os.path.abspath(work_dir)
    print(f"🔍 正在與伺服器比對 [{repo_name}] 的檔案狀態...")
    print(f"📂 當前掃描之本地目錄: {abs_work_dir}")
    server_manifest = get_server_manifest(repo_name)
    
    new_files = []
    modified_files = []
    local_tracked_files = set()
    
    ignore_dirs = {'.git', '__pycache__', 'my_git_repos', 'venv', 'env', '.vscode', '.idea', 'node_modules'}
    
    # 掃描本地目錄結構
    for root, dirs, files in os.walk(work_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            full_p = os.path.join(root, f)
            rel_p = os.path.relpath(full_p, work_dir).replace('\\', '/')
            
            # 忽略工具本身的檔案
            if rel_p in ['gitlocal.py', '.gitlocal', 'gitlocal.bat'] and rel_p not in server_manifest:
                continue 
                
            local_tracked_files.add(rel_p)
            
            # 🌟 核心優比對邏輯 (由伺服器清單主導)
            if rel_p not in server_manifest:
                # 1. 伺服器沒有這個路徑 -> 肯定是新檔案，直接記錄，完全不讀取/不計算 Hash！
                new_files.append(rel_p)
            else:
                # 2. 伺服器有這個路徑 -> 只有這時候才需要算 Hash 比對內容是否有修改！
                if get_local_hash(full_p) != server_manifest[rel_p]:
                    modified_files.append(rel_p)
            
    # 3. 檢查遠端有、但本地沒被掃描到的檔案 -> 已刪除檔案
    deleted_files = [rel_p for rel_p in server_manifest.keys() if rel_p not in local_tracked_files]
            
    # 美化輸出結果
    if not new_files and not modified_files and not deleted_files:
        print("✅ 工作目錄非常乾淨！與遠端伺服器 100% 完全同步。")
        return
        
    print("\n📋 遠端分支與本地工作目錄之差異狀態：")
    if new_files:
        print("\n➕ 未追蹤的新檔案 (伺服器上尚不存在)：")
        for f in new_files: print(f"   [新檔案]  {f}")
    if modified_files:
        print("\n✏️ 已修改的檔案 (內容與伺服器不一致)：")
        for f in modified_files: print(f"   [已修改]  {f}")
    if deleted_files:
        print("\n❌ 本地已刪除的檔案 (伺服器上仍然存在)：")
        for f in deleted_files: print(f"   [已刪除]  {f}")
            
    print("\n💡 提示：您可以使用 `commit` 指令上傳上述變更，或保持原樣繼續開發。")

def command_commit(repo_name, message, targets, work_dir):
    """🌟 優化版：智慧過濾上傳，同樣避免無謂計算未追蹤檔案的 Hash"""
    abs_work_dir = os.path.abspath(work_dir)
    print(f"🔍 正在與伺服器比對 [{repo_name}] 的檔案狀態...")
    print(f"📂 當前掃描之本地目錄: {abs_work_dir}")
    server_manifest = get_server_manifest(repo_name)
    files_to_upload = []
    
    ignore_dirs = {'.git', '__pycache__', 'my_git_repos', 'venv', 'env', '.vscode', '.idea', 'node_modules'}
    
    for target in targets:
        if target == '.':
            for root, dirs, files in os.walk(work_dir):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for f in files:
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, work_dir).replace('\\', '/')
                    
                    if rel_p in ['gitlocal.py', '.gitlocal', 'gitlocal.bat'] and rel_p not in server_manifest:
                        continue 
                    
                    # 🌟 智慧過濾比對
                    if rel_p not in server_manifest:
                        # 新檔案註定要上傳，無需浪費 CPU 算 Hash 來比對
                        files_to_upload.append(rel_p)
                    else:
                        # 既有檔案，才需要算 Hash 確認是否有被修改過
                        if get_local_hash(full_p) != server_manifest[rel_p]:
                            files_to_upload.append(rel_p)
        else:
            # 處理指定的單一檔案
            target_full = os.path.join(work_dir, target)
            if os.path.isfile(target_full):
                rel_p = os.path.relpath(target_full, work_dir).replace('\\', '/')
                if rel_p not in server_manifest:
                    files_to_upload.append(rel_p)
                else:
                    if get_local_hash(target_full) != server_manifest[rel_p]:
                        files_to_upload.append(rel_p)
            else:
                print(f"⚠️ 警告: 找不到檔案 '{target}'，將跳過。")

    if not files_to_upload:
        print("✅ 沒有偵測到任何變更，無需 Commit。")
        return

    print(f"📦 偵測到 {len(files_to_upload)} 個檔案變更：")
    for f in files_to_upload: print(f"   - {f}")

    multi_line_msg = f"{message}\n\n🚀 透過 GitLocal CLI 自動提交\n📦 異動檔案清單 ({len(files_to_upload)} 個)：\n"
    for f in files_to_upload: multi_line_msg += f"  - {f}\n"

    url = f"{SERVER_URL}/repo/{repo_name}/batch_upload"
    data = {'message': multi_line_msg.strip()}
    
    files = []
    file_handles = [] 
    for file_path in files_to_upload:
        f = open(file_path, 'rb')
        file_handles.append(f)
        files.append(('files', (file_path, f)))

    print("🚀 正在提交到伺服器...")
    try:
        response = requests.post(url, data=data, files=files)
        if response.ok: print(f"🎉 提交成功！")
        else: print(f"❌ 伺服器錯誤 ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ 上傳失敗: {e}")
    finally:
        for f in file_handles: f.close()

def command_branch(repo_name, branch_name, commit_sha):
    url = f"{SERVER_URL}/repo/{repo_name}/branch/create"
    data = {'branch_name': branch_name}
    if commit_sha: data['commit_sha'] = commit_sha
    msg = f"已成功建立並切換至新分支 [{branch_name}]" + (f" (從 {commit_sha[:7]} 起點)" if commit_sha else "")
    simple_post(url, data, msg, f"🌱 正在建立分支 [{branch_name}]...")

def command_checkout(repo_name, branch_name):
    url = f"{SERVER_URL}/repo/{repo_name}/branch/switch"
    data = {'branch_name': branch_name}
    simple_post(url, data, f"已成功切換伺服器至 [{branch_name}] 分支！\n💡 提示：若需同步本地檔案，請搭配 `zip` 指令下載遠端最新進度。", f"🔄 正在切換伺服器分支至 [{branch_name}]...")

def command_delete_branch(repo_name, branch_name):
    url = f"{SERVER_URL}/repo/{repo_name}/branch/delete"
    data = {'branch_name': branch_name}
    simple_post(url, data, f"已永久刪除分支 [{branch_name}]！", f"🗑️ 正在刪除分支 [{branch_name}]...")

def command_merge(repo_name, source_branch):
    url = f"{SERVER_URL}/repo/{repo_name}/branch/merge"
    data = {'source_branch': source_branch}
    simple_post(url, data, f"已成功將 [{source_branch}] 合併至伺服器當前分支，並產生 Y 型匯流 Commit！", f"🔀 正在執行分支合併...")

def command_push(repo_name, remote_url, token):
    url = f"{SERVER_URL}/repo/{repo_name}/push"
    data = {'remote_url': remote_url, 'token': token}
    simple_post(url, data, f"推送成功！已完美同步至 GitHub。", f"☁️ 正在連線至 GitHub 推送程式碼，請稍候...")

def command_get_file(repo_name, commit_sha, file_path, save_path):
    url = f"{SERVER_URL}/repo/{repo_name}/download/{commit_sha}/{file_path}"
    print(f"📥 正在下載單一檔案 ({commit_sha[:7]} -> {file_path})...")
    try:
        response = requests.get(url, stream=True)
        if response.ok:
            os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            print(f"🎉 檔案下載完成！已儲存至: {save_path}")
        else:
            print(f"❌ 下載失敗 ({response.status_code}): 找不到該檔案或伺服器錯誤。")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")

def command_zip(repo_name, commit_sha, save_path):
    url = f"{SERVER_URL}/repo/{repo_name}/download_zip/{commit_sha}"
    print(f"📦 正在打包遠端專案 ({commit_sha[:7]})...")
    try:
        response = requests.get(url, stream=True)
        if response.ok:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
            print(f"🎉 專案打包下載完成！已儲存至: {save_path}")
        else:
            print(f"❌ 下載失敗 ({response.status_code}): 找不到該 Commit 紀錄。")
    except Exception as e:
        print(f"❌ 連線失敗: {e}")

# ==========================================
# 程式入口與說明選單
# ==========================================
if __name__ == '__main__':
    # 🌟 說明選單更新：將 status 排在第一位
    custom_help_text = """
================================================================================
 🚀 GitLocal 遠端指令列工具 (Full API Client)
================================================================================
 基本語法:
   python gitlocal.py <專案名稱> <指令> [參數]

 🛠️ [基礎操作] 
  (1) status        : 🌟 純粹查看本地與遠端伺服器的檔案差異狀態 (不上傳)
      語法: python gitlocal.py <專案> status
      範例: python gitlocal.py my_repo status

  (2) commit        : 智慧比對並上傳變更的檔案到伺服器
      語法: python gitlocal.py <專案> commit -m "<說明>" <檔案或.>
      範例: python gitlocal.py my_repo commit -m "更新首頁" .

 🌿 [分支管理]
  (3) branch        : 建立新分支 (可選定特定歷史起點)
      語法: python gitlocal.py <專案> branch <新分支名> [commit_sha]
      範例: python gitlocal.py my_repo branch feature-3d
      
  (4) checkout      : 讓伺服器切換工作目錄至指定分支
      語法: python gitlocal.py <專案> checkout <分支名>
      範例: python gitlocal.py my_repo checkout master

  (5) delete-branch : 刪除伺服器上的分支
      語法: python gitlocal.py <專案> delete-branch <分支名>
      範例: python gitlocal.py my_repo delete-branch test-bug

  (6) merge         : 將來源分支合併至當前分支 (產生 Y 型匯流)
      語法: python gitlocal.py <專案> merge <來源分支名>
      範例: python gitlocal.py my_repo merge feature-3d

 ☁️ [雲端與下載]
  (7) push          : 將伺服器進度推送到 GitHub
      語法: python gitlocal.py <專案> push <遠端網址> <PAT_Token>
      範例: python gitlocal.py my_repo push https://github.com/a/b.git ghp_123

  (8) get-file      : 下載歷史紀錄中的「單一檔案」
      語法: python gitlocal.py <專案> get-file <commit_sha> <檔案路徑> <存檔路徑>
      範例: python gitlocal.py my_repo get-file 650195a app.py ./old_app.py

  (9) zip           : 下載特定歷史點的「完整專案打包檔」
      語法: python gitlocal.py <專案> zip <commit_sha> <儲存檔名.zip>
      範例: python gitlocal.py my_repo zip cdd0f39 backup.zip
================================================================================
    """

    if len(sys.argv) == 1 or sys.argv[1] in ['-h', '--help']:
        print(custom_help_text)
        sys.exit(0)

    if len(sys.argv) == 2:
        print(f"❌ 錯誤：您指定了專案「{sys.argv[1]}」，但忘記輸入指令！\n")
        print(custom_help_text)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="GitLocal 遠端指令列工具", add_help=False)
    parser.add_argument("repo", help="專案名稱")
    subparsers = parser.add_subparsers(dest="command")

    # 1. Status (🌟 加入專屬的 -d)
    p_status = subparsers.add_parser("status")
    p_status.add_argument("-d", "--dir", default=".", help="指定本地專案的資料夾路徑 (預設為當前目錄)")

    # 2. Commit (🌟 加入專屬的 -d)
    p_commit = subparsers.add_parser("commit")
    p_commit.add_argument("-m", "--message", required=True)
    p_commit.add_argument("targets", nargs='+')
    p_commit.add_argument("-d", "--dir", default=".", help="指定本地專案的資料夾路徑 (預設為當前目錄)")

    # 3. Branch
    p_branch = subparsers.add_parser("branch")
    p_branch.add_argument("branch_name")
    p_branch.add_argument("commit_sha", nargs='?', default=None)

    # 4. Checkout
    p_checkout = subparsers.add_parser("checkout")
    p_checkout.add_argument("branch_name")

    # 5. Delete Branch
    p_del_branch = subparsers.add_parser("delete-branch")
    p_del_branch.add_argument("branch_name")

    # 6. Merge
    p_merge = subparsers.add_parser("merge")
    p_merge.add_argument("source_branch")

    # 7. Push
    p_push = subparsers.add_parser("push")
    p_push.add_argument("remote_url")
    p_push.add_argument("token")

    # 8. Get File
    p_get = subparsers.add_parser("get-file")
    p_get.add_argument("commit_sha")
    p_get.add_argument("file_path")
    p_get.add_argument("save_path")

    # 9. Zip
    p_zip = subparsers.add_parser("zip")
    p_zip.add_argument("commit_sha")
    p_zip.add_argument("save_path")

    args = parser.parse_args()

    # 路由執行區塊 (更新這兩行)
    if args.command == "status": command_status(args.repo, args.dir)
    elif args.command == "commit": command_commit(args.repo, args.message, args.targets, args.dir)
    elif args.command == "branch": command_branch(args.repo, args.branch_name, args.commit_sha)
    elif args.command == "checkout": command_checkout(args.repo, args.branch_name)
    elif args.command == "delete-branch": command_delete_branch(args.repo, args.branch_name)
    elif args.command == "merge": command_merge(args.repo, args.source_branch)
    elif args.command == "push": command_push(args.repo, args.remote_url, args.token)
    elif args.command == "get-file": command_get_file(args.repo, args.commit_sha, args.file_path, args.save_path)
    elif args.command == "zip": command_zip(args.repo, args.commit_sha, args.save_path)
    else:
        print("❌ 未知的指令！請執行 `python gitlocal.py` 查看可用清單。")