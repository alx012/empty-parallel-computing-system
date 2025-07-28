#!/usr/bin/env python3
# ============================================
# parallel_test.py - 測試 Worker 並行處理能力
# ============================================

import requests
import threading
import time
from datetime import datetime
import json

# Worker URLs
workers = [
    "http://localhost:5001",
    "http://localhost:5002", 
    "http://localhost:5003",
    "http://localhost:5004",
    "http://localhost:5005"
]

def test_worker_health(worker_url, worker_id):
    """測試單個 Worker 的健康狀態"""
    try:
        start_time = time.time()
        response = requests.get(f"{worker_url}/health", timeout=5)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Worker {worker_id} ({worker_url}): {data['status']} - 響應時間: {duration:.3f}s - 時間: {data.get('current_time', 'N/A')}")
            return True
        else:
            print(f"❌ Worker {worker_id} ({worker_url}): HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Worker {worker_id} ({worker_url}): 連線失敗 - {e}")
        return False

def test_worker_compute(worker_url, worker_id, task_duration=3):
    """測試 Worker 的計算處理能力"""
    try:
        start_time = time.time()
        print(f"🚀 Worker {worker_id} 開始測試計算 - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        # 模擬一個簡單的計算任務
        test_task = {
            "module_name": "test_parallel",
            "input_data": {
                "task_id": worker_id,
                "duration": task_duration,
                "test_mode": True
            },
            "execution_id": f"parallel_test_{worker_id}_{int(time.time())}"
        }
        
        response = requests.post(
            f"{worker_url}/compute", 
            json=test_task,
            timeout=10
        )
        
        duration = time.time() - start_time
        end_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        if response.status_code == 200:
            print(f"✅ Worker {worker_id} 計算完成 - {end_time} - 耗時: {duration:.3f}s")
            return True
        else:
            print(f"❌ Worker {worker_id} 計算失敗 - HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        end_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"❌ Worker {worker_id} 計算異常 - {end_time} - 耗時: {duration:.3f}s - 錯誤: {e}")
        return False

def test_parallel_health():
    """測試所有 Worker 的並行健康檢查"""
    print("\n" + "="*60)
    print("🔍 測試 1: 並行健康檢查")
    print("="*60)
    
    threads = []
    results = []
    
    def health_test_wrapper(worker_url, worker_id):
        result = test_worker_health(worker_url, worker_id)
        results.append((worker_id, result))
    
    # 同時啟動所有健康檢查
    start_time = time.time()
    for i, worker_url in enumerate(workers):
        thread = threading.Thread(target=health_test_wrapper, args=(worker_url, i+1))
        thread.start()
        threads.append(thread)
    
    # 等待所有線程完成
    for thread in threads:
        thread.join()
    
    total_duration = time.time() - start_time
    success_count = sum(1 for _, success in results if success)
    
    print(f"\n📊 健康檢查結果:")
    print(f"  成功: {success_count}/{len(workers)} 個 Worker")
    print(f"  總耗時: {total_duration:.3f}s")
    print(f"  並行效果: {'✅ 良好' if total_duration < 2 else '❌ 可能有問題'}")
    
    return success_count == len(workers)

def test_parallel_compute():
    """測試所有 Worker 的並行計算"""
    print("\n" + "="*60) 
    print("🔍 測試 2: 並行計算處理")
    print("="*60)
    
    threads = []
    results = []
    
    def compute_test_wrapper(worker_url, worker_id):
        result = test_worker_compute(worker_url, worker_id, task_duration=2)
        results.append((worker_id, result))
    
    # 同時啟動所有計算任務
    print(f"🕐 測試開始時間: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    start_time = time.time()
    
    for i, worker_url in enumerate(workers):
        thread = threading.Thread(target=compute_test_wrapper, args=(worker_url, i+1))
        thread.start()
        threads.append(thread)
    
    # 等待所有線程完成
    for thread in threads:
        thread.join()
    
    total_duration = time.time() - start_time
    print(f"🕐 測試結束時間: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    
    success_count = sum(1 for _, success in results if success)
    
    print(f"\n📊 並行計算結果:")
    print(f"  成功: {success_count}/{len(workers)} 個 Worker")
    print(f"  總耗時: {total_duration:.3f}s")
    
    # 判斷是否真正並行（應該接近單個任務時間，而不是所有任務時間總和）
    expected_parallel_time = 3.0  # 單個任務約 2 秒 + 網路延遲
    expected_sequential_time = len(workers) * 2.5  # 如果是依序執行
    
    if total_duration < expected_parallel_time:
        print(f"  並行效果: ✅ 優秀 (真正並行執行)")
    elif total_duration < expected_sequential_time / 2:
        print(f"  並行效果: ⚠️ 一般 (部分並行)")
    else:
        print(f"  並行效果: ❌ 差 (可能依序執行)")
        print(f"    預期並行時間: ~{expected_parallel_time}s")
        print(f"    預期依序時間: ~{expected_sequential_time}s")
        print(f"    實際耗時: {total_duration:.3f}s")
    
    return success_count > 0

def main():
    """主測試函數"""
    print("🧪 Worker 並行處理能力測試")
    print(f"🕐 測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 測試目標: {len(workers)} 個 Worker")
    
    # 測試 1: 健康檢查
    health_ok = test_parallel_health()
    
    if not health_ok:
        print("\n❌ 健康檢查失敗，請確認所有 Worker 都已啟動")
        return
    
    # 測試 2: 並行計算（注意：這會失敗，因為 Worker 不認識 test_parallel 模組）
    print("\n⚠️ 注意：計算測試可能會失敗（因為沒有 test_parallel 模組），但重點是觀察時間戳")
    test_parallel_compute()
    
    print("\n" + "="*60)
    print("🎯 測試重點：觀察時間戳是否同時開始")
    print("  - 如果時間戳幾乎相同 → 並行正常")
    print("  - 如果時間戳依序遞增 → 依序執行，需要檢查 threaded=True")
    print("="*60)

if __name__ == "__main__":
    main()