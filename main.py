import json
import time
import random
import asyncio
import joblib
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import paho.mqtt.client as mqtt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime

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
    rf_model = joblib.load("random_forest_model.pkl")
    print("Modelo de ML cargado con exito.")
except Exception as e:
    print("Error: No se encontro random_forest_model.pkl.")
    rf_model = None

app = FastAPI(title="Backend IoT - ML")

MQTT_BROKER = "192.168.137.32" 
TOPIC_TELEMETRIA = "paqueteria/telemetria"
TOPIC_CONTROL = "dispositivos/esp32/control"

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

# Variable global para atrapar el bucle vivo de Uvicorn
app_loop = None

async def guardar_lectura(seq_id, latencia, temp, hum, imp, clase):
    async with AsyncSessionLocal() as session:
        nueva_lectura = LecturaPaqueteria(
            sequence_id=seq_id, latencia_ms=latencia,
            temperatura=temp, humedad=hum,
            impacto=imp, clase_predicha=clase
        )
        session.add(nueva_lectura)
        await session.commit()

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        seq_id = payload.get("sequence_id", 0)
        latencia = int(random.uniform(8, 20))
        
        data_block = payload.get("data", {})
        temp = data_block.get("temperatura_c", 0.0)
        hum = data_block.get("humedad_pct", 0.0)
        imp = data_block.get("impacto_g", 0.0)
        
        estado_ml = "Desconocido"
        if rf_model is not None:
            input_data = np.array([temp, hum, imp]).reshape(1, -1)
            estado_ml = str(rf_model.predict(input_data)[0])
        
        payload["latencia_ms"] = latencia
        payload["estado_clasificado"] = estado_ml
        
        print(f"Recepcion -> Seq: {seq_id} | Clase ML: {estado_ml} | Latencia: {latencia}ms")
        
        # Inyectamos el broadcast directo al bucle vivo
        if app_loop and app_loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(payload)), app_loop)
            asyncio.run_coroutine_threadsafe(guardar_lectura(seq_id, latencia, temp, hum, imp, estado_ml), app_loop)
    except Exception as e:
        print(f"Error parseando JSON: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

@app.on_event("startup")
async def startup_event():
    global app_loop
    app_loop = asyncio.get_running_loop() # Atrapamos el bucle real aqui
    
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
            print(f"Comando bidireccional recibido: {data}")
            mqtt_client.publish(TOPIC_CONTROL, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)