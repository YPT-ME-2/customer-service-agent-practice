import asyncio

from neo4j import AsyncGraphDatabase

from app.core.config import settings

from app.services.ollama_service import OllamaService

class Neo4jService:
    async def get_order_supplier(self, order_id: str) -> list[dict]:
        query = """
        MATCH (o:Order {orderId: $order_id})
              -[:CONTAINS]->(p:Product)
              -[:SUPPLIED_BY]->(s:Supplier)
        RETURN
            o.orderId AS order_id,
            p.ProductName AS product,
            s.CompanyName AS supplier
        """

        async with AsyncGraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(
                settings.NEO4J_USERNAME,
                settings.NEO4J_PASSWORD,
            ),
        ) as driver:
            async with driver.session(
                database=settings.NEO4J_DATABASE,
                default_access_mode="READ",
            ) as session:
                result = await session.run(
                    query,
                    order_id=order_id,
                )

                return await result.data()
    async def generate_cypher(self,question: str)->str:
        chat=OllamaService()
        return await chat.generate([
            {
                "role": "system",
                "content": """
你负责将用户问题转换为 Neo4j Cypher 查询。

数据库结构：
节点：
- Order，属性：orderId，字符串
- Product，属性：ProductName，字符串
- Supplier，属性：CompanyName，字符串

关系及方向：
(Order)-[:CONTAINS]->(Product)
(Product)-[:SUPPLIED_BY]->(Supplier)

要求：
- 只能使用上述节点、属性和关系。
- 只生成读取查询，不生成新增、修改、删除操作。
- 只输出 Cypher，不要解释，不要 Markdown 代码块。
- 返回结果最多20条。
- 如果现有结构无法回答，只输出 UNSUPPORTED。
注意：关系方向由数据库结构决定，不能根据自然语言的主语改变箭头。
CONTAINS：Order -> Product。
SUPPLIED_BY：Product -> Supplier。

参考示例1：
问题：订单EXAMPLE-001包含哪些商品？
查询：MATCH (o:Order {orderId: 'EXAMPLE-001'})-[:CONTAINS]->(p:Product) RETURN p.ProductName LIMIT 20

参考示例2：
问题：供应商甲供应哪些商品？
查询：MATCH (p:Product)-[:SUPPLIED_BY]->(s:Supplier {CompanyName: '供应商甲'}) RETURN p.ProductName LIMIT 20

实际查询必须使用当前问题中的条件，不要照搬示例的订单号或供应商名。
""",
            },
            {
                "role": "user",
                "content": question,
            }
        ])

    async def execute_cypher(self,query:str) -> list[dict]:
        query=query.strip()
        if query=="UNSUPPORTED":
            raise ValueError("当前图结构无法回答这个问题")
        async with AsyncGraphDatabase.driver(
            settings.NEO4J_URL,
            auth=(
                settings.NEO4J_READ_USERNAME,
                settings.NEO4J_READ_PASSWORD,
            ),
        ) as driver:
            async with driver.session(
                database=settings.NEO4J_DATABASE,
                default_access_mode="READ",
            ) as session:
                result=await session.run(query)
                return await result.data()
    
# 直接运行本文件对应的模块时，验证一次查询。
async def main():
    service = Neo4jService()
    # rows = await service.get_order_supplier("DEMO-001")
    # print(rows)
    query=await service.generate_cypher(
         "订单DEMO-001里的商品由哪些供应商提供？"
    )
    print("生成的查询：", query)
    rows=await service.execute_cypher(query)
    print("查询结果：", rows)

if __name__ == "__main__":
    asyncio.run(main())