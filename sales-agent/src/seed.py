import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "ventas.db"

vendedores = ["Juan Pérez", "Ana García", "Carlos Ruiz", "María López", "Andrés Gómez"]
sedes = ["Bogotá", "Medellín", "Cali", "Barranquilla"]
productos = ["Mouse Logitech", "Teclado Mecánico", "Router TP-Link", "RAM 16GB", "SSD 1TB", "Impresora HP"]

def rand_date():
    start = date(2025, 7, 1)
    return (start + timedelta(days=random.randint(0, 180))).isoformat()

con = sqlite3.connect(DB)
cur = con.cursor()

# Asegura que exista la tabla (si ya existe no falla si tu schema la creó)
cur.execute("""
CREATE TABLE IF NOT EXISTS ventas (
  id INTEGER PRIMARY KEY,
  vendedor TEXT NOT NULL,
  sede TEXT NOT NULL,
  producto TEXT NOT NULL,
  cantidad INTEGER NOT NULL,
  precio REAL NOT NULL,
  fecha TEXT NOT NULL
);
""")

rows = []
for _ in range(200):
    rows.append((
        random.choice(vendedores),
        random.choice(sedes),
        random.choice(productos),
        random.randint(1, 15),
        round(random.uniform(50_000, 2_500_000), 2),
        rand_date()
    ))

cur.executemany(
    "INSERT INTO ventas (vendedor,sede,producto,cantidad,precio,fecha) VALUES (?,?,?,?,?,?)",
    rows
)

con.commit()
con.close()
print(f"Seed OK: {len(rows)} filas insertadas en {DB}")
