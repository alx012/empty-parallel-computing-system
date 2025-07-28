#!/usr/bin/env python3
# ============================================
# history_manager.py - 歷史計算結果管理工具
# ============================================

import os
import json
import sys
from datetime import datetime
from db_utils import (
    init_enhanced_db, get_session_list, get_session_results,
    export_session_to_file, import_session_from_file,
    copy_session_results
)

def print_banner():
    """顯示程式橫幅"""
    print("="*60)
    print("🗄️  歷史計算結果管理工具")
    print("📊  管理、查看、匯出計算會話")
    print("="*60)

def format_duration(seconds):
    """格式化時間顯示"""
    if not seconds:
        return "N/A"
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.0f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        return f"{hours}h {remaining_minutes}m"

def list_sessions(limit=20, status=None):
    """列出計算會話"""
    print(f"\n📚 計算會話列表 (最近 {limit} 個)：")
    
    sessions = get_session_list(limit=limit, status=status)
    
    if not sessions:
        print("📝 沒有找到計算會話")
        return []
    
    print("-" * 100)
    print(f"{'序號':<4} {'會話ID':<14} {'描述':<30} {'狀態':<8} {'耗時':<10} {'模組':<8} {'開始時間':<16}")
    print("-" * 100)
    
    for i, session in enumerate(sessions, 1):
        duration = format_duration(session['duration_seconds'])
        modules = f"{session['success_modules']}/{session['total_modules']}"
        start_time = session['start_time'][:16] if session['start_time'] else "N/A"
        description = session['description'][:28] + "..." if len(session['description']) > 30 else session['description']
        
        status_color = "✅" if session['status'] == 'completed' else "⏳" if session['status'] == 'running' else "❌"
        
        print(f"{i:<4} {session['session_id'][:14]:<14} {description:<30} "
              f"{status_color} {session['status']:<6} {duration:<10} {modules:<8} {start_time:<16}")
    
    print("-" * 100)
    return sessions

def show_session_detail(session_id):
    """顯示會話詳細信息"""
    session_data = get_session_results(session_id)
    if not session_data:
        print(f"❌ 找不到會話：{session_id}")
        return None
    
    print(f"\n📋 會話詳細資料")
    print("="*60)
    print(f"🆔 會話ID：{session_data['session_id']}")
    print(f"📝 描述：{session_data['description']}")
    print(f"👤 用戶輸入：{json.dumps(session_data['user_inputs'], ensure_ascii=False)}")
    print(f"🏷️ 標籤：{', '.join(session_data['tags']) if session_data['tags'] else '無'}")
    print(f"📅 開始時間：{session_data['start_time']}")
    print(f"📅 結束時間：{session_data['end_time'] or '進行中'}")
    print(f"⏱️ 耗時：{format_duration(session_data['duration_seconds'])}")
    print(f"📊 狀態：{session_data['status']}")
    print(f"🧩 模組統計：{session_data['success_modules']}/{session_data['total_modules']}")
    
    if session_data['final_result']:
        print(f"🎯 最終結果：{json.dumps(session_data['final_result'], ensure_ascii=False)}")
    
    print(f"\n🧩 各模組執行詳情：")
    print("-" * 80)
    print(f"{'模組ID':<12} {'執行順序':<8} {'耗時':<10} {'狀態':<8} {'結果摘要':<30}")
    print("-" * 80)
    
    for module_id in sorted(session_data['modules'].keys(), key=lambda x: session_data['modules'][x]['execution_order']):
        module_data = session_data['modules'][module_id]
        duration = format_duration(module_data['duration_seconds'])
        order = module_data['execution_order']
        status = "✅" if module_data['status'] == 'success' else "❌"
        
        # 結果摘要
        result = module_data['result']
        if isinstance(result, dict):
            result_summary = f"{len(result)} 個鍵值"
            if len(result) <= 3:
                result_summary = str(result)[:28] + "..." if len(str(result)) > 30 else str(result)
        else:
            result_summary = str(result)[:28] + "..." if len(str(result)) > 30 else str(result)
        
        print(f"{module_id:<12} {order:<8} {duration:<10} {status} {module_data['status']:<6} {result_summary:<30}")
    
    print("-" * 80)
    return session_data

