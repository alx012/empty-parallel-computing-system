# ============================================
# enhanced_master.py (支援歷史計算記錄的增強版)
# ============================================
import uuid
import time
import os
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests
from transport_utils import get_available_worker
from dag_utils import build_dag
from modules_config import get_modules_config
from db_utils import (
    init_enhanced_db, start_calculation_session, save_result, 
    complete_calculation_session, get_session_list, get_session_results,
    export_session_to_file, copy_session_results
)

# ------------------------分隔線--------------------------- #

def ask_user_inputs():
    """
    收集用戶輸入 - 範本版本
    請根據您的模組需求修改此函數
    num1 = int(input("請輸入 num1："))
    num2 = int(input("請輸入 num2："))
    num3 = int(input("請輸入 num3："))
    return {"num1": num1, "num2": num2, "num3": num3}

    """

# ------------------------分隔線--------------------------- #

def ask_calculation_description():
    """詢問計算描述和標籤"""
    description = input("請輸入此次計算的描述（可選）：").strip()
    if not description:
        description = f"計算 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    tags_input = input("請輸入標籤（多個標籤用逗號分隔，可選）：").strip()
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()] if tags_input else []
    
    return description, tags

def show_historical_sessions():
    """顯示歷史計算會話"""
    print("\n📚 近期計算會話：")
    sessions = get_session_list(limit=10)
    
    if not sessions:
        print("  📝 還沒有歷史計算記錄")
        return None
    
    print("-" * 80)
    print(f"{'序號':<4} {'會話ID':<12} {'描述':<25} {'狀態':<8} {'耗時':<8} {'模組':<8} {'開始時間':<16}")
    print("-" * 80)
    
    for i, session in enumerate(sessions, 1):
        duration = f"{session['duration_seconds']:.1f}s" if session['duration_seconds'] else "N/A"
        modules = f"{session['success_modules']}/{session['total_modules']}"
        start_time = session['start_time'][:16] if session['start_time'] else "N/A"
        
        print(f"{i:<4} {session['session_id'][:12]:<12} {session['description'][:25]:<25} "
              f"{session['status']:<8} {duration:<8} {modules:<8} {start_time:<16}")
    
    print("-" * 80)
    
    choice = input("\n要查看詳細結果嗎？輸入序號（1-{}），或按 Enter 跳過：".format(len(sessions))).strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(sessions):
        selected_session = sessions[int(choice) - 1]
        show_session_detail(selected_session['session_id'])
        
        # 詢問是否要使用歷史結果
        use_historical = input("\n要使用這個會話的結果作為本次計算的基礎嗎？(y/N)：").strip().lower()
        if use_historical == 'y':
            return selected_session['session_id']
    
    return None

def show_session_detail(session_id: str):
    """顯示會話詳細結果"""
    session_data = get_session_results(session_id)
    if not session_data:
        print(f"❌ 找不到會話：{session_id}")
        return
    
    print(f"\n📋 會話詳細資料：{session_id}")
    print("=" * 60)
    print(f"📝 描述：{session_data['description']}")
    print(f"👤 用戶輸入：{session_data['user_inputs']}")
    print(f"🏷️ 標籤：{', '.join(session_data['tags']) if session_data['tags'] else '無'}")
    print(f"⏱️ 耗時：{session_data['duration_seconds']:.2f} 秒")
    print(f"📊 模組：{session_data['success_modules']}/{session_data['total_modules']}")
    print(f"🎯 最終結果：{session_data['final_result']}")
    
    print(f"\n🧩 各模組結果：")
    print("-" * 50)
    for module_id in sorted(session_data['modules'].keys()):
        module_data = session_data['modules'][module_id]
        duration = f"{module_data['duration_seconds']:.2f}s" if module_data['duration_seconds'] else "N/A"
        print(f"  {module_id:<12}: {module_data['result']} (耗時: {duration})")

# ------------------------分隔線--------------------------- #

