# ============================================
# module_runner.py (完全修正版 - 移除依賴處理)
# ============================================
from modules_config import get_modules_config

def run_module(module_name, inputs, user_inputs=None):
    """
    執行指定模組，直接使用 master 傳來的 inputs
    不再在 worker 端處理依賴關係，因為 master 已經準備好了
    """
    user_inputs = user_inputs or {}

    print(f"🔧 [module_runner] 開始執行模組 {module_name}")
    print(f"📥 [module_runner] 輸入資料: {inputs}")
    print(f"👤 [module_runner] 用戶輸入: {user_inputs}")

    try:
        # 載入模組配置
        print("📋 [module_runner] 載入模組配置...")
        modules = get_modules_config(user_inputs)

        if module_name not in modules:
            raise ValueError(f"❌ 找不到模組：{module_name}")

        module = modules[module_name]
        print(f"✅ [module_runner] 模組 {module_name} 配置載入成功")

        # 直接執行模組，不處理依賴（master 已經處理了）
        print(f"🚀 [module_runner] 執行模組函數...")
        result = module["generator"](inputs)

        print(f"✅ [module_runner] 模組 {module_name} 執行完成")
        print(f"📤 [module_runner] 輸出結果: {result}")

        return result

    except Exception as e:
        print(f"❌ [module_runner] 模組 {module_name} 執行失敗：{e}")
        import traceback
        traceback.print_exc()
        raise