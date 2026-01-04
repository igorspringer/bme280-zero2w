import time
import threading
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template_string
import smbus2
import bme280

# ================= CONFIG =================
I2C_ADDR = 0x76
DB_PATH = "bme280.db"
READ_INTERVAL = 30        # сек
HISTORY_DAYS = 7

# ================ FLASK ==================
app = Flask(__name__)

bus = smbus2.SMBus(1)
calibration_params = bme280.load_calibration_params(bus, I2C_ADDR)

last_data = {"temperature": None, "humidity": None, "pressure": None, "ts": None}

# ================== DB ===================
def db_connect():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    with db_connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                temperature REAL,
                humidity REAL,
                pressure REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agg_1min (
                ts TEXT PRIMARY KEY,
                temp REAL,
                hum REAL,
                pres REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agg_10min (
                ts TEXT PRIMARY KEY,
                temp REAL,
                hum REAL,
                pres REAL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agg_1h (
                ts TEXT PRIMARY KEY,
                temp REAL,
                hum REAL,
                pres REAL
            )
        """)

def cleanup_db():
    limit = (datetime.now() - timedelta(days=HISTORY_DAYS)).isoformat()
    with db_connect() as conn:
        conn.execute("DELETE FROM readings WHERE ts < ?", (limit,))
        conn.execute("DELETE FROM agg_1min WHERE ts < ?", (limit,))
        conn.execute("DELETE FROM agg_10min WHERE ts < ?", (limit,))
        conn.execute("DELETE FROM agg_1h WHERE ts < ?", (limit,))

init_db()

# ================= SENSOR =================
def sensor_worker():
    global last_data
    while True:
        try:
            data = bme280.sample(bus, I2C_ADDR, calibration_params)
            t = round(data.temperature, 2)
            h = round(data.humidity, 2)
            p = round(data.pressure, 2)
            ts = datetime.now().isoformat()

            last_data = {"temperature": t, "humidity": h, "pressure": p, "ts": ts}

            with db_connect() as conn:
                conn.execute(
                    "INSERT INTO readings (ts, temperature, humidity, pressure) VALUES (?,?,?,?)",
                    (ts, t, h, p)
                )
                # Агрегація 1 хв
                conn.execute("""
                    INSERT OR REPLACE INTO agg_1min (ts, temp, hum, pres)
                    VALUES (?, ?, ?, ?)
                """, (ts[:16], t, h, p))  # ts[:16] => YYYY-MM-DDTHH:MM

            cleanup_db()
        except Exception as e:
            print("Sensor error:", e)

        time.sleep(READ_INTERVAL)

threading.Thread(target=sensor_worker, daemon=True).start()

# ================= FLASK ROUTES =================
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>BME280 Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{font-family:Arial;background:#121212;color:#e0e0e0} .chart{width:600px;margin:20px;background:#1e1e1e;padding:20px;border-radius:10px;}</style>
</head>
<body>
<h1>BME280 Dashboard</h1>
<div class="chart"><canvas id="t"></canvas></div>
<div class="chart"><canvas id="h"></canvas></div>
<div class="chart"><canvas id="p"></canvas></div>

<script>
const MAX_POINTS=100;
function makeChart(id,label,color){return new Chart(document.getElementById(id),{type:'line',data:{labels:[],datasets:[{label,data:[],borderColor:color,tension:0.2}]},options:{animation:false}});}
function push(chart,label,value){chart.data.labels.push(label);chart.data.datasets[0].data.push(value);if(chart.data.labels.length>MAX_POINTS){chart.data.labels.shift();chart.data.datasets[0].data.shift();}chart.update();}
const ct=makeChart("t","Temp °C","red"),ch=makeChart("h","Humidity %","blue"),cp=makeChart("p","Pressure hPa","green");
async function update(){
  const r=await fetch("/data");
  const d=await r.json();
  const t=new Date(d.ts).toLocaleTimeString();
  push(ct,t,d.temperature);
  push(ch,t,d.humidity);
  push(cp,t,d.pressure);
}
setInterval(update,5000);
update();
</script>
</body>
</html>
""")

@app.route("/data")
def data():
    return jsonify(last_data)

@app.route("/history")
def history():
    since = (datetime.now() - timedelta(hours=24)).isoformat()
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT ts, temperature, humidity, pressure FROM readings WHERE ts>=? ORDER BY ts ASC",
            (since,)
        ).fetchall()
    return jsonify(rows)

@app.route("/export/csv")
def export_csv():
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ts","temperature","humidity","pressure"])
    with db_connect() as conn:
        for row in conn.execute("SELECT ts,temperature,humidity,pressure FROM readings ORDER BY ts"):
            writer.writerow(row)
    return output.getvalue(), 200, {'Content-Type':'text/csv'}

# ================= RUN =================
if __name__=="__main__":
    # Запуск через Gunicorn
    pass