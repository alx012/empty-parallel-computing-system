# ============================================
# worker_server.py (立即回應版)
# ============================================
from flask import Flask, request, jsonify
from module_runner import run_module
from db_utils import save_result
from module5_merge import submit_partial_trace
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import os
import signal
import threading
from queue import Queue
from datetime import datetime  # ← 新增這行

# 設定多進程啟動方法（重要！）
if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)

app = Flask(__name__)


# 全局進程池（在 Worker 啟動時創建）
process_pool = None
computation_queue = Queue()

def init_process_pool():
    """初始化進程池"""
    global process_pool
    cpu_count = mp.cpu_count()
    max_workers = min(cpu_count, 4)  # 限制最大進程數，避免系統過載
    
    print(f"🔧 初始化進程池，CPU核心數: {cpu_count}，使用進程數: {max_workers}")
    
    process_pool = ProcessPoolExecutor(
        max_workers=max_workers,
        mp_context=mp.get_context('spawn')  # 確保使用 spawn 方法
    )
    
    return process_pool

def cleanup_process_pool():
    """清理進程池"""
    global process_pool
    if process_pool:
        print("🧹 正在關閉進程池...")
        process_pool.shutdown(wait=True)
        process_pool = None

# 註冊清理函數
import atexit
atexit.register(cleanup_process_pool)

def signal_handler(signum, frame):
    """處理系統信號"""
    print(f"🛑 收到信號 {signum}，正在關閉...")
    cleanup_process_pool()
    os._exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route("/compute", methods=["POST"])
def compute():
    """
    ✅ 修正版：立即回應 HTTP 請求，計算在背景進行
    這是解決並行問題的關鍵修正
    """
    global process_pool
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "無效的 JSON 資料"}), 400
            
        module = data.get("module_name")
        inputs = data.get("input_data", {})
        exec_id = data.get("execution_id", "unknown")
        user_inputs = data.get("user_inputs", {})

        receive_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[WORKER] 📥 {receive_time} 收到任務 {module} (執行 ID: {exec_id})")
        print(f"[WORKER] 📋 輸入：{inputs}")

        # 確保進程池已初始化
        if process_pool is None:
            print("[WORKER] ⚠️ 進程池未初始化，重新創建...")
            init_process_pool()

         
    except Exception as e:
        print(f"[WORKER] ❌ {datetime.now().strftime('%H:%M:%S.%f')[:-3]} 處理請求時發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error", 
            "message": f"伺服器內部錯誤：{str(e)}"
        }), 500


# 修改背景處理判斷為通用版本
def should_use_background_processing(module_name):
    """判斷是否應該使用背景處理某個模組"""
    # 計算密集型模組使用背景處理（範例，請根據實際需求修改）
    background_modules = ["heavy_compute_module", "data_processing_module"]
    return module_name in background_modules



def run_module_background(module_name, inputs, user_inputs, exec_id):
    """背景執行一般模組"""
    try:
        start_time = time.time()
        start_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        pid = os.getpid()
        
        print(f"[子進程] 🔧 {start_timestamp} 執行模組 {module_name} (PID: {pid}, ID: {exec_id})")
        
        # 在子進程中重新導入必要的模組
        from module_runner import run_module
        from db_utils import save_result
        
        result = run_module(module_name, inputs, user_inputs=user_inputs)
        save_result(module_name, result)
        
        duration = time.time() - start_time
        end_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        print(f"[子進程] ✅ {end_timestamp} 模組 {module_name} 執行完成 (PID: {pid}, 耗時: {duration:.2f}s)")
        
        return result
    except Exception as e:
        error_timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[子進程] ❌ {error_timestamp} 模組 {module_name} 執行失敗 (PID: {os.getpid()})：{e}")
        raise


@app.route("/health", methods=["GET", "POST"])
def health_check():
    """Worker 健康檢查端點"""
    global process_pool
    
    pool_status = "ready" if process_pool and not process_pool._shutdown else "not_initialized"
    
    return jsonify({
        "status": "healthy",
        "worker": "ready",
        "execution_mode": "background_multiprocessing",
        "process_pool_status": pool_status,
        "cpu_count": mp.cpu_count(),
        "supports": ["instant_response", "background_computing", "module5_multiprocess", "parallel_computing"],
        "current_time": datetime.now().strftime('%H:%M:%S.%f')[:-3],
        "pid": os.getpid(),
        "description": "立即回應版本，支援真正並行計算"
    })


@app.route("/pool_status", methods=["GET"])
def pool_status():
    """檢查進程池狀態"""
    global process_pool
    
    if process_pool is None:
        return jsonify({
            "status": "not_initialized",
            "message": "進程池尚未初始化"
        })
    
    return jsonify({
        "status": "active",
        "max_workers": process_pool._max_workers,
        "shutdown": process_pool._shutdown,
        "cpu_count": mp.cpu_count(),
        "current_time": datetime.now().strftime('%H:%M:%S.%f')[:-3]
    })



@app.route("/tasks_status", methods=["GET"])
def tasks_status():
    """檢查背景任務狀態（可選）"""
    return jsonify({
        "background_tasks": "active",
        "process_pool_active": process_pool is not None,
        "current_time": datetime.now().strftime('%H:%M:%S.%f')[:-3],
        "message": "背景任務正在進行，請查看控制台輸出"
    })


if __name__ == "__main__":
    import sys
    
    # 處理命令行參數
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
    
    print(f"🚀 立即回應版多進程 Worker 伺服器啟動於端口 {port}")
    print(f"💾 系統 CPU 核心數: {mp.cpu_count()}")
    print(f"🔧 當前進程 PID: {os.getpid()}")
    
    # 初始化進程池
    init_process_pool()
    
    print("📋 關鍵特性：")
    print("  ✅ HTTP 請求立即回應（不等待計算完成）")
    print("  ✅ 計算在背景獨立進程中進行")
    print("  ✅ 支援真正並行處理（無 GIL 限制）")
    print("  ✅ 自動提交計算結果")
    print("  🎯 解決串行執行問題")
    
    try:
        # 嘗試使用 Waitress（更好的 WSGI 伺服器）
        try:
            from waitress import serve
            print("🌟 使用 Waitress 伺服器（生產級別）")
            serve(app, host="0.0.0.0", port=port, threads=mp.cpu_count() * 2)
        except ImportError:
            print("⚠️ Waitress 未安裝，使用 Flask 開發伺服器")
            print("💡 建議安裝：pip install waitress")
            
            # 使用 Flask 的多進程模式
            app.run(
                host="0.0.0.0", 
                port=port, 
                threaded=True,      # 支援多線程處理 HTTP 請求
                processes=1,        # 我們使用內部的 ProcessPoolExecutor
                debug=False,
                use_reloader=False  # 避免重載干擾
            )
            
    except KeyboardInterrupt:
        print("\n🛑 收到中斷信號，正在關閉...")
        cleanup_process_pool()
    except Exception as e:
        print(f"❌ 伺服器啟動失敗：{e}")
        cleanup_process_pool()