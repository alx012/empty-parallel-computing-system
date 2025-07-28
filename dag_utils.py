import networkx as nx
from collections import defaultdict, deque

def build_dag(modules):
    """
    建構 DAG 並回傳 (dag物件, 拓撲排序的模組執行順序)
    modules: dict，每個模組需包含 'requires'（輸入依賴）與 'outputs'（輸出鍵）
    """
    dag = nx.DiGraph()
    answer_to_module = {}

    # 將每個模組及其輸出加入圖中
    for module_id, module in modules.items():
        module_id_str = str(module_id)
        dag.add_node(module_id_str)
        for output in module.get("outputs", []):
            answer_to_module[output] = module_id_str

    # 加入依賴邊
    for module_id, module in modules.items():
        module_id_str = str(module_id)
        for req in module.get("requires", []):
            if req in answer_to_module:
                dag.add_edge(answer_to_module[req], module_id_str)

    # 檢查循環依賴
    if not nx.is_directed_acyclic_graph(dag):
        raise ValueError("[DAG 錯誤] 模組之間存在循環依賴，請檢查 requires / outputs 設定")

    execution_order = list(nx.topological_sort(dag))
    print(f"[DAG] 拓撲排序執行順序：{execution_order}")
    return dag, execution_order

def get_execution_order(modules_config):
    """
    若無 outputs 欄位，此備用排序僅根據 requires 做拓撲排序。
    modules_config: dict，每個模組需包含 'requires'
    """
    graph = defaultdict(list)
    indegree = defaultdict(int)

    for name, config in modules_config.items():
        name_str = str(name)
        for dep in config.get("requires", []):
            graph[dep].append(name_str)
            indegree[name_str] += 1
        indegree.setdefault(name_str, 0)

    queue = deque([name for name in modules_config if indegree[str(name)] == 0])
    order = []

    while queue:
        node = queue.popleft()
        node_str = str(node)
        order.append(node_str)
        for neighbor in graph[node_str]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(modules_config):
        raise Exception("[DAG] 模組之間存在循環依賴，無法進行拓撲排序")

    print(f"[DAG] 備用拓撲排序順序：{order}")
    return order