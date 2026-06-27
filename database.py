import os
import time
import datetime
import re
import threading  # 🌟 確保 Waitress 多線程進來時，Git 寫入安全排隊
from dulwich.repo import Repo
from dulwich.patch import write_tree_diff
from io import BytesIO
from dulwich import porcelain 
from dulwich.diff_tree import tree_changes
import zipfile
import shutil
from dulwich.objects import Commit
import hashlib

REPOS_DIR = os.path.abspath("./my_git_repos")

# 🌟 全域 Git 互斥鎖，阻絕多線程同時寫入造成的 index.lock 崩潰
git_lock = threading.Lock()

# 🌟 核心防禦：自動化建立主資料夾，exist_ok=True 確保跨平台與多線程安全
os.makedirs(REPOS_DIR, exist_ok=True)

def get_all_repositories():
    repos = []
    if os.path.exists(REPOS_DIR):
        for name in os.listdir(REPOS_DIR):
            path = os.path.join(REPOS_DIR, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, '.git')):
                repos.append(name)
    return repos

def get_repo_path(repo_name):
    return os.path.join(REPOS_DIR, repo_name)

def _clean_path(path_val):
    if path_val is None:
        return ""
    if isinstance(path_val, bytes):
        s = path_val.decode('utf-8', errors='replace')
    else:
        s = str(path_val)
    
    if s.startswith("b'") and s.endswith("'"):
        s = s[2:-1]
    elif s.startswith('b"') and s.endswith('"'):
        s = s[2:-1]
        
    return s.replace('\\', '/').lstrip('/')

def _clean_message(msg):
    if isinstance(msg, bytes):
        msg = msg.decode('utf-8', errors='replace')
    msg = re.sub(r"b'([^']+)'", r"\1", msg)
    msg = re.sub(r'b"([^"]+)"', r"\1", msg)
    return msg.strip()

def get_repo_details(repo_name):
    """ 獲取單一倉庫的 Commit 紀錄與檔案列表 (全域分支樹升級版) """
    path = get_repo_path(repo_name)
    if not os.path.exists(path):
        return None
        
    repo = Repo(path)
    commits_data = []      # 🌟 專屬表格用 (確保只顯示當前分支，不混入其他分支)
    graph_commits = []     # 🌟 專屬樹狀圖用 (包含全域分支拓撲)
    
    if len(repo.refs.keys()) > 0:
        # --- 1. 讀取「當前分支」歷史 (修復表格混亂) ---
        try:
            walker = repo.get_walker(max_entries=100)
            for entry in walker:
                commit = entry.commit
                changed_files = []
                try:
                    if commit.parents:
                        parent_tree = repo[commit.parents[0]].tree
                        changes = tree_changes(repo.object_store, parent_tree, commit.tree)
                        for change in changes:
                            new_entry = getattr(change, 'new', None)
                            old_entry = getattr(change, 'old', None)
                            path_bytes = getattr(new_entry, 'path', None) or getattr(old_entry, 'path', None)
                            if path_bytes:
                                clean_p = _clean_path(path_bytes)
                                if clean_p and clean_p not in changed_files:
                                    changed_files.append(clean_p)
                    else:
                        for tree_entry in repo.object_store.iter_tree_contents(commit.tree):
                            clean_p = _clean_path(tree_entry.path)
                            if clean_p and clean_p not in changed_files:
                                changed_files.append(clean_p)
                except Exception:
                    pass

                commits_data.append({
                    "hexsha": commit.id.decode('ascii') if isinstance(commit.id, bytes) else str(commit.id),
                    "message": _clean_message(commit.message),
                    "time": datetime.datetime.fromtimestamp(commit.commit_time).strftime('%Y-%m-%d %H:%M:%S'),
                    "files": changed_files,
                    "parents": [p.decode('ascii') for p in commit.parents]
                })
        except Exception as e:
            print(f"❌ 獲取當前分支歷史失敗: {e}")

        # --- 2. 讀取「全域分支」歷史 (給 Git 樹狀圖專用) ---
        try:
            walk_includes = [repo.refs[ref] for ref in repo.refs.keys() if ref.startswith(b'refs/heads/')]
            if walk_includes:
                all_walker = repo.get_walker(include=walk_includes, max_entries=100)
                for entry in all_walker:
                    c = entry.commit
                    graph_commits.append({
                        "hexsha": c.id.decode('ascii') if isinstance(c.id, bytes) else str(c.id),
                        "message": _clean_message(c.message),
                        "time": datetime.datetime.fromtimestamp(c.commit_time).strftime('%Y-%m-%d %H:%M:%S'),
                        "parents": [p.decode('ascii') for p in c.parents]
                    })
        except Exception as e:
            print(f"❌ 獲取全域分支歷史失敗: {e}")
    else:
        print(f"ℹ️ 倉庫 {repo_name} 目前為空 (無任何 Ref)，跳過 Commit 解析。")

    # 獲取當前實體檔案列表 (index)
    files = []
    try:
        index = repo.open_index()
        for file_path_bytes in index:
            clean_rel_path = _clean_path(file_path_bytes)
            full_path = os.path.join(path, clean_rel_path)
            
            if os.path.exists(full_path):
                # 獲取檔案最後修改時間
                mtime = os.path.getmtime(full_path)
                dt = datetime.datetime.fromtimestamp(mtime)
                exact_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # 計算相對時間
                diff = datetime.datetime.now() - dt
                if diff.days > 0: time_ago = f"{diff.days} 天前"
                elif diff.seconds >= 3600: time_ago = f"{diff.seconds // 3600} 小時前"
                elif diff.seconds >= 60: time_ago = f"{diff.seconds // 60} 分鐘前"
                else: time_ago = f"{diff.seconds} 秒前"
                    
                # 獲取該檔案的最後一次 commit 訊息
                try:
                    walker = repo.get_walker(paths=[file_path_bytes], max_entries=1)
                    commit_obj = next(iter(walker)).commit
                    msg = _clean_message(commit_obj.message)
                    hexsha = commit_obj.id.decode('utf-8') if isinstance(commit_obj.id, bytes) else str(commit_obj.id)
                except Exception:
                    msg = f"Update {clean_rel_path}"
                    hexsha = ""

                files.append({
                    "path": clean_rel_path,
                    "time": f"{time_ago} ({exact_time})",
                    "message": msg,
                    "hexsha": hexsha
                })
    except Exception as e:
        print(f"❌ 讀取檔案列表錯誤: {e}")

    # 加入分支資訊並回傳
    branches = get_branches(repo_name)
    # 🌟 將 graph_commits 一起回傳給前端
    return {"commits": commits_data, "graph_commits": graph_commits, "files": files, "branches": branches}

