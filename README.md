# Sistema de Telemetría y Monitoreo de Cadena de Custodia (IoT)

Sistema de monitoreo en tiempo real diseñado para la supervisión de paquetes y procesos de logística crítica.

El sistema utiliza un **ESP32** equipado con sensores para recopilar información de telemetría y transmitirla mediante **MQTT** a un broker **Mosquitto**. Los datos son procesados por un backend desarrollado con **FastAPI** y enviados en tiempo real mediante **WebSockets** a un dashboard web interactivo.

---

## Arquitectura del Sistema

```text
┌─────────────────────────┐
│    ESP32 + Sensores     │
│                         │
│  - DHT11 / DHT22        │
│  - MPU6050               │
└────────────┬────────────┘
             │
             │ MQTT
             │ Puerto 1883
             ▼
┌─────────────────────────┐
│   Mosquitto Broker      │
└────────────┬────────────┘
             │
             │ Paho MQTT
             ▼
┌─────────────────────────┐
│     Backend FastAPI     │
│                         │
│  - Procesamiento        │
│  - WebSockets           │
│  - Persistencia         │
└───────┬─────────┬───────┘
        │         │
        │         ▼
        │   ┌──────────────┐
        │   │ Base de Datos│
        │   └──────────────┘
        │
        │ WebSocket
        │ Puerto 8000
        ▼
┌─────────────────────────┐
│    Dashboard Web        │
│                         │
│  HTML / CSS / JavaScript│
│  Chart.js / DOM API     │
└─────────────────────────┘
```

---

## Tecnologías Utilizadas

### Hardware / Firmware

* **ESP32** — Wi-Fi y comunicación MQTT.
* **DHT11 / DHT22** — Sensor de temperatura y humedad.
* **MPU6050** — Acelerómetro y giroscopio.
* **C++** — Lenguaje utilizado para el firmware.
* **Arduino Framework**.
* **PubSubClient** — Comunicación MQTT.
* **ArduinoJson** — Procesamiento de datos JSON.

### Broker MQTT

* **Eclipse Mosquitto**
* **MQTT**
* Puerto utilizado: `1883`

### Backend

* **Python 3.10+**
* **FastAPI**
* **Uvicorn**
* **Paho MQTT Client**
* **WebSockets**

### Frontend

* **HTML5**
* **CSS3**
* **Tailwind CSS**
* **JavaScript Vanilla**
* **WebSockets**
* **Chart.js**
* **DOM API**

### Persistencia

* Base de datos para almacenar la información de telemetría recibida por el backend.

---

# Flujo de Datos

El sistema sigue el siguiente flujo:

1. Los sensores conectados al **ESP32** recopilan información del paquete.
2. El ESP32 procesa las lecturas y genera un payload en formato **JSON**.
3. Los datos son publicados mediante **MQTT** en el tópico:

```text
paqueteria/telemetria
```

4. **Mosquitto** recibe y distribuye los mensajes MQTT.
5. El backend **FastAPI**, mediante `paho-mqtt`, recibe los datos.
6. El backend procesa y clasifica el estado de la telemetría.
7. Los datos pueden almacenarse en la **base de datos**.
8. FastAPI transmite las actualizaciones mediante **WebSockets**.
9. El **dashboard web** recibe los datos en tiempo real y actualiza la información mostrada.

---

# Estructura de Datos

Los datos de telemetría se publican en el tópico:

```text
paqueteria/telemetria
```

El payload utilizado tiene la siguiente estructura:

```json
{
  "node_id": "ESP32_Logistica",
  "sequence_id": 1,
  "timestamp_ms": 1700000000000,
  "temperatura_c": 24.5,
  "humedad_pct": 55.0,
  "impacto_g": 1.02,
  "estado": "Tránsito Seguro"
}
```

## Descripción de los campos

| Campo           | Tipo    | Descripción                                     |
| --------------- | ------- | ----------------------------------------------- |
| `node_id`       | String  | Identificador del dispositivo ESP32.            |
| `sequence_id`   | Integer | Número consecutivo del mensaje enviado.         |
| `timestamp_ms`  | Integer | Marca de tiempo en milisegundos.                |
| `temperatura_c` | Float   | Temperatura registrada en grados Celsius.       |
| `humedad_pct`   | Float   | Porcentaje de humedad registrado.               |
| `impacto_g`     | Float   | Aceleración o impacto registrado en unidades G. |
| `estado`        | String  | Estado actual de las condiciones del paquete.   |

---

# Clasificación de Estados

El sistema clasifica las condiciones del paquete utilizando los datos obtenidos de los sensores.

| Estado                            | Condición                                                           |
| --------------------------------- | ------------------------------------------------------------------- |
| **Tránsito Seguro**               | Operación dentro de los parámetros normales.                        |
| **Manejo Brusco (Caída)**         | Impacto superior a `2.5 G`.                                         |
| **Exposición a Humedad Excesiva** | Humedad superior al `80%` o temperatura superior a `40 °C`.         |
| **Daño Potencial**                | Combinación de un impacto fuerte y una condición climática extrema. |

---

# Instalación y Configuración

## 1. Configuración de Mosquitto

Primero es necesario configurar el broker **Mosquitto** para aceptar conexiones desde la red.

En el archivo `mosquitto.conf`:

```conf
listener 1883
allow_anonymous true
```

> **Nota:** `allow_anonymous true` se utiliza para facilitar las pruebas en un entorno local. Para un entorno de producción se recomienda utilizar autenticación y configuraciones de seguridad adecuadas.

Para iniciar Mosquitto utilizando esta configuración:

```bash
mosquitto -c mosquitto.conf -v
```

---

# 2. Configuración del Backend FastAPI

Clona el repositorio:

```bash
git clone https://github.com/tu-usuario/tu-repositorio.git
```
