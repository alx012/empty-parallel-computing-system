# 分散式計算系統

## 系統概述

這是一個基於 Python 的分散式計算框架，能夠將複雜的計算任務分解成多個相互依賴的模組，並使用多個 Worker 節點進行並行處理。系統具備自動任務調度、依賴管理、歷史記錄和結果重用等功能。

## 主要特色

- **智能任務調度**: 基於 DAG（有向無環圖）自動管理模組依賴關係
- **並行計算**: 支援多 Worker 節點並行處理，突破 GIL 限制
- **歷史記錄管理**: 完整的計算會話記錄、搜尋、比較和重用功能
- **容錯機制**: 支援任務失敗重試和系統恢復
- **模組化設計**: 易於擴展和維護

## 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Master Node   │    │   Worker Node   │    │   Worker Node   │
│                 │    │                 │    │                 │
│  • 任務調度      │◄──►│  • 任務執行       │    │  • 任務執行      │
│  • 依賴管理      │    │  • 結果回傳       │    │  • 結果回傳      │
│  • 結果整合      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                                             
          ▼                                             
┌─────────────────┐                                     
│   SQLite DB     │                                     
│                 │                                     
│  • 計算結果      │                                     
│  • 歷史記錄      │                                     
│  • 會話管理      │                                     
└─────────────────┘                                     
```
# ------------------------分隔線--------------------------- #

## 快速開始

### 1. 環境準備

```bash
# 安裝必要套件
pip install flask requests networkx dask numpy sqlite3

# 選擇性安裝（建議）
pip install waitress  # 更好的 WSGI 伺服器
```

### 2. 啟動 Worker 節點

```bash
# 啟動多個 Worker（分別在不同終端執行）
python worker_server.py 5001
python worker_server.py 5002
python worker_server.py 5003
python worker_server.py 5004
python worker_server.py 5005
```
### 如果要在在單機上開多個虛擬機，就在不同的terminal上輸入指令
### 如果使用實際多台電腦，就要輸入電腦實際的連線名稱

### 3. 啟動 Master 節點

```bash
python master.py
```

### 4. 測試系統健康狀態

```bash
python parallel_test.py
```

# ------------------------分隔線--------------------------- #

## 模組開發指南

### 創建新模組
#### 1. 創建模組檔案 （先將計算模組拉進來modules資料夾裡，然後針對模組去做）
在 `modules/` 目錄下創建您的模組檔案：

```python
# modules/your_module.py
def your_module_function(inputs, user_inputs=None):
    """
    您的模組函數
    
    Args:
        inputs: dict - 包含依賴答案的字典
        user_inputs: dict - 用戶輸入的字典（可選）
        
    Returns:
        dict - 包含輸出答案的字典
    """
    print("===== 您的模組：描述 =====")
    
    # 取得依賴的答案
    if "required_answer" in inputs:
        input_value = inputs["required_answer"]
    
    # 取得用戶輸入
    if user_inputs and "user_param" in user_inputs:
        user_param = user_inputs["user_param"]
    
    # 執行您的計算邏輯
    result = input_value * 2  # 範例計算
    
    print(f"計算結果：{result}")
    
    return {
        "your_answer": result
    }
```

#### 2. 在 modules_config.py 中註冊模組

```python
from modules.your_module import your_module_function

def get_modules_config(user_inputs):
    return {
        "your_module": {
            "id": 依序輸入,
            "requires": ["required_answer"],  # 此模組需要的輸入答案
            "outputs": ["your_answer"],       # 此模組產生的答案
            "generator": lambda inputs: your_module_function(inputs, user_inputs)
        },
        # 添加更多模組...
    }
```

#### 3. 配置用戶輸入

在 `master.py` 中修改 `ask_user_inputs()` 函數：

```python
def ask_user_inputs():
    """收集用戶輸入"""
    param1 = input("請輸入參數1：")
    param2 = int(input("請輸入參數2："))
    
    return {
        "user_param1": param1,
        "user_param2": param2
    }
