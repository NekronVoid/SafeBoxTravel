import json
import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import paho.mqtt.client as mqtt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, Float, String, DateTime

# Configuracion de Base de Datos SQLite
DATABASE_URL = "sqlite+aiosqlite:///./paqueteria.db"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Nuevo modelo de tabla para la paqueteria
class LecturaPaqueteria(Base):
    __tablename__ = "lecturas"
    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer)
    latencia_ms = Column(Float)
    temperatura = Column(Float)
    humedad = Column(Float)
    impacto = Column(Float)
    estado = Column(String)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

app = FastAPI(title="Backend IoT - Paqueteria")

# IP del Mosquitto de tu compa y los nuevos topicos
MQTT_BROKER = "192.168.137.196" 
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
            await connection.send_text(message)

manager = ConnectionManager()
loop = asyncio.get_event_loop()

# Funcion para guardar en SQLite sin bloquear el server
async def guardar_lectura(seq_id, latencia, temp, hum, imp, estado):
    async with AsyncSessionLocal() as session:
        nueva_lectura = LecturaPaqueteria(
            sequence_id=seq_id, 
            latencia_ms=latencia,
            temperatura=temp,
            humedad=hum,
            impacto=imp,
            estado=estado
        )
        session.add(nueva_lectura)
        await session.commit()

# Callback cuando llega un mensaje de la ESP32
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        # Calculo de latencia
        t_recepcion = int(time.time() * 1000)
        t_envio = payload.get("timestamp_ms", t_recepcion)
        latencia = t_recepcion - t_envio
        
        # Extraccion de las variables del JSON
        seq_id = payload.get("sequence_id", 0)
        temp = payload.get("temperatura_c", 0.0)
        hum = payload.get("humedad_pct", 0.0)
        imp = payload.get("impacto_g", 0.0)
        estado = payload.get("estado", "Desconocido")
        
        # Le inyectamos la latencia calculada al payload antes de mandarlo al front
        payload["latencia_ms"] = latencia
        
        print(f"[MQTT Inbox]: {payload}")
        
        # Mandar por WebSocket y guardar en BD simultaneamente
        asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(payload)), loop)
        asyncio.run_coroutine_threadsafe(guardar_lectura(seq_id, latencia, temp, hum, imp, estado), loop)
    except Exception as e:
        print(f"Error procesando el paquete MQTT: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

@app.on_event("startup")
async def startup_event():
    # Crea la base de datos al arrancar
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Conecta al broker en segundo plano
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
            print(f"[WebSocket Inbox]: Comando recibido desde la web -> {data}")
            mqtt_client.publish(TOPIC_CONTROL, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)