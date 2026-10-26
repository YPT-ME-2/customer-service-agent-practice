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