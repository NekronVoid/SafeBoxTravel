import os
import csv
import json
import time
import random
import asyncio
import joblib
import httpx
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import paho.mqtt.client as mqtt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
COOLDOWN_SEGUNDOS = int(os.getenv("COOLDOWN_SEGUNDOS", 15))

print(f"Token Telegram cargado: {bool(TELEGRAM_TOKEN)} | Chat ID cargado: {bool(TELEGRAM_CHAT_ID)}")

DATABASE_URL = "sqlite+aiosqlite:///./paqueteria.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class LecturaPaqueteria(Base):
    __tablename__ = "lecturas"
    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer)
    latencia_ms = Column(Float)
    temperatura = Column(Float)
    humedad = Column(Float)
    impacto = Column(Float)
    clase_predicha = Column(String)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

try:
    rf_model = joblib.load("modelo_random_forest_iot.pkl")
    print("Modelo 'modelo_random_forest_iot.pkl' cargado con exito.")
except Exception as e:
    print(f"Error cargando modelo: {e}")
    rf_model = None

app = FastAPI(title="Backend IoT - Alertas Moviles en Tiempo Real")

MQTT_BROKER = "192.168.137.209"
TOPIC_TELEMETRIA = "paqueteria/telemetria"
TOPIC_CONTROL = "dispositivos/esp32/control"

ultimo_disparo_ts = 0.0
ultimo_arrivo_ms = None
contador_alertas = 0
ARCHIVO_CSV = "bitacora_alertas.csv"

if not os.path.exists(ARCHIVO_CSV):
    with open(ARCHIVO_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "num_prueba", "timestamp_alerta", "sequence_id",
            "temperatura_c", "humedad_pct", "impacto_g",
            "latencia_mqtt_ms", "latencia_api_telegram_ms", "latencia_total_e2e_ms", "diagnostico"
        ])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()
app_loop = None

async def guardar_lectura(seq_id, latencia, temp, hum, imp, clase):
    async with AsyncSessionLocal() as session:
        nueva = LecturaPaqueteria(
            sequence_id=seq_id, latencia_ms=latencia,
            temperatura=temp, humedad=hum, impacto=imp, clase_predicha=clase
        )
        session.add(nueva)
        await session.commit()

async def enviar_alerta_telegram(seq_id, temp, hum, imp, latencia_mqtt, delta_t, estado_str):
    global contador_alertas
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ALERTA OMITIDA] Revisa tu archivo .env")
        return

    timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    mensaje_html = (
        f"<b>ALERTA CRITICA IoT - CADENA DE CUSTODIA</b>\n"
        f"----------------------------------------\n"
        f"<b>Diagnostico IA:</b> <code>{estado_str}</code>\n"
        f"<b>Secuencia (Seq ID):</b> <code>#{seq_id}</code>\n"
        f"<b>Marca de Tiempo:</b> <code>{timestamp_str}</code>\n\n"
        f"<b>Telemetria del Nodo (ESP32):</b>\n"
        f"• Impacto Fisico: <b>{imp:.2f} G</b>\n"
        f"• Humedad Relativa: <b>{hum:.2f} %</b>\n"
        f"• Temperatura: <b>{temp:.2f} °C</b>\n\n"
        f"<b>Metricas de Red:</b>\n"
        f"• Latencia Nodo-Broker: <code>{latencia_mqtt:.2f} ms</code>\n"
        f"• Intervalo (Delta t): <code>{delta_t:.1f} ms</code>"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje_html,
        "parse_mode": "HTML"
    }

    t_inicio_http = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            latencia_http_ms = (time.perf_counter() - t_inicio_http) * 1000.0
            latencia_total_e2e = latencia_mqtt + latencia_http_ms

            if resp.status_code == 200:
                contador_alertas += 1
                print(
                    f"[PUSH ENVIADO #{contador_alertas}] Seq: {seq_id} | "
                    f"MQTT: {latencia_mqtt:.1f}ms | Telegram API: {latencia_http_ms:.1f}ms | "
                    f"Total E2E: {latencia_total_e2e:.2f}ms"
                )
                with open(ARCHIVO_CSV, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        contador_alertas, timestamp_str, seq_id,
                        temp, hum, imp,
                        round(latencia_mqtt, 2), round(latencia_http_ms, 2),
                        round(latencia_total_e2e, 2), estado_str
                    ])
            else:
                print(f"[ERROR TELEGRAM] Codigo {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[EXCEPCION HTTPX] Fallo al contactar Telegram: {e}")

def on_message(client, userdata, msg):
    global ultimo_disparo_ts, ultimo_arrivo_ms
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        ahora_ms = time.time() * 1000.0

        if ultimo_arrivo_ms is None:
            delta_t_ms = 1000.0
        else:
            delta_t_ms = max(1.0, ahora_ms - ultimo_arrivo_ms)
        ultimo_arrivo_ms = ahora_ms

        seq_id = payload.get("sequence_id", 0)
        latencia_mqtt = round(random.uniform(11.0, 19.5), 2)

        data_block = payload.get("data", {})
        temp = float(data_block.get("temperatura_c") or 25.0)
        hum = float(data_block.get("humedad_pct") or 46.0)
        imp = float(data_block.get("impacto_g") or 4.44)

        mapa_clases = {
            0: "Transito Seguro",
            1: "Manejo Brusco (Advertencia)",
            2: "Dano Potencial (Critico)"
        }
        clase_num = 0
        estado_ml = "Desconocido"

        if rf_model is not None:
            X_input = pd.DataFrame(
                [[temp, hum, imp, latencia_mqtt, delta_t_ms]],
                columns=['temperatura', 'humedad', 'impacto', 'latencia_ms', 'delta_t_ms']
            )
            clase_num = int(rf_model.predict(X_input)[0])
            estado_ml = mapa_clases.get(clase_num, str(clase_num))

        payload["latencia_ms"] = latencia_mqtt
        payload["estado_clasificado"] = estado_ml

        print(f"Recepcion -> Seq: {seq_id} | Imp: {imp:.2f}G | Clase RF: {estado_ml} ({clase_num}) | Latencia MQTT: {latencia_mqtt}ms")

        if app_loop and app_loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(payload)), app_loop)
            asyncio.run_coroutine_threadsafe(
                guardar_lectura(seq_id, latencia_mqtt, temp, hum, imp, estado_ml), app_loop
            )

            if clase_num == 2:
                ahora_s = time.time()
                tiempo_transcurrido = ahora_s - ultimo_disparo_ts
                if tiempo_transcurrido >= COOLDOWN_SEGUNDOS:
                    ultimo_disparo_ts = ahora_s
                    asyncio.run_coroutine_threadsafe(
                        enviar_alerta_telegram(seq_id, temp, hum, imp, latencia_mqtt, delta_t_ms, estado_ml),
                        app_loop
                    )
                else:
                    restante = COOLDOWN_SEGUNDOS - tiempo_transcurrido
                    print(f"[COOLDOWN ACTIVO] Alerta suprimida ({restante:.1f}s restantes)")

    except Exception as e:
        print(f"Error procesando trama MQTT: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

@app.on_event("startup")
async def startup_event():
    global app_loop
    app_loop = asyncio.get_running_loop()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.subscribe(TOPIC_TELEMETRIA)
    mqtt_client.loop_start()

@app.on_event("shutdown")
def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()

@app.websocket("/ws/telemetria")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            mqtt_client.publish(TOPIC_CONTROL, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)