import sqlite3
import numpy as np
from datetime import datetime, timedelta

conn = sqlite3.connect('paqueteria.db')
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS lecturas")
cursor.execute("""
CREATE TABLE lecturas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER,
    latencia_ms REAL,
    temperatura REAL,
    humedad REAL,
    impacto REAL,
    clase_predicha TEXT,
    fecha_registro DATETIME
)
""")

np.random.seed(42)
tiempo_actual = datetime.now() - timedelta(minutes=5)
registros = []

for seq in range(250):
    if seq in [45, 112, 113, 198]:
        tiempo_actual += timedelta(milliseconds=1000)
        continue
        
    jitter_intervalo = np.random.normal(1000, 25)
    tiempo_actual += timedelta(milliseconds=jitter_intervalo)
    
    if np.random.rand() < 0.05:
        latencia = round(np.random.uniform(65, 140), 2)
    else:
        latencia = round(np.random.normal(15, 3), 2)
        
    temp = round(25.4 + np.random.normal(0, 0.25) + (0.8 if 80 < seq < 140 else 0), 2)
    
    if 80 < seq < 150:
        hum = round(min(68.0, 46.0 + (seq - 80) * 0.35 + np.random.normal(0, 0.8)), 2)
    elif seq >= 150:
        hum = round(max(46.0, 68.0 - (seq - 150) * 0.25 + np.random.normal(0, 0.8)), 2)
    else:
        hum = round(46.0 + np.random.normal(0, 0.5), 2)
        
    if seq in [30, 95, 160, 210, 211]:
        imp = round(np.random.uniform(5.2, 6.8), 2)
    else:
        imp = round(4.44 + np.random.normal(0, 0.06), 2)
        
    clase = "Daño Potencial" if (imp > 2.5 and hum > 80) else "Manejo Brusco (Caída)"
    
    registros.append((seq, latencia, temp, hum, imp, clase, tiempo_actual.strftime('%Y-%m-%d %H:%M:%S.%f')))

cursor.executemany("""
INSERT INTO lecturas (sequence_id, latencia_ms, temperatura, humedad, impacto, clase_predicha, fecha_registro)
VALUES (?, ?, ?, ?, ?, ?, ?)
""", registros)

conn.commit()
conn.close()
print(f"Listo: {len(registros)} lecturas guardadas en paqueteria.db.")