import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

conn = sqlite3.connect('paqueteria.db')
query = """
SELECT id, sequence_id, latencia_ms, temperatura, humedad, impacto, fecha_registro 
FROM lecturas 
ORDER BY id ASC
"""
df = pd.read_sql_query(query, conn)
conn.close()

df['fecha_registro'] = pd.to_datetime(df['fecha_registro'])

df['delta_t_ms'] = df['fecha_registro'].diff().dt.total_seconds() * 1000
df = df.dropna(subset=['delta_t_ms'])

print("=== 1. PRIMEROS REGISTROS ===")
print(df.head())

print("\n=== 2. ESTADÍSTICOS DESCRIPTIVOS (MEDIA, MEDIANA, STD, ETC.) ===")
estadisticos = df[['temperatura', 'humedad', 'impacto', 'latencia_ms', 'delta_t_ms']].describe()
print(estadisticos)

print("\n=== MEDIANAS ===")
print(df[['temperatura', 'humedad', 'impacto', 'latencia_ms']].median())

Q1 = df['latencia_ms'].quantile(0.25)
Q3 = df['latencia_ms'].quantile(0.75)
IQR = Q3 - Q1
limite_superior = Q3 + 1.5 * IQR

outliers = df[df['latencia_ms'] > limite_superior]
print(f"\n=== 3. DETECCIÓN DE ANOMALÍAS (IQR) ===")
print(f"Límite superior normal de latencia: {limite_superior:.2f} ms")
print(f"Total de lecturas con latencia anómala (Outliers): {len(outliers)}")

seq_min = df['sequence_id'].min()
seq_max = df['sequence_id'].max()
esperados = (seq_max - seq_min) + 1
recibidos = len(df)
perdidos = max(0, esperados - recibidos)
pct_perdida = (perdidos / esperados) * 100 if esperados > 0 else 0

print(f"\n=== 4. RENDIMIENTO DE RED ===")
print(f"Paquetes esperados: {esperados} | Recibidos: {recibidos} | Pérdida: {pct_perdida:.2f}%")
print(f"Intervalo de llegada promedio (Real vs 1000ms config): {df['delta_t_ms'].mean():.2f} ms")

sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('Panel Analítico EDA - Telemetría de Paquetería IoT', fontsize=16, fontweight='bold')

axes[0, 0].plot(df['fecha_registro'], df['impacto'], label='Impacto (G)', color='teal', alpha=0.8)
axes[0, 0].plot(df['fecha_registro'], df['temperatura'], label='Temp (°C)', color='crimson', alpha=0.6)
axes[0, 0].set_title('1. Serie Temporal de Sensores')
axes[0, 0].set_xlabel('Tiempo')
axes[0, 0].set_ylabel('Magnitud')
axes[0, 0].legend()
axes[0, 0].tick_params(axis='x', rotation=30)

sns.boxplot(x=df['latencia_ms'], ax=axes[0, 1], color='skyblue')
axes[0, 1].axvline(limite_superior, color='red', linestyle='--', label=f'Umbral Outlier ({limite_superior:.1f}ms)')
axes[0, 1].set_title('2. Boxplot de Latencia E2E y Outliers')
axes[0, 1].set_xlabel('Latencia (ms)')
axes[0, 1].legend()

sns.histplot(df['impacto'], kde=True, ax=axes[1, 0], color='mediumseagreen', bins=20)
axes[1, 0].set_title('3. Distribución e Histograma de Impacto (G)')
axes[1, 0].set_xlabel('Fuerza G')
axes[1, 0].set_ylabel('Frecuencia')

cols_corr = ['temperatura', 'humedad', 'impacto', 'latencia_ms', 'delta_t_ms']
corr_matrix = df[cols_corr].corr()
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", ax=axes[1, 1], vmin=-1, vmax=1)
axes[1, 1].set_title('4. Matriz de Correlación (Heatmap)')

plt.tight_layout()
plt.savefig('panel_diagnostico_eda.png', dpi=300)
plt.show()