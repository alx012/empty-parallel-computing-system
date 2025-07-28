# ============================================
# enhanced_db_utils.py - 增強版資料庫工具（支援歷史計算記錄）
# ============================================
import sqlite3
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_FILE = 'dag_result.db'

class CalculationSession:
    """計算會話管理器"""
    def __init__(self, session_id: str = None, user_inputs: Dict = None, description: str = ""):
        self.session_id = session_id or str(uuid.uuid4())
        self.user_inputs = user_inputs or {}
        self.description = description
        self.start_time = datetime.now()
        self.end_time = None
        self.status = "running"
        
    def complete(self):
        """標記計算完成"""
        self.end_time = datetime.now()
        self.status = "completed"
        
    def get_duration(self):
        """取得計算耗時"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

# 全局會話管理
current_session = None

def init_enhanced_db():
    """初始化增強版 SQLite 資料庫"""
    print("\n🔄 初始化增強版資料庫 ...")
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # 原有的即時結果表（保持向後相容）
        c.execute('''
            CREATE TABLE IF NOT EXISTS module_result (
                module_id TEXT PRIMARY KEY,
                result_json TEXT
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS result_index (
                module TEXT PRIMARY KEY,
                location TEXT,
                result_json TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ✨ 新增：計算會話表
        c.execute('''
            CREATE TABLE IF NOT EXISTS calculation_sessions (
                session_id TEXT PRIMARY KEY,
                description TEXT,
                user_inputs_json TEXT,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT,
                duration_seconds REAL,
                total_modules INTEGER,
                success_modules INTEGER,
                final_result_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # ✨ 新增：歷史模組結果表
        c.execute('''
            CREATE TABLE IF NOT EXISTS historical_module_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                module_id TEXT,
                module_name TEXT,
                result_json TEXT,
                execution_order INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                duration_seconds REAL,
                status TEXT,
                error_message TEXT,
                FOREIGN KEY (session_id) REFERENCES calculation_sessions (session_id)
            )
        ''')
        
        # ✨ 新增：會話標籤表（便於分類管理）
        c.execute('''
            CREATE TABLE IF NOT EXISTS session_tags (
                session_id TEXT,
                tag TEXT,
                PRIMARY KEY (session_id, tag),
                FOREIGN KEY (session_id) REFERENCES calculation_sessions (session_id)
            )
        ''')
        
        # 建立索引提升查詢效能
        c.execute('CREATE INDEX IF NOT EXISTS idx_historical_session_module ON historical_module_results (session_id, module_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_time ON calculation_sessions (start_time)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_status ON calculation_sessions (status)')
        
        # 清空即時結果表（新計算開始）
        c.execute('DELETE FROM module_result')
        c.execute('DELETE FROM result_index')
        conn.commit()
    
    print("✅ 增強版資料庫初始化完成")

def start_calculation_session(user_inputs: Dict, description: str = "", tags: List[str] = None) -> str:
    """開始新的計算會話"""
    global current_session
    
    current_session = CalculationSession(
        user_inputs=user_inputs,
        description=description
    )
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # 插入會話記錄
        c.execute('''
            INSERT INTO calculation_sessions 
            (session_id, description, user_inputs_json, start_time, status, total_modules, success_modules)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            current_session.session_id,
            description,
            json.dumps(user_inputs, ensure_ascii=False),
            current_session.start_time,
            "running",
            0,
            0
        ))
        
        # 插入標籤
        if tags:
            for tag in tags:
                c.execute('INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?, ?)', 
                         (current_session.session_id, tag))
        
        conn.commit()
    
    print(f"🚀 開始計算會話：{current_session.session_id}")
    print(f"📝 描述：{description}")
    print(f"👤 用戶輸入：{user_inputs}")
    
    return current_session.session_id

def save_result(module_id: str, result_dict: Dict, execution_order: int = 0, 
                start_time: datetime = None, end_time: datetime = None):
    """儲存模組結果（同時儲存到即時表和歷史表）"""
    global current_session
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        result_json = json.dumps(result_dict, ensure_ascii=False, default=str)
        module_id_str = str(module_id)
        
        # 1. 儲存到即時結果表（保持原有功能）
        c.execute('''
            INSERT OR REPLACE INTO module_result (module_id, result_json)
            VALUES (?, ?)
        ''', (module_id_str, result_json))
        
        # 2. 儲存到歷史結果表
        if current_session:
            duration = None
            if start_time and end_time:
                duration = (end_time - start_time).total_seconds()
            
            c.execute('''
                INSERT INTO historical_module_results 
                (session_id, module_id, module_name, result_json, execution_order, 
                 start_time, end_time, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_session.session_id,
                module_id_str,
                module_id_str,  # module_name 暫時等於 module_id
                result_json,
                execution_order,
                start_time,
                end_time,
                duration,
                "success"
            ))
            
            # 更新會話統計
            c.execute('''
                UPDATE calculation_sessions 
                SET success_modules = success_modules + 1,
                    total_modules = CASE WHEN total_modules < ? THEN ? ELSE total_modules END
                WHERE session_id = ?
            ''', (execution_order + 1, execution_order + 1, current_session.session_id))
        
        conn.commit()
    
    print(f"💾 模組 {module_id} 結果已儲存（會話：{current_session.session_id if current_session else 'N/A'}）")

def complete_calculation_session(final_result: Any = None, total_modules: int = 0):
    """完成計算會話"""
    global current_session
    
    if not current_session:
        print("⚠️ 沒有活躍的計算會話")
        return
    
    current_session.complete()
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        final_result_json = None
        if final_result:
            final_result_json = json.dumps(final_result, ensure_ascii=False, default=str)
        
        c.execute('''
            UPDATE calculation_sessions 
            SET end_time = ?, status = ?, duration_seconds = ?, final_result_json = ?,
                total_modules = CASE WHEN total_modules < ? THEN ? ELSE total_modules END
            WHERE session_id = ?
        ''', (
            current_session.end_time,
            "completed",
            current_session.get_duration(),
            final_result_json,
            total_modules,
            total_modules,
            current_session.session_id
        ))
        
        conn.commit()
    
    duration = current_session.get_duration()
    print(f"✅ 計算會話完成：{current_session.session_id}")
    print(f"⏱️ 總耗時：{duration:.2f} 秒")
    
    current_session = None

def get_session_list(limit: int = 20, status: str = None, tag: str = None) -> List[Dict]:
    """取得計算會話列表"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        query = '''
            SELECT s.session_id, s.description, s.start_time, s.end_time, s.status, 
                   s.duration_seconds, s.total_modules, s.success_modules,
                   GROUP_CONCAT(t.tag) as tags
            FROM calculation_sessions s
            LEFT JOIN session_tags t ON s.session_id = t.session_id
        '''
        params = []
        
        conditions = []
        if status:
            conditions.append("s.status = ?")
            params.append(status)
        
        if tag:
            conditions.append("t.tag = ?")
            params.append(tag)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY s.session_id ORDER BY s.start_time DESC LIMIT ?"
        params.append(limit)
        
        c.execute(query, params)
        rows = c.fetchall()
        
        sessions = []
        for row in rows:
            sessions.append({
                'session_id': row[0],
                'description': row[1],
                'start_time': row[2],
                'end_time': row[3],
                'status': row[4],
                'duration_seconds': row[5],
                'total_modules': row[6],
                'success_modules': row[7],
                'tags': row[8].split(',') if row[8] else []
            })
        
        return sessions

def get_session_results(session_id: str) -> Dict:
    """取得指定會話的完整結果"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # 取得會話基本信息
        c.execute('''
            SELECT session_id, description, user_inputs_json, start_time, end_time,
                   status, duration_seconds, total_modules, success_modules, final_result_json
            FROM calculation_sessions WHERE session_id = ?
        ''', (session_id,))
        
        session_row = c.fetchone()
        if not session_row:
            return None
        
        # 取得所有模組結果
        c.execute('''
            SELECT module_id, module_name, result_json, execution_order, 
                   start_time, end_time, duration_seconds, status
            FROM historical_module_results 
            WHERE session_id = ? 
            ORDER BY execution_order
        ''', (session_id,))
        
        module_rows = c.fetchall()
        
        # 取得標籤
        c.execute('SELECT tag FROM session_tags WHERE session_id = ?', (session_id,))
        tags = [row[0] for row in c.fetchall()]
        
        # 組織結果
        session_info = {
            'session_id': session_row[0],
            'description': session_row[1],
            'user_inputs': json.loads(session_row[2]) if session_row[2] else {},
            'start_time': session_row[3],
            'end_time': session_row[4],
            'status': session_row[5],
            'duration_seconds': session_row[6],
            'total_modules': session_row[7],
            'success_modules': session_row[8],
            'final_result': json.loads(session_row[9]) if session_row[9] else None,
            'tags': tags,
            'modules': {}
        }
        
        for module_row in module_rows:
            module_id = module_row[0]
            session_info['modules'][module_id] = {
                'module_name': module_row[1],
                'result': json.loads(module_row[2]) if module_row[2] else None,
                'execution_order': module_row[3],
                'start_time': module_row[4],
                'end_time': module_row[5],
                'duration_seconds': module_row[6],
                'status': module_row[7]
            }
        
        return session_info

def export_session_to_file(session_id: str, file_path: str = None) -> str:
    """將會話結果匯出到 JSON 檔案"""
    session_data = get_session_results(session_id)
    if not session_data:
        raise ValueError(f"找不到會話：{session_id}")
    
    if not file_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = f"calculation_session_{session_id[:8]}_{timestamp}.json"
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"📄 會話結果已匯出到：{file_path}")
    return file_path

def import_session_from_file(file_path: str) -> str:
    """從 JSON 檔案匯入會話結果"""
    with open(file_path, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    session_id = session_data['session_id']
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # 插入會話記錄
        c.execute('''
            INSERT OR REPLACE INTO calculation_sessions 
            (session_id, description, user_inputs_json, start_time, end_time,
             status, duration_seconds, total_modules, success_modules, final_result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            session_data['description'],
            json.dumps(session_data['user_inputs']),
            session_data['start_time'],
            session_data['end_time'],
            session_data['status'],
            session_data['duration_seconds'],
            session_data['total_modules'],
            session_data['success_modules'],
            json.dumps(session_data['final_result']) if session_data['final_result'] else None
        ))
        
        # 插入模組結果
        for module_id, module_data in session_data['modules'].items():
            c.execute('''
                INSERT OR REPLACE INTO historical_module_results 
                (session_id, module_id, module_name, result_json, execution_order,
                 start_time, end_time, duration_seconds, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id,
                module_id,
                module_data['module_name'],
                json.dumps(module_data['result']),
                module_data['execution_order'],
                module_data['start_time'],
                module_data['end_time'],
                module_data['duration_seconds'],
                module_data['status']
            ))
        
        # 插入標籤
        for tag in session_data['tags']:
            c.execute('INSERT OR IGNORE INTO session_tags (session_id, tag) VALUES (?, ?)', 
                     (session_id, tag))
        
        conn.commit()
    
    print(f"📥 會話結果已匯入：{session_id}")
    return session_id

def copy_session_results(source_session_id: str, target_inputs: Dict, description: str = "") -> Dict:
    """複製指定會話的結果作為新計算的輸入"""
    source_data = get_session_results(source_session_id)
    if not source_data:
        raise ValueError(f"找不到來源會話：{source_session_id}")
    
    # 提取所有模組的輸出作為答案映射
    answer_map = {}
    for module_id, module_data in source_data['modules'].items():
        result = module_data['result']
        if isinstance(result, dict):
            answer_map.update(result)
    
    # 如果有最終結果，也加入
    if source_data['final_result']:
        answer_map.update(source_data['final_result'])
    
    print(f"📋 從會話 {source_session_id} 複製了 {len(answer_map)} 個結果")
    print(f"🔑 可用的結果鍵：{list(answer_map.keys())}")
    
    return answer_map

# 保持向後相容的原有函數
def register_result_location(module_name, result, worker_url):
    """紀錄模組的計算結果與所在 Worker（保持向後相容）"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        result_json = json.dumps(result, ensure_ascii=False, default=str)
        module_name = str(module_name)
        c.execute('''
            INSERT OR REPLACE INTO result_index (module, location, result_json)
            VALUES (?, ?, ?)
        ''', (module_name, worker_url, result_json))
        conn.commit()

def fetch_answers(required_modules):
    """從資料庫擷取模組結果（保持向後相容）"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        collected = {}

        while True:
            c.execute('SELECT module_id, result_json FROM module_result')
            rows = c.fetchall()
            for module_id, result_json in rows:
                if module_id not in collected:
                    result_dict = json.loads(result_json)
                    collected[module_id] = result_dict

            if all(module in collected for module in required_modules):
                return {m: collected[m] for m in required_modules}

            time.sleep(0.1)

def get_all_results():
    """取回全部模組的結果資料（保持向後相容）"""
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT module_id, result_json FROM module_result ORDER BY module_id')
        return [(module_id, json.loads(result_json)) for module_id, result_json in c.fetchall()]


#----------------分隔線-------------------#

def get_final_result(final_module_name="final_module"):
    """
    取回最終結果 - 通用版本
    final_module_name: 最終模組的名稱，請根據實際情況修改
    """
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('SELECT result_json FROM module_result WHERE module_id = ?', ("final_module_name",))
        result = c.fetchone()
        return json.loads(result[0]) if result else None

#----------------分隔線-------------------#

# 舊函數名稱保持相容
init_db = init_enhanced_db