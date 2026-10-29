SEARCH_TOOL = {
    "name": "search_knowledge",
    "description": "查询机器人说明资料，获取故障处理、维护保养和售后信息",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "需要检索的机器人相关问题",
            }
        },
        "required": ["query"],
    },
}

ORDER_SUPPLIER_TOOL = {
    "name": "query_order_supplier",
    "description": "根据订单号，查询该订单包含的商品名称及其供应商名称",
    "parameters": {
        "type": "object",
        "properties": {
            "order_id": {
                "type": "string",
                "description": "用户提供的订单号，例如 DEMO-001",
            }
        },
        "required": ["order_id"],
    },
}

GRAPH_QUERY_TOOL = {
    "name": "query_graph",
    "description": (
        "查询订单、商品和供应商之间的关系，"
        "例如某供应商供应哪些商品、某商品属于哪些订单。"
        "按订单号查询商品及供应商时，优先使用 query_order_supplier。"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "包含查询对象和条件的完整问题",
            }
        },
        "required": ["question"],
    },
}