def export_session_interactive():
    """互動式匯出會話"""
    sessions = list_sessions(limit=10)
    if not sessions:
        return
    
    while True:
        choice = input(f"\n請選擇要匯出的會話 (1-{len(sessions)}) 或 'q' 退出：").strip()
        
        if choice.lower() == 'q':
            return
        
        if not choice.isdigit() or not (1 <= int(choice) <= len(sessions)):
            print("❌ 無效的選擇")
            continue
        
        selected_session = sessions[int(choice) - 1]
        session_id = selected_session['session_id']
        
        # 顯示會話詳情
        show_session_detail(session_id)
        
        # 確認匯出
        confirm = input(f"\n確定要匯出會話 {session_id[:12]}...？(y/N)：").strip().lower()
        if confirm != 'y':
            continue
        
        # 選擇匯出路徑
        default_filename = f"session_{session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        custom_path = input(f"匯出檔案名稱 (預設: {default_filename})：").strip()
        
        file_path = custom_path if custom_path else default_filename
        
        try:
            actual_path = export_session_to_file(session_id, file_path)
            print(f"✅ 成功匯出到：{actual_path}")
            
            # 驗證檔案
            file_size = os.path.getsize(actual_path)
            print(f"📁 檔案大小：{file_size:,} bytes")
            
            break
            
        except Exception as e:
            print(f"❌ 匯出失敗：{e}")

