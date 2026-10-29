MERGE (o:Order {orderId: "DEMO-001"})
MERGE (p:Product {ProductName: "ZS-T01扫地机器人"})
MERGE (s:Supplier {CompanyName: "示例供应商"})
MERGE (o)-[:CONTAINS]->(p)
MERGE (p)-[:SUPPLIED_BY]->(s)
RETURN o, p, s;