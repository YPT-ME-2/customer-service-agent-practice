import asyncio

from neo4j import AsyncGraphDatabase

from app.core.config import settings


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


# 直接运行本文件对应的模块时，验证一次查询。
async def main():
    service = Neo4jService()
    rows = await service.get_order_supplier("DEMO-001")
    print(rows)


if __name__ == "__main__":
    asyncio.run(main())