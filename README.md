# Sales Agent (NL → SQL → Resultados + Gráficos) con MCP + SQLite

Proyecto de ejemplo de **Agentic AI** para análisis de ventas: el usuario escribe una consulta en lenguaje natural, el agente genera SQL (solo `SELECT`), consulta una base **SQLite** y devuelve resultados como **tabla**, **gráfico** (PNG) o **export** (CSV/XLSX).

---

## 1) Arquitectura (alto nivel)

**Componentes:**

- **Agente (LangChain)**: interpreta la intención del usuario (tabla / gráfico / export), genera SQL y llama herramientas (tools).
- **MCP Server (FastMCP)**: expone herramientas para:
  - `get_schema()` → inspección de tablas/columnas
  - `run_sql(sql)` → ejecuta consultas seguras (solo `SELECT`)
  - `plot_sql(sql, ...)` → genera gráficos y los guarda en `outputs/`
  - `export_sql(sql, ...)` → exporta resultados a CSV/XLSX en `outputs/`
- **SQLite DB**: base de datos local `ventas.db` con la tabla `ventas`.
- **CLI**: archivo `agent_cli.py` para ejecutar el bot desde terminal.

**Flujo:**

Usuario → Agente → Tools MCP (schema/query/plot/export) → Respuesta (texto + archivos)

---

## 2) Estructura de carpetas

Ejemplo de estructura usada:

```text
ejerMCP/
  .env -> de tu propiedad previamente configuradas
  .venv/ -> lo generarás cuando hagas python venv
  requirements.txt
  sales-agent/
    app/
      agent_cli.py
    servers/
      db_server.py
    src/
      ventas.db
    outputs/
      (se generan png/csv/xlsx)
```

## 3) Requisitos

- Python 3.10+ (recomendado)

- Paquetes instalados desde requirements.txt

## 4) Instalación

### 4.1 Crear y activar entorno virtual

Desde la raíz del proyecto (ejerMCP/):

```bash
python -m venv .venv
source .venv/bin/activate
```
Verificación rápida:


```bash
which python
python --version

```

### 4.2 Para instalar dependencias

```bash
pip install -r requirements.txt
```
### 4.3 Variables de Entorno

```text
OPENAI_API_KEY=TU_API_KEY
OPENAI_MODEL=gpt-4o-mini
```

## 5) Base de datos SQLite (ventas.db)

La tabla principal usada por el agente es:

ventas(id, vendedor, sede, producto, cantidad, precio, fecha)

### 5.1 Problema encontrado: “file is not a database”

En un punto se presentó el error debido a que ventas.db no era una base SQLite real, sino un archivo de texto que contenía únicamente el DDL CREATE TABLE ....

Cómo se verificó:

El DB válido tiene cabecera: SQLite format 3

Un DB inválido suele aparecer como “ASCII text” al ejecutar file.

Comandos útiles:

```bash
file sales-agent/src/ventas.db
sqlite3 sales-agent/src/ventas.db ".tables"
sqlite3 sales-agent/src/ventas.db "SELECT COUNT(*) FROM ventas;"
```

### 5.2 Solución aplicada

Paso A — Crear schema.sql

Se creó un archivo sales-agent/src/schema.sql con la definición de la tabla ventas, por ejemplo:

```sql
CREATE TABLE IF NOT EXISTS ventas (
  id INTEGER PRIMARY KEY,
  vendedor TEXT NOT NULL,
  sede TEXT NOT NULL,
  producto TEXT NOT NULL,
  cantidad INTEGER NOT NULL,
  precio REAL NOT NULL,
  fecha TEXT NOT NULL
);

```
Paso B — Crear la base SQLite a partir del schema

Desde la raíz del proyecto:

```bash
sqlite3 sales-agent/src/ventas.db < sales-agent/src/schema.sql
```

Validación:

```bash
file sales-agent/src/ventas.db
sqlite3 sales-agent/src/ventas.db ".tables"
```

Paso C — Poblar datos con seed.py

Se construyó un script sales-agent/src/seed.py para insertar registros de ejemplo en la tabla ventas (seed de datos).

Ejecución:

```bash
python sales-agent/src/seed.py
```

Validación:

```bash
sqlite3 sales-agent/src/ventas.db "SELECT COUNT(*) FROM ventas;"
```

Nota Importante: el servidor MCP apunta a sales-agent/src/ventas.db, por lo tanto ese archivo debe existir y contener la tabla ventas con datos

## 6) Ejecución del Proyecto

Desde la raíz :

```bash
python ./sales-agent/app/agent_cli.py
```

El bot queda listo para recibir preguntas. Para salir: exit o quit.

## 7) Ejemplos de consultas

### 7.1 Consultas tipo tabla

“¿Cuántas ventas hay por sede?”

### 7.2 Consultas con gráfico (PNG en outputs/)

“Grafica en barras el total vendido por sede”

### 7.3 Export (CSV/XLSX en outputs/)

“Exporta a CSV el total vendido por sede”

## 8) Salidas generadas

sales-agent/outputs/plot_*.png

sales-agent/outputs/export_*.csv o export_*.xlsx

## 9) Notas técnicas y seguridad

El servidor MCP valida que el SQL sea solo SELECT (sin DDL/DML).

Se aplican límites de filas (LIMIT) para evitar respuestas enormes.

El agente puede usar get_schema() para conocer columnas reales y reducir errores.