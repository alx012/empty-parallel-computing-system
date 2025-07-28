#下方輸入：所有的 import

#----------------分隔線-------------------#
#下方輸入：所有模組的 wrapper 函數以及 return 的 require 和 output 內容
def get_modules_config(user_inputs):
    """
    獲取模組配置 - 範本版本
    請在此處定義您的模組配置
    每個模組需要包含：
    - id: 模組編號
    - requires: 依賴的答案列表
    - outputs: 產生的答案列表  
    - generator: 模組執行函數
    """
    
    # 示例模組配置（請根據實際需求修改）
    return {
        # "your_module_name": {
        #     "id": 1,
        #     "requires": [],  # 此模組需要的輸入答案，如 ["answer1", "answer2"]
        #     "outputs": ["answer1"],  # 此模組產生的答案
        #     "generator": your_module_function
        # }
    }