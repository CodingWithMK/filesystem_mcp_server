# test_minimal_server.py
#!/usr/bin/env python3
import sys
from mcp.server import Server, stdio_server
from mcp.types import Tool, TextContent

# Debug print
print("MCP Server starting...", file=sys.stderr)

server = Server("Test Server")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="hello",
            description="Say hello",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "hello":
        return TextContent(type="text", text="Hello from MCP!")
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    print("Starting stdio server...", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())