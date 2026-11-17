import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

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
df = df.dropna(subset=['delta_t_ms']).copy()

def etiquetar_estado(row):
    if row['impacto'] > 5.0 or row['latencia_ms'] > 50.0 or row['delta_t_ms'] > 1500:
        return 2
    elif row['humedad'] > 55.0 or row['latencia_ms'] > 17.5:
        return 1
    return 0

df['estado_sistema'] = df.apply(etiquetar_estado, axis=1)

X = df[['temperatura', 'humedad', 'impacto', 'latencia_ms', 'delta_t_ms']]
y = df['estado_sistema']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y
)

rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    criterion='gini'
)
rf_model.fit(X_train, y_train)

y_pred = rf_model.predict(X_test)
nombres_clases = ['Normal (0)', 'Advertencia (1)', 'Crítico (2)']

print("=== 1. EXACTITUD GLOBAL (ACCURACY) ===")
print(f"Accuracy del modelo: {accuracy_score(y_test, y_pred) * 100:.2f}%\n")

print("=== 2. REPORTE DE CLASIFICACIÓN ===")
print(classification_report(y_test, y_pred, target_names=nombres_clases, digits=4))

importances = rf_model.feature_importances_
df_importance = pd.DataFrame({
    'Característica': X.columns,
    'Importancia': importances
}).sort_values(by='Importancia', ascending=False)

print("=== 3. IMPORTANCIA DE CARACTERÍSTICAS (FEATURE IMPORTANCE) ===")
print(df_importance.to_string(index=False))

joblib.dump(rf_model, 'modelo_random_forest_iot.pkl')
print("\n=== 4. SERIALIZACIÓN E INFERENCIA DE PRUEBA ===")
print("Archivo 'modelo_random_forest_iot.pkl' exportado con éxito.")

modelo_cargado = joblib.load('modelo_random_forest_iot.pkl')
nueva_lectura = pd.DataFrame([[25.8, 62.0, 4.45, 18.5, 1005.0]], columns=X.columns)
prediccion = modelo_cargado.predict(nueva_lectura)[0]
mapa_estados = {0: 'Normal', 1: 'Advertencia', 2: 'Crítico'}
print(f"Predicción para lectura simulada [Temp=25.8, Hum=62.0, Imp=4.45G, Lat=18.5ms, dT=1005ms]: {prediccion} ({mapa_estados[prediccion]})")

sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
fig.suptitle('Evaluación del Modelo Random Forest - Telemetría IoT', fontsize=15, fontweight='bold')

cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
            xticklabels=nombres_clases, yticklabels=nombres_clases, ax=axes[0], annot_kws={"size": 13})
axes[0].set_title('1. Matriz de Confusión (Conjunto de Prueba 20%)')
axes[0].set_xlabel('Predicción del Bosque')
axes[0].set_ylabel('Estado Real del Sistema')

sns.barplot(x='Importancia', y='Característica', data=df_importance, palette='viridis', ax=axes[1])
axes[1].set_title('2. Importancia de Características (Criterio Gini)')
axes[1].set_xlabel('Peso Relativo (0.0 a 1.0)')
axes[1].set_ylabel('Variable Predictora')

for index, value in enumerate(df_importance['Importancia']):
    axes[1].text(value + 0.01, index, f"{value*100:.1f}%", va='center', fontweight='bold')
axes[1].set_xlim(0, 0.65)

plt.tight_layout()
plt.savefig('evaluacion_random_forest.png', dpi=300)
plt.show()