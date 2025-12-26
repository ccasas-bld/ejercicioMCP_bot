# app/agent_cli.py
import asyncio
import os
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """Eres un analista de ventas.
Tienes acceso a tools MCP para:
- get_schema()
- run_sql(sql)
- plot_sql(sql, chart_type, x, y)
- export_sql(sql, format, filename)

Reglas:
1) Antes de escribir SQL, si hay duda del schema, llama get_schema().
2) Genera SOLO SELECT (sin INSERT/UPDATE/DELETE/DDL).
3) Si el usuario pide "gráfico", usa plot_sql.
4) Si pide "guardar/exportar", usa export_sql.
5) Si pide tabla o no especifica formato, usa run_sql y resume resultados.
"""

async def main():
    load_dotenv()

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0
    )

    client = MultiServerMCPClient({
        "sales_db": {
            "transport": "stdio",
            "command": "python",
            "args": ["sales-agent/servers/db_server.py"],
        }
    })

    tools = await client.get_tools()

    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        debug=False
    )

    print("Listo. Escribe tu consulta (exit para salir).")
    while True:
        q = input("\n> ").strip()
        if q.lower() in ("exit", "quit"):
            break

        result = await agent.ainvoke({
            "messages": [{"role": "user", "content": q}]
        })

        print("\n" + result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
