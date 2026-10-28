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