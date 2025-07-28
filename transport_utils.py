# ============================================
# transport_utils.py (调整超时设置版)
# ============================================

import requests
import time
import json
from typing import Dict, Any
from db_utils import fetch_answers

def send_task_to_worker(worker_url: str, task_packet: Dict[str, Any], timeout: int = 300):
    """
    發送任務到指定 worker
    timeout: HTTP 请求超时时间（秒），默认5分钟，可根据任务复杂度调整
    """
    try:
        # ✅ 针对不同模块设置不同的超时时间
        module_name = task_packet.get("module_name", "")
        if module_name == "module5":
            timeout = 600  # module5 设置10分钟超时
        elif module_name.startswith("module5_"):
            timeout = 300  # module5 子任务设置5分钟超时
        else:
            timeout = 60   # 其他模块1分钟超时
        
        print(f"⏰ 设置 {module_name} 的超时时间为 {timeout} 秒")
        
        response = requests.post(
            f"{worker_url}/compute",
            json=task_packet,
            headers={'Content-Type': 'application/json'},
            timeout=timeout  # ✅ 使用动态超时时间
        )

        if response.status_code == 200:
            print(f"✅ 任務成功發送至 {worker_url}")
            return response.json()
        else:
            print(f"❌ 傳送任務至 {worker_url} 失敗：{response.status_code} {response.reason}")
            return None

    except requests.exceptions.ReadTimeout:
        print(f"⏰ {worker_url} 執行 {module_name} 超時（{timeout}秒），但任務可能仍在背景執行")
        return {"status": "timeout_but_running"}
    except Exception as e:
        print(f"❌ 傳送任務至 {worker_url} 失敗：{e}")
        return None

def receive_result(module_name: str, timeout: int = 600):
    """
    等待並從 SQLite 資料庫接收模組結果
    timeout: 等待结果的超时时间（秒），默认10分钟
    """
    # ✅ 针对不同模块设置不同的等待时间
    if module_name == "module5":
        timeout = 900  # module5 等待15分钟
    elif module_name.startswith("module5_"):
        timeout = 600  # module5 相关任务等待10分钟
    else:
        timeout = 120  # 其他模块等待2分钟
    
    print(f"⏰ 等待 {module_name} 结果，最多等待 {timeout} 秒")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            result = fetch_answers([module_name])
            if module_name in result:
                elapsed = time.time() - start_time
                print(f"✅ 收到模組 {module_name} 的結果：{result[module_name]} (等待了 {elapsed:.1f} 秒)")
                return result[module_name]
        except Exception as e:
            print(f"⚠️ 無法取得 {module_name} 結果，錯誤：{e}")

        # 显示等待进度
        elapsed = time.time() - start_time
        if int(elapsed) % 30 == 0:  # 每30秒显示一次进度
            print(f"⏳ 仍在等待 {module_name} 結果... ({elapsed:.0f}/{timeout}秒)")
        
        time.sleep(0.5)  # 稍微增加检查间隔，减少数据库压力

    raise TimeoutError(f"等待模組 {module_name} 結果超時（{timeout}秒）")

def store_result_from_worker(module_name: str, result: Any):
    """此功能保留，但現已透過資料庫處理結果，不再使用"""
    print(f"📥 模組 {module_name} 的結果已由 worker 儲存至資料庫，略過本地記憶體儲存")

def get_available_worker(worker_pool: Dict[str, str], index: int = None):
    """取得可用的 worker URL"""
    if index is not None:
        worker_keys = list(worker_pool.keys())
        worker_key = worker_keys[index % len(worker_keys)]
        return worker_pool[worker_key]
    else:
        # 預設回傳第一個 worker
        return list(worker_pool.values())[0]

# 以下兩個函數目前架構未使用，保留以供擴充
def listen_for_task():
    pass

def send_result_to_master(module_name: str, result: Any):
    pass