def get_commit_diff(repo_name, commit_sha):
    path = get_repo_path(repo_name)
    repo = Repo(path)
    sha_bytes = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha
    
    if sha_bytes not in repo:
        return None

    commit = repo[sha_bytes]
    diffs = ""
    
    if len(commit.parents) > 0:
        parent_commit = repo[commit.parents[0]]
        out = BytesIO()
        write_tree_diff(out, repo.object_store, parent_commit.tree, commit.tree)
        diffs = out.getvalue().decode('utf-8', errors='ignore')
    else:
        diffs = "這是首次提交 (Initial Commit)，沒有變更差異。"

    return {
        "commit": {
            "hexsha": commit.id.decode('utf-8') if isinstance(commit.id, bytes) else str(commit.id),
            "message": _clean_message(commit.message),
            "author": commit.author.decode('utf-8', errors='ignore') if isinstance(commit.author, bytes) else str(commit.author),
            "time": datetime.datetime.fromtimestamp(commit.commit_time).strftime('%Y-%m-%d %H:%M:%S')
        },
        "diffs": diffs
    }

# ================= CRUD 安全排隊區塊 =================
def create_new_repo(repo_name):
    with git_lock:
        path = get_repo_path(repo_name)
        # 🌟 同樣加上 exist_ok=True，防呆且更簡潔
        os.makedirs(path, exist_ok=True)
        porcelain.init(path)

def get_file_content(repo_name, file_path):
    path = get_repo_path(repo_name)
    full_path = os.path.join(path, file_path)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    return ""

def write_and_commit(repo_name, file_path, content, message):
    with git_lock:
        repo_dir = get_repo_path(repo_name)
        cleanup_lock_files(repo_dir)
        clean_p = _clean_path(file_path)
        full_path = os.path.join(repo_dir, clean_p)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)

        porcelain.add(repo_dir, paths=[clean_p])
        porcelain.commit(repo_dir, message=message.encode('utf-8'), author=b"Web User <web@local.git>")

