import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# Semilla para que los resultados sean replicables
np.random.seed(42)
n_samples = 1000

# Fabricamos datos aleatorios dentro y fuera de los umbrales
temperatura = np.random.uniform(10, 50, n_samples)
humedad = np.random.uniform(30, 95, n_samples)
impacto = np.random.uniform(0.5, 4.0, n_samples)

estados = []
for t, h, i in zip(temperatura, humedad, impacto):
    clima_extremo = h > 80.0 or t > 40.0
    impacto_fuerte = i > 2.5
    
    if impacto_fuerte and clima_extremo:
        estados.append("Daño Potencial")
    elif impacto_fuerte:
        estados.append("Manejo Brusco (Caída)")
    elif clima_extremo:
        estados.append("Exposición a Humedad Excesiva")
    else:
        estados.append("Tránsito Seguro")

# Estructuramos el dataset de entrenamiento
X = np.column_stack((temperatura, humedad, impacto))
y = np.array(estados)

# Entrenamos el modelo de clasificacion
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# Exportamos el archivo binario para FastAPI
joblib.dump(clf, "random_forest_model.pkl")
print("El modelo random_forest_model.pkl se generó exitosamente.")