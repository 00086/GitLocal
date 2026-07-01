from flask import Blueprint, render_template, abort, request, redirect, url_for, send_file, send_from_directory, jsonify
import database as db
import io
import os # 如果沒有 os 請補上

web_ui = Blueprint('web_ui', __name__)

@web_ui.route('/')
def index():
    repos = db.get_all_repositories()
    return render_template('index.html', repos=repos)

# --- 🌟 新增：建立新倉庫 ---
@web_ui.route('/create_repo', methods=['POST'])
def create_repo():
    repo_name = request.form.get('repo_name')
    if repo_name:
        db.create_new_repo(repo_name)
    return redirect(url_for('web_ui.index'))

@web_ui.route('/repo/<repo_name>')
def repo_detail(repo_name):
    details = db.get_repo_details(repo_name)
    if details is None:
        abort(404)
        
    # 🌟 讀取 Releases 金庫資料
    releases = db.get_releases_list(repo_name)
        
    return render_template('repo.html', 
                           repo_name=repo_name, 
                           commits=details["commits"], 
                           graph_commits=details.get("graph_commits", []), 
                           files=details["files"],
                           branches=details.get("branches", {}),
                           releases=releases) # 🌟 新增這行

# --- 🌟 讀取與修改：檔案編輯器介面 ---
@web_ui.route('/repo/<repo_name>/file/<path:file_path>', methods=['GET', 'POST'])
def edit_file(repo_name, file_path):
    # 如果使用者按下儲存 (POST)
    if request.method == 'POST':
        content = request.form.get('content')
        message = request.form.get('message', f"Update {file_path}")
        db.write_and_commit(repo_name, file_path, content, message)
        return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))

    # 如果是純瀏覽 (GET)
    content = db.get_file_content(repo_name, file_path)
    return render_template('edit.html', repo_name=repo_name, file_path=file_path, content=content)

# --- 🌟 建立新檔案：跳轉到編輯器 ---
@web_ui.route('/repo/<repo_name>/new_file', methods=['POST'])
def new_file(repo_name):
    file_name = request.form.get('file_name')
    if file_name:
        # 將使用者導向該新檔案的編輯頁面
        return redirect(url_for('web_ui.edit_file', repo_name=repo_name, file_path=file_name))
    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))

# --- 🌟 刪除檔案 ---
@web_ui.route('/repo/<repo_name>/delete/<path:file_path>', methods=['POST'])
def delete_file(repo_name, file_path):
    db.delete_and_commit(repo_name, file_path)
    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))

# --- 替換 routes.py 裡的 upload_file ---
@web_ui.route('/repo/<repo_name>/upload', methods=['POST'])
def upload_file(repo_name):
    if 'file' not in request.files:
        return "No file part", 400
    
    uploaded_file = request.files['file']
    
    # 🌟 暴力攔截：確保無論前端用什麼變數名稱傳過來，都能接得住
    custom_message = request.form.get('message') or request.form.get('commit_message') 
    target_path = request.form.get('file_path', uploaded_file.filename)
    
    if uploaded_file.filename != '':
        file_bytes = uploaded_file.read()
        
        # 🌟 嚴格防呆：過濾掉前端可能傳來的 undefined 或 null 字串
        if not custom_message or str(custom_message).strip() in ["", "undefined", "null"]:
            commit_msg = f"Upload file: {target_path}"
        else:
            commit_msg = str(custom_message).strip()
            
        db.upload_and_commit(repo_name, target_path, file_bytes, commit_msg)
        
    return "Success", 200

# --- 🌟 讀取特定 Commit 的詳細差異 (Diff) --- # 202606170903
@web_ui.route('/repo/<repo_name>/commit/<commit_sha>')
def commit_detail(repo_name, commit_sha):
    data = db.get_commit_diff(repo_name, commit_sha)
    if not data:
        return "Commit not found", 404
    return render_template('commit.html', repo_name=repo_name, **data)
    
