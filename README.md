MQTT + Home Assistant — це ідеальний вибір для Raspberry Pi Zero 2 W: легкий, стабільний, без WebSocket і без зайвого навантаження.

Нижче — перевірена схема, яка точно підходить для Zero 2 W.

🏗️ Архітектура (як це працює)
BME280
  ↓ (30 сек)
Python sensor_worker
  ↓
MQTT publish (paho-mqtt)
  ↓
MQTT broker (Mosquitto)
  ↓
Home Assistant


✔ мінімум RAM
✔ без постійних з’єднань
✔ працює роками

1️⃣ MQTT broker (де він буде?)
Варіант А — НАЙКРАЩИЙ ✅

MQTT (Mosquitto) працює на Home Assistant
→ Raspberry Pi Zero 2 W = тільки клієнт

📌 Рекомендую саме це.

Варіант Б

Mosquitto на самій Zero 2 W
→ можна, але зайве навантаження

2️⃣ Встановлюємо MQTT клієнт (на Zero 2 W)

У venv:

source ~/myenv/bin/activate
pip install paho-mqtt

3️⃣ MQTT topics (простi та правильні)

Використаємо Home Assistant MQTT Discovery
(щоб сенсори з’явились автоматично)

homeassistant/sensor/bme280_temperature/config
homeassistant/sensor/bme280_humidity/config
homeassistant/sensor/bme280_pressure/config

bme280/state

4️⃣ Код: MQTT publish (ДОДАЄМО В project.py)
🔧 CONFIG
import json
import paho.mqtt.client as mqtt

MQTT_HOST = "IP_HOME_ASSISTANT"
MQTT_PORT = 1883
MQTT_USER = "mqtt_user"
MQTT_PASS = "mqtt_pass"
MQTT_CLIENT_ID = "bme280_zero2w"

🔧 MQTT init (один раз)
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
mqtt_client.loop_start()

🔧 Home Assistant discovery (один раз при старті)
def mqtt_discovery():
    sensors = {
        "temperature": {
            "unit": "°C",
            "device_class": "temperature"
        },
        "humidity": {
            "unit": "%",
            "device_class": "humidity"
        },
        "pressure": {
            "unit": "hPa",
            "device_class": "pressure"
        }
    }

    for name, cfg in sensors.items():
        payload = {
            "name": f"BME280 {name}",
            "state_topic": "bme280/state",
            "unit_of_measurement": cfg["unit"],
            "value_template": f"{{{{ value_json.{name} }}}}",
            "device_class": cfg["device_class"],
            "unique_id": f"bme280_{name}",
            "device": {
                "identifiers": ["bme280_zero2w"],
                "name": "BME280 Zero 2 W",
                "manufacturer": "DIY",
                "model": "BME280"
            }
        }

        mqtt_client.publish(
            f"homeassistant/sensor/bme280_{name}/config",
            json.dumps(payload),
            retain=True
        )


Викликати один раз після старту програми:

mqtt_discovery()

🔧 Публікація даних (у sensor_worker)

ДОДАЙ у кінець циклу:

mqtt_client.publish(
    "bme280/state",
    json.dumps({
        "temperature": t,
        "humidity": h,
        "pressure": p,
        "ts": ts
    }),
    retain=True
)


📌 retain=True → Home Assistant завжди бачить останні значення

5️⃣ Home Assistant — що ти побачиш

Через 10–30 секунд після запуску:

📍 Settings → Devices & Services → MQTT → Devices

З’явиться:

🌡️ BME280 temperature

💧 BME280 humidity

🌬️ BME280 pressure

👉 БЕЗ YAML. БЕЗ ручних сенсорів.

6️⃣ Алерти в Home Assistant (рекомендую)

В HA:

Automation:

if temperature > 30

notify (Telegram / mobile / siren)

❗ Краще робити алерти в HA, а не в Python
→ Zero 2 W робить мінімум роботи

7️⃣ Навантаження (реально)

На Zero 2 W:

MQTT client: ~2–3 MB RAM

CPU: ~0%

стабільність: 🔥🔥🔥

❌ Чого НЕ робимо

❌ WebSocket

❌ MQTT broker на Zero 2 W

❌ часті publish (<5 сек)

✅ Підсумок

✔ MQTT + Home Assistant ідеально підходить для Zero 2 W
✔ Автодискавері — все з’являється саме
✔ Алерти краще в HA
✔ Система не падає

🔜 Хочеш далі?

Можемо:
1️⃣ додати availability / LWT
2️⃣ зробити multiple sensors
3️⃣ MQTT → Grafana
4️⃣ systemd hardening (MemoryMax, Nice)

Просто напиши номер 👌







# 📟 BME280 + Raspberry Pi Zero 2 W + MQTT + Home Assistant

Цей README описує **повну, стабільну архітектуру** збору даних з датчика **BME280** на **Raspberry Pi Zero 2 W** з передачею в **Home Assistant через MQTT (Mosquitto)**.

> 🎯 Мета: **максимальна стабільність, мінімальне навантаження**, без WebSocket, без polling, без Flask для продакшену.

---

## 🧱 Архітектура системи

