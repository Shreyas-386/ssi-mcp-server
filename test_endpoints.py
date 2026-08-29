import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        r1 = await client.post("/mcp/messages", json={"method": "tools/call", "params": {"name": "get_daily_graphs"}})
        print("/mcp/messages:", r1.status_code)
        
        r2 = await client.post("/messages", json={"method": "tools/call", "params": {"name": "get_daily_graphs"}})
        print("/messages:", r2.status_code)
        
        r3 = await client.post("/mcp", json={"method": "tools/call", "params": {"name": "get_daily_graphs"}})
        print("/mcp:", r3.status_code)

asyncio.run(test())