# Worker Pool 配置 - 請根據實際部署修改
worker_pool = {
    # "worker1": "http://localhost:5001",
    # "worker2": "http://localhost:5002",
    # 添加更多 worker...
}

# ------------------------分隔線--------------------------- #

def format_duration(seconds):
    """格式化時間顯示"""
    if seconds < 1:
        return f"{seconds*1000:.1f} 毫秒"
    elif seconds < 60:
        return f"{seconds:.2f} 秒"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes} 分 {remaining_seconds:.2f} 秒"

def send_task_fire_and_forget(task_info):
    """發射即忘任務發送"""
    subtask, worker_url, task_id = task_info
    
    try:
        send_time = time.strftime('%H:%M:%S.%f')[:-3]
        print(f"📤 [任務 {task_id+1}] {send_time} 發送到 {worker_url}")
        
        task_packet = {

        }
        
        response = requests.post(
            f"{worker_url}/compute",
            json=task_packet,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            confirm_time = time.strftime('%H:%M:%S.%f')[:-3]
            print(f"✅ [任務 {task_id+1}] {confirm_time} 成功發送並確認接收")
            return {
                "task_id": task_id, 
                "worker": worker_url, 
                "status": "sent",
                "send_time": send_time,
                "confirm_time": confirm_time
            }
        else:
            print(f"❌ [任務 {task_id+1}] 發送失敗：{response.status_code}")
            return {"task_id": task_id, "status": "failed"}
            
    except Exception as e:
        print(f"❌ [任務 {task_id+1}] 發送異常：{e}")
        return {"task_id": task_id, "status": "error", "error": str(e)}

def dispatch_subtasks_truly_parallel(subtasks):
    """真正的並行分派子任務"""
    print(f"\n🚀 開始真正並行分派 {len(subtasks)} 個子任務...")
    dispatch_start_time = time.time()
    start_timestamp = time.strftime('%H:%M:%S.%f')[:-3]
    
    print(f"🕐 分派開始時間：{start_timestamp}")
    print(f"💻 系統 CPU 核心數：{mp.cpu_count()}")
    
    task_list = []
    for i, subtask in enumerate(subtasks):
        worker_url = get_available_worker(worker_pool, i)
        task_list.append((subtask, worker_url, i))
    
    max_workers = len(task_list)
    print(f"🔧 使用 {max_workers} 個線程同時發送任務...")
    
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {
            executor.submit(send_task_fire_and_forget, task_info): task_info 
            for task_info in task_list
        }
        
        for future in as_completed(future_to_task):
            try:
                result = future.result(timeout=30)
                results.append(result)
                
                if result["status"] == "sent":
                    print(f"📡 任務 {result['task_id']+1} 發送確認完成")
                else:
                    print(f"⚠️ 任務 {result['task_id']+1} 發送失敗")
                    
            except Exception as e:
                print(f"❌ 任務發送過程異常：{e}")
                results.append({"status": "exception", "error": str(e)})
    
    dispatch_duration = time.time() - dispatch_start_time
    end_timestamp = time.strftime('%H:%M:%S.%f')[:-3]
    
    sent_count = sum(1 for r in results if r.get("status") == "sent")
    failed_count = len(results) - sent_count
    
    print(f"\n📊 任務分派統計：")
    print(f"  🕐 分派結束時間：{end_timestamp}")
    print(f"  ✅ 成功發送：{sent_count} 個任務")
    print(f"  ❌ 發送失敗：{failed_count} 個任務")
    print(f"  ⏱️ 分派耗時：{format_duration(dispatch_duration)}")
    print(f"  🎯 現在所有 Worker 正在同時並行計算！")
    
    if results:
        send_times = [r.get("send_time") for r in results if r.get("send_time")]
        if len(send_times) > 1:
            print(f"  📈 任務發送時間分佈：{send_times[0]} ~ {send_times[-1]}")
            print(f"  🎯 時間分佈範圍：約 {dispatch_duration:.3f} 秒（應該很短才對）")
    
    return sent_count > 0

def main(user_inputs, description="", tags=None, base_session_id=None):
    """主執行函數（增強版）"""
    total_start_time = time.time()
    startup_time = time.time()
    
    print(f"\n🚀 啟動增強版 Master（支援歷史記錄）")
    print(f"💾 系統 CPU 核心數：{mp.cpu_count()}")
    print(f"🕐 開始時間：{datetime.now().strftime('%H:%M:%S')}")
    
    # 初始化增強版資料庫
    print("\n🔄 初始化增強版資料庫...")
    init_enhanced_db()
    
    # 開始新的計算會話
    session_id = start_calculation_session(user_inputs, description, tags)
    
    # 設定環境變數
    os.environ['AVAILABLE_WORKERS'] = str(len(worker_pool))

    print("\n🧩 載入模組與建構 DAG...")
    modules = get_modules_config(user_inputs)
    dag, execution_order = build_dag(modules)
    result_map = {}
    answer_map = {}
    
    # 如果有基礎會話，載入其結果
    if base_session_id:
        print(f"📋 載入基礎會話結果：{base_session_id}")
        base_results = copy_session_results(base_session_id, user_inputs, 
                                          f"基於會話 {base_session_id[:8]} 的計算")
        answer_map.update(base_results)
        print(f"✅ 已載入 {len(base_results)} 個基礎結果")
    
    # 記錄各模組執行時間
    module_times = {}
    
    startup_duration = time.time() - startup_time
    print(f"⚡ 初始化完成，耗時：{format_duration(startup_duration)}")

    print(f"\n🚀 模組執行順序為：{execution_order}")
    print(f"📊 共需執行 {len(execution_order)} 個模組\n")

    for idx, module in enumerate(execution_order):
        module_start_time = time.time()
        
        print(f"\n=== 🟡 執行模組 {module} ({idx+1}/{len(execution_order)}) ===")
        print(f"🕐 模組開始時間：{datetime.now().strftime('%H:%M:%S')}")

        # 準備輸入資料
        if module == "module1":
            inputs = user_inputs.copy()
        else:
            inputs = {}
            for required_answer in modules[module]["requires"]:
                if required_answer in answer_map:
                    inputs[required_answer] = answer_map[required_answer]
                else:
                    print(f"⚠️ 警告：找不到依賴答案 {required_answer}")

        print(f"📋 準備的輸入資料：{inputs}")

        exec_id = str(uuid.uuid4())
        module_exec_start_time = datetime.now()

        
    # 計算總執行時間
    total_duration = time.time() - total_start_time
    
    # 取得最終結果
    final_result = None
    if "final_result" in answer_map:
        final_result = answer_map["final_result"]
    elif "module7" in result_map and "final_result" in result_map["module7"]:
        final_result = result_map["module7"]["final_result"]
    
    # 完成計算會話
    complete_calculation_session(final_result, len(execution_order))
    
    print("\n" + "="*60)
    print("🎉 所有模組執行完畢（增強版 - 支援歷史記錄）")
    print("="*60)
    
    # 顯示各模組執行時間統計
    print("\n📊 各模組執行時間統計：")
    print("-" * 40)
    for module, duration in module_times.items():
        percentage = (duration / total_duration) * 100
        print(f"  {module:<20} : {format_duration(duration):<12} ({percentage:.1f}%)")
    
    print("-" * 40)
    print(f"  {'總計':<20} : {format_duration(total_duration)}")
    
    # 顯示最終結果
    if final_result:
        print(f"\n📦 最終結果：{final_result}")
    else:
        print("\n⚠️ 未找到最終結果，可能執行中途失敗")
        if "answer7" not in answer_map:
            print("❌ 主要問題：answer7 缺失（Module name 可能失敗）")
        else:
            print(f"✅ answer7 存在：{answer_map.get('answer7')}")
    
    print(f"\n💾 計算會話已儲存：{session_id}")
    print(f"📄 可使用 export_session_to_file('{session_id}') 匯出結果")
    
    # 詢問是否要匯出結果
    export_choice = input("\n要將此次計算結果匯出到檔案嗎？(y/N)：").strip().lower()
    if export_choice == 'y':
        try:
            file_path = export_session_to_file(session_id)
            print(f"✅ 結果已匯出到：{file_path}")
        except Exception as e:
            print(f"❌ 匯出失敗：{e}")
    
    return session_id, final_result

def execute_standard_module(module, inputs, exec_id, user_inputs, idx):
    """執行標準模組的通用函數"""
    from transport_utils import send_task_to_worker, receive_result
    
    send_start = time.time()
    worker = get_available_worker(worker_pool, idx)
    task_packet = {
        "module_name": module,
        "input_data": inputs,
        "execution_id": exec_id,
        "user_inputs": user_inputs
    }

    print(f"📤 發送 {module} 到 {worker}")
    send_response = send_task_to_worker(worker, task_packet)
    send_duration = time.time() - send_start

    if send_response is None:
        print(f"❌ 無法傳送模組 {module}，跳過此模組")
        return None

    print(f"📡 任務傳送耗時：{format_duration(send_duration)}")

    try:
        wait_start = time.time()
        print(f"⏳ 等待模組 {module} 執行結果...")
        
        timeout = 300 if module == "module name" else 120
        result_data = receive_result(module, timeout=timeout)
        wait_duration = time.time() - wait_start
        
        if isinstance(result_data, dict) and module in result_data:
            result = result_data[module]
        else:
            result = result_data
        
        from db_utils import register_result_location
        register_result_location(module, result, worker)
        
        print(f"✅ 模組 {module} 完成，結果為：{result}")
        print(f"⏱️ 等待結果耗時：{format_duration(wait_duration)}")
        
        return result
        
    except Exception as e:
        print(f"❌ 模組 {module} 執行失敗或超時：{e}")
        return None

def interactive_mode():
    """互動模式主函數"""
    print("🚀 增強版 Master - 支援歷史計算記錄")
    print(f"💻 檢測到 {mp.cpu_count()} 個 CPU 核心")
    print("🎯 新特性：完整的計算歷史記錄和結果重用")
    
    while True:
        print("\n" + "="*50)
        print("📋 選擇操作：")
        print("1. 開始新的計算")
        print("2. 查看歷史計算")
        print("3. 基於歷史結果計算")
        print("4. 匯出歷史結果")
        print("5. 退出")
        print("="*50)
        
        choice = input("請選擇 (1-5)：").strip()
        
        if choice == '1':
            # 新計算
            user_inputs = ask_user_inputs()
            description, tags = ask_calculation_description()
            main(user_inputs, description, tags)
            
        elif choice == '2':
            # 查看歷史
            show_historical_sessions()
            
        elif choice == '3':
            # 基於歷史結果計算
            base_session_id = show_historical_sessions()
            if base_session_id:
                user_inputs = ask_user_inputs()
                description, tags = ask_calculation_description()
                description = f"[基於歷史] {description}"
                main(user_inputs, description, tags, base_session_id)
            else:
                print("⚠️ 未選擇基礎會話")
                
        elif choice == '4':
            # 匯出歷史結果
            sessions = get_session_list(limit=10)
            if sessions:
                print("\n📚 可匯出的會話：")
                for i, session in enumerate(sessions, 1):
                    print(f"{i}. {session['session_id'][:12]} - {session['description']}")
                
                choice_idx = input("選擇要匯出的會話序號：").strip()
                if choice_idx.isdigit() and 1 <= int(choice_idx) <= len(sessions):
                    selected_session = sessions[int(choice_idx) - 1]
                    try:
                        file_path = export_session_to_file(selected_session['session_id'])
                        print(f"✅ 已匯出到：{file_path}")
                    except Exception as e:
                        print(f"❌ 匯出失敗：{e}")
                else:
                    print("❌ 無效的選擇")
            else:
                print("📝 沒有可匯出的歷史記錄")
                
        elif choice == '5':
            print("👋 再見！")
            break
            
        else:
            print("❌ 無效的選擇，請輸入 1-5")

if __name__ == "__main__":
    interactive_mode()