```
[BME280]
    ↓ I2C
[Raspberry Pi Zero 2 W]
    ↓ MQTT (publish)
[Mosquitto Broker]
    ↓ MQTT (subscribe)
[Home Assistant]
    ↓
[Entities / Automations / Grafana]
```

---

## 🔑 Чому MQTT, а не Flask / WebSocket

| Параметр     | Flask + WS  | MQTT          |
| ------------ | ----------- | ------------- |
| RAM          | ❌ високий   | ✅ мінімальний |
| CPU          | ❌ постійний | ✅ імпульсний  |
| Стабільність | ❌ падає     | ✅ роками      |
| Zero 2 W     | ❌ критично  | ✅ ідеально    |

📌 **MQTT — стандарт для IoT**, Home Assistant оптимізований саме під нього.

---

## 📦 requirements.txt

```txt
smbus2
bme280
paho-mqtt
```

📌 Flask / Gunicorn **не потрібні** для передачі даних у HA.

            "availability_topic": "bme280/availability",
            "unique_id": f"bme280_{key}",
            "device": {
                "identifiers": ["bme280_pi"],
                "name": "BME280 Sensor",
                "model": "BME280",
                "manufacturer": "Bosch"
            }
        }
        client.publish(topic, json.dumps(payload), retain=True)
```

📌 Викликати **один раз при старті**.

---

## 🔔 Алерти в Home Assistant

Приклад автоматизації:

* Температура > 30°C → Telegram
* Вологість < 30% → MQTT / Notification

HA все робить **без Raspberry Pi**.

---

## 📤 Експорт у Grafana

* Home Assistant → InfluxDB addon
---

## 🔌 Налаштування Mosquitto в Home Assistant

1. **Settings → Add-ons → Mosquitto broker → Install**
* MQTT → HA → InfluxDB
            "value_template": f"{{{{ value_json.{key} }}}}",
* Grafana читає InfluxDB
            "unit_of_measurement": meta["unit"],

📌 Raspberry Pi **не зберігає історію**.

            "device_class": meta["device_class"],
---

2. Запустити addon
## 🧰 Systemd сервіс (автозапуск)

```ini
[Unit]
Description=BME280 MQTT Publisher
After=network.target

[Service]
ExecStart=/home/pi/myenv/bin/python /home/pi/bme280_mqtt.py
Restart=always
User=pi
3. Створити користувача:

[Install]
WantedBy=multi-user.target
```

---

## 🟢 Переваги фінальної системи

* ✅ працює місяцями без падінь
* ✅ мінімум RAM / CPU
* ✅ Zero 2 W не перегрівається
* ✅ Home Assistant — центр логіки

---

## 🚫 Що НЕ використовуємо

* ❌ Flask dev server
* ❌ Gunicorn
* ❌ WebSocket
* ❌ polling / fetch

---

## 🧭 Рекомендований розвиток

* MQTT TLS
* OTA оновлення
* кілька датчиків
* ESP32 як альтернатива

---

✍️ README створений для **стабільного продакшену**, а не демо.

   * Settings → People → Users
        topic = f"homeassistant/sensor/bme280_{key}/config"
        payload = {
            "name": f"BME280 {key}",
            "state_topic": "bme280/state",
4. Увімкнути MQTT інтеграцію

Mosquitto слухає:

    for key, meta in sensors.items():

* Host: IP Home Assistant
* Port: `1883`
    }

---

        }
## 🧠 MQTT Topics (прийнята схема)

```
            "device_class": "pressure"
bme280/state
bme280/availability
homeassistant/sensor/bme280_temperature/config
        "pressure": {
            "unit": "hPa",
homeassistant/sensor/bme280_humidity/config
homeassistant/sensor/bme280_pressure/config
```

---

        },
## 🧪 Python: читання BME280 + MQTT publish
            "device_class": "humidity"

```python
import time
import json
import smbus2
import bme280
import paho.mqtt.client as mqtt
from datetime import datetime

I2C_ADDR = 0x76
MQTT_HOST = "192.168.1.10"  # IP Home Assistant
MQTT_USER = "mqtt"
            "unit": "%",
MQTT_PASS = "password"
        "humidity": {

bus = smbus2.SMBus(1)
calibration = bme280.load_calibration_params(bus, I2C_ADDR)

client = mqtt.Client(client_id="bme280_pi")
client.username_pw_set(MQTT_USER, MQTT_PASS)

        },
client.will_set("bme280/availability", "offline", retain=True)
client.connect(MQTT_HOST, 1883)

            "device_class": "temperature"
client.publish("bme280/availability", "online", retain=True)

            "unit": "°C",
while True:
    data = bme280.sample(bus, I2C_ADDR, calibration)

    payload = {
        "temperature": round(data.temperature, 2),
        "temperature": {

def publish_config(client):
    sensors = {
        "humidity": round(data.humidity, 2),
        "pressure": round(data.pressure, 2),
import json
        "ts": datetime.now().isoformat()
    }

    client.publish(
```python
        "bme280/state",
        json.dumps(payload),
        retain=True

    )


## 🧙 MQTT Discovery (автоматичні сенсори)
    time.sleep(30)
```

