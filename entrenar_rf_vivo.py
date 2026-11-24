import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

np.random.seed(42)
rows = []
for _ in range(450):
    rows.append([
        np.random.normal(25.0, 2.5),
        np.random.uniform(25, 58),
        np.random.uniform(3.5, 5.6),
        np.random.uniform(8, 25),
        np.random.uniform(800, 3600),
        0
    ])
for _ in range(450):
    if np.random.rand() < 0.5:
        rows.append([
            np.random.normal(25.0, 2.5),
            np.random.uniform(62, 88),
            np.random.uniform(3.5, 5.6),
            np.random.uniform(8, 28),
            np.random.uniform(800, 3600),
            1
        ])
    else:
        rows.append([
            np.random.normal(25.0, 2.5),
            np.random.uniform(25, 58),
            np.random.uniform(3.5, 5.6),
            np.random.uniform(30, 50),
            np.random.uniform(800, 3600),
            1
        ])
for _ in range(450):
    r = np.random.rand()
    if r < 0.55:
        rows.append([
            np.random.normal(25.0, 2.5),
            np.random.uniform(25, 85),
            np.random.uniform(6.2, 12.0),
            np.random.uniform(8, 28),
            np.random.uniform(800, 3600),
            2
        ])
    elif r < 0.8:
        rows.append([
            np.random.normal(25.0, 2.5),
            np.random.uniform(25, 85),
            np.random.uniform(3.5, 5.6),
            np.random.uniform(55, 150),
            np.random.uniform(800, 3600),
            2
        ])
    else:
        rows.append([
            np.random.normal(25.0, 2.5),
            np.random.uniform(25, 85),
            np.random.uniform(3.5, 5.6),
            np.random.uniform(8, 28),
            np.random.uniform(4500, 7500),
            2
        ])

cols = ['temperatura', 'humedad', 'impacto', 'latencia_ms', 'delta_t_ms']
df = pd.DataFrame(rows, columns=cols + ['estado'])
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, criterion='gini')
rf.fit(df[cols], df['estado'])
joblib.dump(rf, 'modelo_random_forest_iot.pkl')
print("Modelo calibrado listo.")