```

#### 4. 配置 Worker 節點

在 `master.py` 中設定您的 Worker 節點：

```python
worker_pool = {
    "worker1": "http://localhost:5001",
    "worker2": "http://localhost:5002",
    "worker3": "http://localhost:5003",
    # 添加更多 worker...
}
```

# ------------------------分隔線--------------------------- #

### 模組依賴關係範例

```python
# 範例：三個相互依賴的模組
{
    "module_a": {
        "id": 1,
        "requires": [],           # 不依賴其他模組
        "outputs": ["answer1"],
        "generator": module_a_function
    },
    "module_b": {
        "id": 2,
        "requires": ["answer1"],  # 依賴 module_a 的輸出
        "outputs": ["answer2"],
        "generator": module_b_function
    },
    "module_c": {
        "id": 3,
        "requires": ["answer1", "answer2"],  # 依賴多個模組
        "outputs": ["final_result"],
        "generator": module_c_function
    }
}
```

# ------------------------分隔線--------------------------- #

## 系統管理

### 歷史記錄管理

```bash
# 互動式歷史管理
python history_manager.py

# 命令行操作
python history_manager.py list          # 列出會話
python history_manager.py stats         # 顯示統計
python history_manager.py export <id>   # 匯出會話
python history_manager.py import <file> # 匯入會話
```

### 系統監控

```bash
# 檢查 Worker 健康狀態
curl http://localhost:5001/health

# 檢查進程池狀態
curl http://localhost:5001/pool_status

# 檢查背景任務狀態
curl http://localhost:5001/tasks_status
```

# ------------------------分隔線--------------------------- #

## 核心檔案說明

### 控制層
- **master.py**: 主控制器，負責任務調度和流程管理
- **worker_server.py**: Worker 節點伺服器，處理具體計算任務

### 模組層
- **modules_config.py**: 模組配置和註冊
- **module_runner.py**: 模組執行器
- **modules/**: 具體業務模組目錄

### 調度層
- **dag_utils.py**: DAG 建構和拓撲排序
- **transport_utils.py**: Master-Worker 通訊

### 資料層
- **db_utils.py**: 資料庫操作和會話管理
- **history_manager.py**: 歷史記錄管理工具

### 測試工具
- **parallel_test.py**: 並行能力測試工具

# ------------------------分隔線--------------------------- #

## 進階功能
### 智能執行模式
系統支援根據計算複雜度自動選擇本地或分散式執行：

```python
def your_complex_module(inputs, execution_mode="auto"):
    if execution_mode == "auto":
        # 系統自動判斷最佳執行方式
        pass
    elif execution_mode == "local":
        # 強制本地執行
        pass
    elif execution_mode == "distributed":
        # 強制分散式執行
        pass
```

### 計算會話管理
每次計算都會創建一個會話，包含：
- 用戶輸入參數
- 所有模組執行結果
- 執行時間統計
- 錯誤日誌

### 結果重用機制
可以基於歷史計算結果進行新的計算，避免重複運算。

# ------------------------分隔線--------------------------- #

## 故障排除

### 常見問題

1. **Worker 連線失敗**
   ```bash
   # 檢查 Worker 是否正常啟動
   curl http://localhost:5001/health
   ```

2. **任務執行超時**
   - 檢查 `transport_utils.py` 中的超時設定
   - 確認 Worker 資源充足

3. **依賴循環錯誤**
   - 檢查 `modules_config.py` 中的依賴關係
   - 確保沒有循環依賴

4. **資料庫鎖定**
   ```bash
   # 清理資料庫
   rm dag_result.db 
   ```

### 日誌分析
系統提供詳細的執行日誌，包括：
- 任務分派時間戳
- 模組執行耗時
- 錯誤堆疊追蹤

# ------------------------分隔線--------------------------- #

## 最佳實踐

1. **模組設計**
   - 保持模組功能單一
   - 避免過深的依賴鏈
   - 適當使用並行計算

2. **效能優化**
   - 根據計算複雜度選擇執行模式
   - 合理配置 Worker 數量
   - 使用 Dask 處理大數據

3. **錯誤處理**
   - 在模組中加入適當的異常處理
   - 使用系統的重試機制
   - 保存中間結果以便除錯