# --- 🌟 批次上傳處理路由 (請替換這段) ---
@web_ui.route('/repo/<repo_name>/batch_upload', methods=['POST'])
def batch_upload(repo_name):
    files = request.files.getlist('files')
    # 從前端 FormData 獲取訊息
    message = request.form.get('message', '').strip()
    
    # 防呆：如果沒有說明，給予預設值
    if not message:
        message = f"批次上傳 {len(files)} 個檔案"
    
    file_data_list = []
    for f in files:
        if f.filename:
            file_data_list.append({
                'path': f.filename,
                'bytes': f.read()
            })
    
    # 確保 file_data_list 有內容才進行 Commit
    if file_data_list:
        db.batch_upload_and_commit(repo_name, file_data_list, message)
        
    return "Success", 200
    
# --- 🌟 新增：下載特定 Commit 版本的檔案 ---
@web_ui.route('/repo/<repo_name>/download/<commit_sha>/<path:file_path>')
def download_file_at_commit(repo_name, commit_sha, file_path):
    file_bytes = db.get_file_at_commit(repo_name, commit_sha, file_path)
    
    if file_bytes is None:
        return "找不到該版本的檔案，可能已被刪除或路徑錯誤。", 404
        
    file_name = file_path.split('/')[-1]
    
    # 🌟 新增：取得 Commit 的時間字串 (如 20260618_1455)
    time_str = db.get_commit_time_filename(repo_name, commit_sha)
    
    # 組合新檔名：[時間]_[簡短SHA]_[原檔名]
    if time_str:
        custom_download_name = f"{time_str}_{commit_sha[:7]}_{file_name}"
    else:
        custom_download_name = f"{commit_sha[:7]}_{file_name}"
    
    return send_file(
        io.BytesIO(file_bytes),
        as_attachment=True,
        download_name=custom_download_name
    )
  
# --- 🌟 新增：取得原始檔案 (供圖片預覽使用) ---
@web_ui.route('/repo/<repo_name>/raw/<path:file_path>')
def raw_file(repo_name, file_path):
    # 取得倉庫的絕對路徑
    repo_dir = db.get_repo_path(repo_name)
    # send_from_directory 會安全地回傳實體檔案
    return send_from_directory(repo_dir, file_path)
    
@web_ui.route('/repo/<repo_name>/download_zip/<commit_sha>')
def download_commit_zip(repo_name, commit_sha):
    zip_buffer = db.get_commit_zip(repo_name, commit_sha)
    
    if zip_buffer is None:
        return "無法打包該版本的專案", 404

    # 🌟 新增：取得 Commit 的時間字串 (如 20260618_1455)
    time_str = db.get_commit_time_filename(repo_name, commit_sha)
    
    # 組合新檔名：[專案名]_[時間]_[簡短SHA].zip
    if time_str:
        custom_zip_name = f"{repo_name}_{time_str}_{commit_sha[:7]}.zip"
    else:
        custom_zip_name = f"{repo_name}_{commit_sha[:7]}.zip"

    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=custom_zip_name
    )
    
# --- 🌟 新增：建立分支 (可指定從歷史 Commit 建立) ---
@web_ui.route('/repo/<repo_name>/branch/create', methods=['POST'])
def create_branch(repo_name):
    branch_name = request.form.get('branch_name')
    commit_sha = request.form.get('commit_sha')  # 若從歷史紀錄點擊，會有這個值

    if branch_name:
        # 清理分支名稱中的空白字元
        clean_branch_name = branch_name.replace(" ", "-").strip()
        db.create_branch(repo_name, clean_branch_name, commit_sha)
        
        # 建立完成後，自動將使用者切換到該新分支
        db.switch_branch(repo_name, clean_branch_name)

    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))

# --- 🌟 新增：切換分支 (Checkout) ---
@web_ui.route('/repo/<repo_name>/branch/switch', methods=['POST'])
def switch_branch(repo_name):
    branch_name = request.form.get('branch_name')
    if branch_name:
        db.switch_branch(repo_name, branch_name)

    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))
    
