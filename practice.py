# import asyncio

# async def make_answer():
#     print("开始准备回答")
#     await asyncio.sleep(1)
#     return "你好"

# async def main():
#     answer=await make_answer()
#     print(answer)

# asyncio.run(main())

import asyncio


async def task(name):
    print(f"{name}：开始")
    await asyncio.sleep(2)
    print(f"{name}：结束")


async def main():
    await asyncio.gather(
        task("任务A"),
        task("任务B"),
    )


asyncio.run(main())