def delete_and_commit(repo_name, file_path):
    with git_lock:
        repo_dir = get_repo_path(repo_name)
        cleanup_lock_files(repo_dir)
        clean_p = _clean_path(file_path)
        
        # 1. 執行 git rm
        porcelain.rm(repo_dir, paths=[clean_p])
            
        # 2. 強制 commit 刪除行為，這樣在歷史紀錄才看得到「刪除檔名」的項目
        commit_msg = f"刪除檔案: {clean_p}"
        porcelain.commit(
            repo_dir, 
            message=commit_msg.encode('utf-8'), 
            author=b"Web User <web@local.git>"
        )
        
def upload_and_commit(repo_name, file_path, file_bytes, message):
    with git_lock:
        repo_dir = get_repo_path(repo_name)
        cleanup_lock_files(repo_dir)
        
        clean_p = _clean_path(file_path)
        full_path = os.path.join(repo_dir, clean_p)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            f.write(file_bytes)

        porcelain.add(repo_dir, paths=[clean_p])
        porcelain.commit(repo_dir, message=message.encode('utf-8'), author=b"Web User <web@local.git>")

def cleanup_lock_files(repo_dir):
    lock_file = os.path.join(repo_dir, '.git', 'index.lock')
    if os.path.exists(lock_file):
        try: os.remove(lock_file)
        except Exception: pass
        
def batch_upload_and_commit(repo_name, file_data_list, message):
    """
    file_data_list: 一個列表，格式為 [{'path': 'file1.txt', 'bytes': b'...'}, {'path': 'file2.txt', 'bytes': b'...'}]
    """
    with git_lock:
        repo_dir = get_repo_path(repo_name)
        cleanup_lock_files(repo_dir)
        
        all_paths = []
        for item in file_data_list:
            clean_p = _clean_path(item['path'])
            full_path = os.path.join(repo_dir, clean_p)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(item['bytes'])
            all_paths.append(clean_p)

        # 批次 add
        porcelain.add(repo_dir, paths=all_paths)
        # 一次 commit
        porcelain.commit(repo_dir, message=message.encode('utf-8'), author=b"Web User <web@local.git>")

# --- 🌟 新增：獲取特定 Commit 版本的檔案內容 ---
def get_file_at_commit(repo_name, commit_sha, file_path):
    path = get_repo_path(repo_name)
    if not os.path.exists(path):
        return None
        
    repo = Repo(path)
    sha_bytes = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha
    
    if sha_bytes not in repo:
        return None
        
    try:
        commit = repo[sha_bytes]
        # 遍歷該 Commit 當時的目錄樹
        for item_path, mode, sha in repo.object_store.iter_tree_contents(commit.tree):
            clean_item_path = _clean_path(item_path)
            clean_target_path = _clean_path(file_path)
            
            if clean_item_path == clean_target_path:
                # 找到了！回傳該檔案的原始二進位資料
                return repo[sha].data
    except Exception as e:
        print(f"❌ 讀取歷史檔案失敗: {e}")
        
    return None
    