# 🌟 新增：接收前端 Push 請求的 API
@web_ui.route('/repo/<repo_name>/push', methods=['POST'])
def push_repo(repo_name):
    remote_url = request.form.get('remote_url')
    token = request.form.get('token')
    
    if not remote_url or not token:
        return "必須提供 GitHub 網址與 Token", 400
        
    try:
        # 呼叫底層引擎執行推送
        db.push_to_remote(repo_name, remote_url.strip(), token.strip())
        return "Push 成功！已同步至遠端。", 200
    except Exception as e:
        return str(e), 500

# --- 🌟 新增：移動或重新命名檔案的 API ---
@web_ui.route('/repo/<repo_name>/move', methods=['POST'])
def move_file(repo_name):
    old_path = request.form.get('old_path')
    new_path = request.form.get('new_path')

    if not old_path or not new_path:
        return "缺少原始路徑或目標路徑", 400

    # 防呆：避免被利用 ../ 惡意搬移系統其他檔案
    if ".." in new_path:
        return "無效的目標路徑", 400

    try:
        db.move_and_commit(repo_name, old_path.strip(), new_path.strip())
        return "Success", 200
    except Exception as e:
        return str(e), 500
        
# --- 🌟 新增：刪除分支 (Delete Branch) ---
@web_ui.route('/repo/<repo_name>/branch/delete', methods=['POST'])
def delete_branch(repo_name):
    branch_name = request.form.get('branch_name')
    if branch_name:
        try:
            db.delete_branch(repo_name, branch_name)
        except Exception as e:
            # 發生錯誤時直接回傳錯誤訊息
            return str(e), 400

    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))
    
# --- 🌟 新增：合併分支 (Merge) ---
@web_ui.route('/repo/<repo_name>/branch/merge', methods=['POST'])
def merge_branch(repo_name):
    source_branch = request.form.get('source_branch')
    if source_branch:
        try:
            db.merge_branch(repo_name, source_branch)
        except Exception as e:
            return str(e), 400

    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))
    
# --- 🌟 新增：CLI 專用 API (取得專案檔案清單與 Hash) ---
@web_ui.route('/api/repo/<repo_name>/manifest', methods=['GET'])
def api_manifest(repo_name):
    manifest = db.get_repo_manifest(repo_name)
    return jsonify(manifest)
    
# ==========================================
# 🌟 Releases 發布中心專屬 API
# ==========================================
@web_ui.route('/repo/<repo_name>/release/create', methods=['POST'])
def create_release(repo_name):
    tag_name = request.form.get('tag_name')
    message = request.form.get('message', '')
    uploaded_files = request.files.getlist('assets') # 接收多檔案

    if tag_name:
        try:
            db.create_release(repo_name, tag_name, message, uploaded_files)
        except Exception as e:
            return f"建立發布失敗: {e}", 500
            
    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))

@web_ui.route('/repo/<repo_name>/release/download/<tag_name>/<path:file_name>')
def download_release_asset(repo_name, tag_name, file_name):
    target_path = os.path.join(db.get_repo_path(repo_name), ".gitlocal", "releases", tag_name, file_name)
    if not os.path.exists(target_path):
        abort(404, "找不到該發布檔案")
    return send_file(target_path, as_attachment=True)

@web_ui.route('/repo/<repo_name>/release/delete/<tag_name>', methods=['POST'])
def delete_release(repo_name, tag_name):
    if tag_name:
        try:
            db.delete_release(repo_name, tag_name)
        except Exception as e:
            return f"刪除發布失敗: {e}", 500
    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))
    
# --- 🌟 新增：編輯特定 Release ---
@web_ui.route('/repo/<repo_name>/release/edit/<tag_name>', methods=['POST'])
def edit_release(repo_name, tag_name):
    message = request.form.get('message', '')
    uploaded_files = request.files.getlist('assets')

    if tag_name:
        try:
            db.edit_release(repo_name, tag_name, message, uploaded_files)
        except Exception as e:
            return f"編輯發布失敗: {e}", 500
            
    return redirect(url_for('web_ui.repo_detail', repo_name=repo_name))
    