def import_session_interactive():
    """互動式匯入會話"""
    print("\n📥 匯入計算會話")
    
    file_path = input("請輸入要匯入的 JSON 檔案路徑：").strip()
    
    if not file_path:
        print("❌ 未指定檔案路徑")
        return
    
    if not os.path.exists(file_path):
        print(f"❌ 檔案不存在：{file_path}")
        return
    
    try:
        # 預覽檔案內容
        with open(file_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print(f"\n📋 檔案內容預覽：")
        print(f"🆔 會話ID：{session_data.get('session_id', 'N/A')}")
        print(f"📝 描述：{session_data.get('description', 'N/A')}")
        print(f"📅 時間：{session_data.get('start_time', 'N/A')}")
        print(f"🧩 模組數：{len(session_data.get('modules', {}))}")
        
        confirm = input(f"\n確定要匯入這個會話嗎？(y/N)：").strip().lower()
        if confirm != 'y':
            print("❌ 取消匯入")
            return
        
        session_id = import_session_from_file(file_path)
        print(f"✅ 成功匯入會話：{session_id}")
        
    except Exception as e:
        print(f"❌ 匯入失敗：{e}")

def compare_sessions():
    """比較兩個會話"""
    sessions = list_sessions(limit=10)
    if len(sessions) < 2:
        print("❌ 至少需要 2 個會話才能比較")
        return
    
    print(f"\n🔍 選擇要比較的會話")
    
    # 選擇第一個會話
    choice1 = input(f"選擇第一個會話 (1-{len(sessions)})：").strip()
    if not choice1.isdigit() or not (1 <= int(choice1) <= len(sessions)):
        print("❌ 無效的選擇")
        return
    
    # 選擇第二個會話
    choice2 = input(f"選擇第二個會話 (1-{len(sessions)})：").strip()
    if not choice2.isdigit() or not (1 <= int(choice2) <= len(sessions)):
        print("❌ 無效的選擇")
        return
    
    if choice1 == choice2:
        print("❌ 不能選擇相同的會話")
        return
    
    session1 = get_session_results(sessions[int(choice1) - 1]['session_id'])
    session2 = get_session_results(sessions[int(choice2) - 1]['session_id'])
    
    print(f"\n📊 會話比較")
    print("="*80)
    print(f"{'項目':<20} {'會話1':<25} {'會話2':<25}")
    print("-"*80)
    print(f"{'會話ID':<20} {session1['session_id'][:22]:<25} {session2['session_id'][:22]:<25}")
    print(f"{'描述':<20} {session1['description'][:22]:<25} {session2['description'][:22]:<25}")
    print(f"{'耗時':<20} {format_duration(session1['duration_seconds']):<25} {format_duration(session2['duration_seconds']):<25}")
    print(f"{'成功模組':<20} {session1['success_modules']:<25} {session2['success_modules']:<25}")
    print(f"{'總模組':<20} {session1['total_modules']:<25} {session2['total_modules']:<25}")
    print(f"{'狀態':<20} {session1['status']:<25} {session2['status']:<25}")
    
    # 比較用戶輸入
    print(f"\n👤 用戶輸入比較：")
    inputs1 = session1['user_inputs']
    inputs2 = session2['user_inputs']
    
    all_keys = set(inputs1.keys()) | set(inputs2.keys())
    for key in sorted(all_keys):
        val1 = inputs1.get(key, "未設定")
        val2 = inputs2.get(key, "未設定")
        same = "✅" if val1 == val2 else "❌"
        print(f"  {key:<15}: {str(val1):<15} vs {str(val2):<15} {same}")
    
    # 比較最終結果
    if session1['final_result'] and session2['final_result']:
        print(f"\n🎯 最終結果比較：")
        result1 = session1['final_result']
        result2 = session2['final_result']
        same = "✅" if result1 == result2 else "❌"
        print(f"  會話1: {result1}")
        print(f"  會話2: {result2}")
        print(f"  相同: {same}")

def cleanup_sessions():
    """清理會話（刪除舊的或失敗的會話）"""
    print("\n🧹 會話清理")
    print("⚠️ 此操作將永久刪除選定的會話，請謹慎操作！")
    
    # 顯示失敗和舊的會話
    all_sessions = get_session_list(limit=50)
    
    failed_sessions = [s for s in all_sessions if s['status'] != 'completed']
    old_sessions = [s for s in all_sessions if s['status'] == 'completed'][-20:]  # 保留最近20個成功的
    
    print(f"\n❌ 失敗的會話 ({len(failed_sessions)} 個)：")
    if failed_sessions:
        for i, session in enumerate(failed_sessions, 1):
            print(f"  {i}. {session['session_id'][:12]} - {session['description'][:30]} ({session['status']})")
    else:
        print("  無失敗的會話")
    
    print(f"\n📅 較舊的會話 ({len(all_sessions) - len(old_sessions)} 個可清理)：")
    if len(all_sessions) > len(old_sessions):
        old_to_clean = all_sessions[len(old_sessions):]
        for i, session in enumerate(old_to_clean[:10], 1):  # 只顯示前10個
            print(f"  {i}. {session['session_id'][:12]} - {session['description'][:30]}")
        if len(old_to_clean) > 10:
            print(f"  ... 還有 {len(old_to_clean) - 10} 個")
    else:
        print("  無較舊的會話需要清理")
    
    print(f"\n⚠️ 清理選項：")
    print("1. 清理所有失敗的會話")
    print("2. 清理較舊的會話（保留最近20個成功的）")
    print("3. 清理所有會話（危險操作）")
    print("4. 取消")
    
    choice = input("請選擇 (1-4)：").strip()
    
    if choice == '4':
        print("❌ 取消清理")
        return
    
    if choice not in ['1', '2', '3']:
        print("❌ 無效的選擇")
        return
    
    # 最後確認
    confirm = input(f"⚠️ 確定要執行清理操作 {choice} 嗎？這將永久刪除選定的會話！(yes/N)：").strip()
    if confirm != 'yes':
        print("❌ 取消清理")
        return
    
    # 執行清理（這裡需要實作資料庫刪除邏輯）
    print("🚧 清理功能開發中，為了安全暫時不實作自動刪除")
    print("💡 建議：手動備份重要會話後，直接刪除資料庫檔案重新開始")

def search_sessions():
    """搜尋會話"""
    print("\n🔍 搜尋計算會話")
    
    search_term = input("請輸入搜尋關鍵字（描述、標籤或會話ID）：").strip()
    if not search_term:
        print("❌ 未輸入搜尋關鍵字")
        return
    
    all_sessions = get_session_list(limit=100)
    
    # 搜尋匹配的會話
    matched_sessions = []
    for session in all_sessions:
        if (search_term.lower() in session['description'].lower() or
            search_term.lower() in session['session_id'].lower() or
            any(search_term.lower() in tag.lower() for tag in session['tags'])):
            matched_sessions.append(session)
    
    if not matched_sessions:
        print(f"📝 沒有找到包含 '{search_term}' 的會話")
        return
    
    print(f"\n🎯 找到 {len(matched_sessions)} 個匹配的會話：")
    print("-" * 80)
    print(f"{'序號':<4} {'會話ID':<14} {'描述':<35} {'狀態':<8} {'時間':<16}")
    print("-" * 80)
    
    for i, session in enumerate(matched_sessions, 1):
        description = session['description'][:33] + "..." if len(session['description']) > 35 else session['description']
        start_time = session['start_time'][:16] if session['start_time'] else "N/A"
        status_color = "✅" if session['status'] == 'completed' else "⏳" if session['status'] == 'running' else "❌"
        
        print(f"{i:<4} {session['session_id'][:14]:<14} {description:<35} "
              f"{status_color} {session['status']:<6} {start_time:<16}")
    
    print("-" * 80)
    
    # 允許查看詳情
    choice = input(f"\n查看詳細資料？輸入序號 (1-{len(matched_sessions)}) 或按 Enter 跳過：").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(matched_sessions):
        selected_session = matched_sessions[int(choice) - 1]
        show_session_detail(selected_session['session_id'])

def main_menu():
    """主選單"""
    init_enhanced_db()  # 確保資料庫已初始化
    
    while True:
        print_banner()
        print("\n📋 選擇操作：")
        print("1. 📚 列出所有會話")
        print("2. 🔍 搜尋會話")
        print("3. 📋 查看會話詳情")
        print("4. 📤 匯出會話")
        print("5. 📥 匯入會話")
        print("6. 🔍 比較會話")
        print("7. 🧹 清理會話")
        print("8. 📊 統計資訊")
        print("9. ❌ 退出")
        print("-" * 40)
        
        choice = input("請選擇操作 (1-9)：").strip()
        
        if choice == '1':
            list_sessions()
            
        elif choice == '2':
            search_sessions()
            
        elif choice == '3':
            sessions = list_sessions(limit=10)
            if sessions:
                session_choice = input(f"\n請選擇會話 (1-{len(sessions)})：").strip()
                if session_choice.isdigit() and 1 <= int(session_choice) <= len(sessions):
                    selected_session = sessions[int(session_choice) - 1]
                    show_session_detail(selected_session['session_id'])
                else:
                    print("❌ 無效的選擇")
            
        elif choice == '4':
            export_session_interactive()
            
        elif choice == '5':
            import_session_interactive()
            
        elif choice == '6':
            compare_sessions()
            
        elif choice == '7':
            cleanup_sessions()
            
        elif choice == '8':
            show_statistics()
            
        elif choice == '9':
            print("👋 再見！")
            break
            
        else:
            print("❌ 無效的選擇，請輸入 1-9")
        
        input("\n按 Enter 鍵繼續...")

def show_statistics():
    """顯示統計資訊"""
    sessions = get_session_list(limit=1000)  # 取得所有會話
    
    if not sessions:
        print("📝 沒有計算會話")
        return
    
    print("\n📊 計算會話統計")
    print("="*50)
    
    # 基本統計
    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s['status'] == 'completed'])
    failed_sessions = len([s for s in sessions if s['status'] != 'completed'])
    
    print(f"📚 總會話數：{total_sessions}")
    print(f"✅ 成功完成：{completed_sessions} ({completed_sessions/total_sessions*100:.1f}%)")
    print(f"❌ 失敗/未完成：{failed_sessions} ({failed_sessions/total_sessions*100:.1f}%)")
    
    # 時間統計
    completed_with_time = [s for s in sessions if s['status'] == 'completed' and s['duration_seconds']]
    if completed_with_time:
        durations = [s['duration_seconds'] for s in completed_with_time]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        print(f"\n⏱️ 執行時間統計（成功的會話）：")
        print(f"  平均耗時：{format_duration(avg_duration)}")
        print(f"  最長耗時：{format_duration(max_duration)}")
        print(f"  最短耗時：{format_duration(min_duration)}")
    
    # 模組統計
    total_modules = sum(s['total_modules'] for s in sessions if s['total_modules'])
    success_modules = sum(s['success_modules'] for s in sessions if s['success_modules'])
    
    if total_modules > 0:
        print(f"\n🧩 模組執行統計：")
        print(f"  總模組執行次數：{total_modules}")
        print(f"  成功執行次數：{success_modules}")
        print(f"  成功率：{success_modules/total_modules*100:.1f}%")
    
    # 最近活動
    recent_sessions = sessions[:5]  # 最近5個
    print(f"\n📅 最近活動：")
    for session in recent_sessions:
        status_icon = "✅" if session['status'] == 'completed' else "❌"
        print(f"  {status_icon} {session['start_time'][:16]} - {session['description'][:40]}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式
        command = sys.argv[1].lower()
        
        if command == 'list':
            init_enhanced_db()
            list_sessions()
            
        elif command == 'stats':
            init_enhanced_db()
            show_statistics()
            
        elif command == 'export' and len(sys.argv) > 2:
            init_enhanced_db()
            session_id = sys.argv[2]
            try:
                file_path = export_session_to_file(session_id)
                print(f"✅ 匯出成功：{file_path}")
            except Exception as e:
                print(f"❌ 匯出失敗：{e}")
                
        elif command == 'import' and len(sys.argv) > 2:
            init_enhanced_db()
            file_path = sys.argv[2]
            try:
                session_id = import_session_from_file(file_path)
                print(f"✅ 匯入成功：{session_id}")
            except Exception as e:
                print(f"❌ 匯入失敗：{e}")
                
        else:
            print("❌ 無效的命令")
            print("用法：")
            print("  python history_manager.py list          # 列出會話")
            print("  python history_manager.py stats         # 顯示統計")
            print("  python history_manager.py export <id>   # 匯出會話")
            print("  python history_manager.py import <file> # 匯入會話")
            print("  python history_manager.py               # 互動模式")
    else:
        # 互動模式
        main_menu()