def get_commit_zip(repo_name, commit_sha):
    """將特定 Commit 的完整專案目錄樹打包為 ZIP 並回傳 BytesIO"""
    path = get_repo_path(repo_name)
    if not os.path.exists(path):
        return None
        
    repo = Repo(path)
    sha_bytes = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha
    
    if sha_bytes not in repo:
        return None
        
    try:
        commit = repo[sha_bytes]
        memory_zip = BytesIO()
        
        # 建立 ZIP 檔案，使用 ZIP_DEFLATED 進行壓縮
        with zipfile.ZipFile(memory_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            # iter_tree_contents 可以抓出當時整個專案所有的檔案
            for item_path, mode, sha in repo.object_store.iter_tree_contents(commit.tree):
                clean_path = _clean_path(item_path)
                file_data = repo[sha].data
                # 將檔案寫入 ZIP 中
                zf.writestr(clean_path, file_data)
                
        memory_zip.seek(0) # 將指標移回開頭以供讀取
        return memory_zip
    except Exception as e:
        print(f"❌ 打包 ZIP 失敗: {e}")
        return None
        
def get_commit_time_filename(repo_name, commit_sha):
    """取得特定 Commit 的時間，格式化為 YYYYMMDD_HHMM (例如 20260618_1455) 供檔名使用"""
    try:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        sha_bytes = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha
        if sha_bytes in repo:
            # 取得該 commit 的時間並格式化到分鐘
            dt = datetime.datetime.fromtimestamp(repo[sha_bytes].commit_time)
            return dt.strftime('%Y%m%d_%H%M')
    except Exception as e:
        print(f"⚠️ 檔案命名時間格式化失敗: {e}")
    return ""
    
def get_branches(repo_name):
    """獲取該倉庫的所有分支與當前所在分支，以及分支對應的 Commit (供前端貼標籤)"""
    path = get_repo_path(repo_name)
    repo = Repo(path)
    
    try:
        active_b = porcelain.active_branch(repo).decode('utf-8')
    except Exception:
        active_b = "main"

    branches = []
    tips = {}  # 🌟 新增：紀錄每個 Commit SHA 對應了哪些分支 (名牌)
    
    for ref in repo.refs.keys():
        if ref.startswith(b'refs/heads/'):
            b_name = ref.decode('utf-8').replace('refs/heads/', '')
            branches.append(b_name)
            
            # 取得該分支目前停留的 Commit SHA
            try:
                sha = repo.refs[ref].decode('ascii')
                if sha not in tips:
                    tips[sha] = []
                tips[sha].append(b_name)
            except:
                pass

    return {"current": active_b, "all": sorted(branches), "tips": tips}

def create_branch(repo_name, branch_name, commit_sha=None):
    """建立新分支。若提供 commit_sha，則從該歷史點建立；否則從當前 HEAD 建立"""
    with git_lock:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        branch_bytes = branch_name.encode('utf-8')
        
        if commit_sha:
            # 從指定的歷史 Commit 點建立分支
            sha_bytes = commit_sha.encode('utf-8') if isinstance(commit_sha, str) else commit_sha
            repo.refs[b'refs/heads/' + branch_bytes] = sha_bytes
        else:
            # 從目前最新的狀態建立分支
            repo.refs[b'refs/heads/' + branch_bytes] = repo.head()

def switch_branch(repo_name, branch_name):
    """切換分支 (Checkout) 並更新工作目錄的實體檔案"""
    with git_lock:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        branch_ref = b'refs/heads/' + branch_name.encode('utf-8')

        if branch_ref not in repo.refs:
            raise ValueError("分支不存在")

        # 1. 改變 HEAD 指針，使其指向新的分支
        repo.refs.set_symbolic_ref(b'HEAD', branch_ref)

        # 2. 強制重置工作目錄的實體檔案，讓畫面上的檔案變成該分支的狀態
        cleanup_lock_files(path)
        # 🌟 修正：移除 b，改用純字串 "HEAD"，避免底層套件型別解析崩潰
        porcelain.reset(repo, "hard", "HEAD")
        
# 🌟 新增：推送到遠端 GitHub 的核心引擎
def push_to_remote(repo_name, remote_url, token):
    """將本地倉庫推送到遠端 GitHub，過程不儲存 Token"""
    with git_lock:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        
        # 將 Token 安全地塞入 HTTPS 網址中進行自動授權
        if remote_url.startswith("https://") and token:
            # 替換 https:// 為 https://<token>@
            auth_url = remote_url.replace("https://", f"https://{token}@")
        else:
            auth_url = remote_url
            
        try:
            # 取得當前所在的分支名稱
            active_b = porcelain.active_branch(repo)
            refspec = b"refs/heads/" + active_b
        except Exception:
            # 防呆：如果獲取不到，預設推 main 分支
            refspec = b"refs/heads/main"
            
        try:
            # 執行 Dulwich push
            porcelain.push(repo, auth_url, refspecs=refspec)
        except Exception as e:
            raise Exception(f"Git Push 失敗，請檢查網址或 Token 權限是否正確。詳細錯誤: {str(e)}")

# --- 🌟 新增：移動或重新命名檔案 ---
def move_and_commit(repo_name, old_path, new_path):
    with git_lock:
        repo_dir = get_repo_path(repo_name)
        cleanup_lock_files(repo_dir)

        clean_old = _clean_path(old_path)
        clean_new = _clean_path(new_path)

        old_full = os.path.join(repo_dir, clean_old)
        new_full = os.path.join(repo_dir, clean_new)

        if not os.path.exists(old_full):
            raise FileNotFoundError(f"找不到原始檔案: {clean_old}")

        # 1. 確保目標資料夾存在 (若無則自動建立)
        os.makedirs(os.path.dirname(new_full), exist_ok=True)

        # 2. 實體移動/重新命名檔案
        shutil.move(old_full, new_full)

        # 3. Git 索引操作：加入新路徑
        porcelain.add(repo_dir, paths=[clean_new])

        # 4. Git 索引操作：移除舊路徑
        try:
            porcelain.rm(repo_dir, paths=[clean_old])
        except Exception as e:
            print(f"⚠️ Git rm 警告 (可忽略): {e}")

        # 5. 提交 Commit (Git 會自動將這兩個動作視為 Rename)
        commit_msg = f"🚚 重新命名/移動: {clean_old} -> {clean_new}"
        porcelain.commit(repo_dir, message=commit_msg.encode('utf-8'), author=b"Web User <web@local.git>")
        
# --- 🌟 新增：刪除分支 ---
def delete_branch(repo_name, branch_name):
    with git_lock:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        
        # 取得當前分支，防呆阻擋
        try:
            active_b = porcelain.active_branch(repo).decode('utf-8')
        except Exception:
            active_b = "main"
            
        if branch_name == active_b:
            raise ValueError("不能刪除當前正在使用的分支！請先切換到其他分支。")
            
        # 刪除底層的分支參考 (Ref)
        branch_ref = b'refs/heads/' + branch_name.encode('utf-8')
        if branch_ref in repo.refs:
            del repo.refs[branch_ref]
        else:
            raise ValueError(f"找不到分支: {branch_name}")
            
# --- 🌟 新增：合併分支 (Merge) ---
def merge_branch(repo_name, source_branch):
    """將來源分支 (source_branch) 的變更合併到當前分支，並產生 Y 型雙親節點"""
    with git_lock:
        path = get_repo_path(repo_name)
        repo = Repo(path)
        
        # 1. 取得目標 (當前) 與來源分支的指標
        try:
            active_b = porcelain.active_branch(repo)
        except Exception:
            active_b = b"main"
            
        target_ref = b'refs/heads/' + active_b
        source_ref = b'refs/heads/' + source_branch.encode('utf-8')
        
        if source_ref not in repo.refs:
            raise ValueError(f"找不到來源分支: {source_branch}")
            
        target_sha = repo.refs[target_ref]
        source_sha = repo.refs[source_ref]
        
        if target_sha == source_sha:
            raise ValueError("兩個分支目前指向同一個進度，無需合併。")
            
        target_commit = repo[target_sha]
        source_commit = repo[source_sha]
        
        # 2. 輕量級合併策略：將 Source 的檔案覆蓋/新增到工作目錄
        for item_path, mode, sha in repo.object_store.iter_tree_contents(source_commit.tree):
            clean_p = _clean_path(item_path)
            full_path = os.path.join(path, clean_p)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb') as f:
                f.write(repo[sha].data)
                
        # 3. 將變更加入 Git 索引，並取得新的樹狀結構 SHA
        porcelain.add(path)
        index = repo.open_index()
        new_tree_sha = index.commit(repo.object_store)
        
        # 4. 🌟 魔法核心：手動建立具有「雙親節點」的 Merge Commit
        merge_commit = Commit()
        merge_commit.tree = new_tree_sha
        merge_commit.parents = [target_sha, source_sha] # 讓 Git 產生 Y 字型匯流
        merge_commit.author = b"Web User <web@local.git>"
        merge_commit.committer = b"Web User <web@local.git>"
        
        current_time = int(time.time())
        merge_commit.commit_time = current_time
        merge_commit.commit_timezone = 0
        merge_commit.author_time = current_time
        merge_commit.author_timezone = 0
        
        msg = f"🔀 Merge branch '{source_branch}' into '{active_b.decode('utf-8')}'"
        merge_commit.message = msg.encode('utf-8')
        
        # 5. 寫入物件庫，並更新當前分支的指標
        repo.object_store.add_object(merge_commit)
        repo.refs[target_ref] = merge_commit.id
        
        # 6. 重置工作目錄確保乾淨
        cleanup_lock_files(path)
        porcelain.reset(repo, "hard", "HEAD")

# --- 🌟 新增：給 CLI 客戶端專用的 API 引擎 ---
def get_repo_manifest(repo_name):
    """計算並回傳伺服器端該專案所有檔案的 SHA-1 Hash 清單"""
    path = get_repo_path(repo_name)
    manifest = {}
    
    if not os.path.exists(path):
        return manifest
        
    for root, dirs, files in os.walk(path):
        # 忽略 Git 底層資料夾
        if '.git' in dirs:
            dirs.remove('.git')
            
        for f in files:
            full_p = os.path.join(root, f)
            # 取得相對路徑 (統一使用正斜線)
            rel_p = os.path.relpath(full_p, path).replace('\\', '/')
            
            # 計算檔案的 SHA-1 Hash
            sha1 = hashlib.sha1()
            with open(full_p, 'rb') as fp:
                sha1.update(fp.read())
            manifest[rel_p] = sha1.hexdigest()
            
    return manifest
    
