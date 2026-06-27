from flask import Flask
from routes import web_ui  # 匯入路由藍圖
# 🌟 新增：引入 Waitress 伺服器
from waitress import serve 

def create_app():
    app = Flask(__name__)
    
    # 註冊路由藍圖
    app.register_blueprint(web_ui)
    
    return app

if __name__ == '__main__':
    # 1. 透過工廠模式建立 Flask 應用程式實例
    app = create_app()
    
    #app.run(debug=True, port=5001)
    
    print("🚀 生產級 WSGI 伺服器 Waitress 啟動中...")
    print("👉 本地管理網址: http://127.0.0.1:5001")
    
    # 2. 🌟 移除原有的 app.run()，改由 Waitress serve 啟動
    # host='127.0.0.1' 限制僅本地連線
    # port=5001 保留你原本指定的 5001 連接埠
    # threads=6 代表同時啟用 6 個執行緒（線程）來高速並發處理前端請求
    serve(app, host='127.0.0.1', port=5001, threads=6)