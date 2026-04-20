import threading
import json
import logging
import time
import random

# --- LOGGING CONFIGURATION ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%m %H:%M:%S'
)
try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False
from flask import Flask, render_template, Response
from waitress import serve

app = Flask(__name__)

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600
# ---------------------

# --- GLOBAL STATE (Dictionary avoids scoping issues) ---
STATE = {
    'system_status': "Healthy",
    'total_data_points': 0,
    'transmitted_data_points': 0,
    'last_tx_time': time.time(),
    'last_real_data_time': 0,
    'current_data': {
        'ax': 0, 'ay': 0, 'az': 0,
        'gx': 0, 'gy': 0, 'gz': 0
    },
    'previous_data': {
        'ax': 0, 'ay': 0, 'az': 0
    },
    'co2_saved': 0.0, # in grams
    'radio_state': "DEEP SLEEP",
    'anomaly_count': 0,
    'mock_anomaly_duration': 0
}

def calculate_co2_saved():
    # Simple linear saving model
    STATE['co2_saved'] += 0.05

def serial_listener():
    """Background thread that listens to the Serial port."""
    while True:
        try:
            logging.info(f"SERIAL: Attempting to connect to {SERIAL_PORT}...")
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1.0)
            ser.reset_input_buffer()
            time.sleep(0.5) 
            logging.info(f"SERIAL: SUCCESS! Connected to {SERIAL_PORT}.")
            
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Debug: Show EXACTLY what is being received
                logging.debug(f"DEBUG RAW: '{line}'")
                
                # Skip header or empty lines
                if any(h in line for h in ["aX", "Accel", "Timestamp"]):
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 7:
                    try:
                        # Handle potential label prefixes like "aX: 1.23"
                        def clean_val(s):
                            if ':' in s: return s.split(':')[-1].strip()
                            return s

                        ax = float(clean_val(parts[0]))
                        ay = float(clean_val(parts[1]))
                        az = float(clean_val(parts[2]))
                        gx = float(clean_val(parts[3]))
                        gy = float(clean_val(parts[4]))
                        gz = float(clean_val(parts[5]))
                        status_str = parts[6]
                        
                        STATE['current_data'] = {
                            'ax': ax, 'ay': ay, 'az': az,
                            'gx': gx, 'gy': gy, 'gz': gz
                        }
                        STATE['total_data_points'] += 1
                        STATE['last_real_data_time'] = time.time()
                        
                        STATE['system_status'] = "Healthy" if status_str.upper() in ["OK", "HEALTHY"] else status_str
                        if STATE['system_status'] != "Healthy":
                            STATE['anomaly_count'] += 1
                            
                        logging.info(f"SERIAL VALID: {STATE['current_data']['ax']}, {STATE['current_data']['ay']} | STATUS: {STATE['system_status']}")
                        
                    except ValueError as ve:
                        logging.error(f"SERIAL PARSE ERROR: {ve} in line: {line}")
        
        except serial.SerialException as e:
            if "Busy" in str(e) or "Permission" in str(e):
                logging.critical(f"SERIAL CRITICAL: Port {SERIAL_PORT} is BUSY or ACCESS DENIED.")
            else:
                logging.error(f"SERIAL ERROR: {e}")
            time.sleep(2)
        except Exception as e:
            logging.error(f"SERIAL UNKNOWN ERROR: {e}")
            time.sleep(2)

def get_data_payload():
    # If no data has arrived in the last 2 seconds, use mock data
    is_mocking = (time.time() - STATE['last_real_data_time'] > 2.0)
    
    if is_mocking:
        STATE['current_data'] = {
            'ax': random.uniform(-0.05, 0.05),
            'ay': random.uniform(-0.05, 0.05),
            'az': random.uniform(0.95, 1.05),
            'gx': random.uniform(-1, 1),
            'gy': random.uniform(-1, 1),
            'gz': random.uniform(-1, 1)
        }
        STATE['total_data_points'] += 1
        if STATE['mock_anomaly_duration'] > 0:
            STATE['system_status'] = "ANOMALY DETECTED"
            STATE['mock_anomaly_duration'] -= 1
        else:
            STATE['system_status'] = "Mocking Data (No Sensor)"
    
    is_cloud_transmitted = (STATE['system_status'] in ["ANOMALY", "Anomaly Detected"] or STATE['total_data_points'] % 20 == 0)
    
    # Calculate sensor delta for TAIL vs DEEP SLEEP
    delta = abs(STATE['current_data']['ax'] - STATE['previous_data']['ax']) + \
            abs(STATE['current_data']['ay'] - STATE['previous_data']['ay']) + \
            abs(STATE['current_data']['az'] - STATE['previous_data']['az'])
    
    # Update previous data for next comparison
    STATE['previous_data'] = {
        'ax': STATE['current_data']['ax'],
        'ay': STATE['current_data']['ay'],
        'az': STATE['current_data']['az']
    }

    # Radio State logic requested by user:
    # 1. ACTIVE = Anomaly
    # 2. TAIL = Changing values (delta > threshold)
    # 3. DEEP SLEEP = Stable values
    if STATE['system_status'] in ["ANOMALY", "Anomaly Detected"]:
        STATE['radio_state'] = "ACTIVE"
    elif delta > 0.1: # Significant change threshold for TAIL
        STATE['radio_state'] = "TAIL"
    else:
        STATE['radio_state'] = "DEEP SLEEP"

    if is_cloud_transmitted:
        STATE['transmitted_data_points'] += 1
        STATE['last_tx_time'] = time.time()
    else:
        calculate_co2_saved()

    efficiency = round((1 - (STATE['transmitted_data_points'] / STATE['total_data_points'])) * 100, 1)
    
    return {
        'ax': round(STATE['current_data']['ax'], 3),
        'ay': round(STATE['current_data']['ay'], 3),
        'az': round(STATE['current_data']['az'], 3),
        'gx': round(STATE['current_data']['gx'], 3),
        'gy': round(STATE['current_data']['gy'], 3),
        'gz': round(STATE['current_data']['gz'], 3),
        'status': STATE['system_status'],
        'efficiency': efficiency,
        'co2_saved': round(STATE['co2_saved'], 2),
        'transmitted': is_cloud_transmitted,
        'radio_state': STATE['radio_state'],
        'timestamp': time.strftime("%H:%M:%S"),
        'total_points': STATE['total_data_points'],
        'transmitted_points': STATE['transmitted_data_points'],
        'is_real': not is_mocking
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chart-data')
def chart_data():
    def generate():
        while True:
            data = get_data_payload()
            if data:
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.5)
            
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/mock_anomaly', methods=['POST'])
def mock_anomaly():
    STATE['system_status'] = "ANOMALY DETECTED"
    STATE['anomaly_count'] += 1
    STATE['mock_anomaly_duration'] = 10 # Last for ~5 seconds (at 0.5s intervals)
    return {"status": "success", "count": STATE['anomaly_count']}

@app.route('/chat', methods=['POST'])
def chat():
    from flask import request
    query = request.json.get('query', '').lower()
    
    # Nibble AI: Short, Simple, Edge-focused responses
    if any(k in query for k in ["how many anomalies", "anomaly count", "how many errors"]):
        count = STATE['anomaly_count']
        if count == 0:
            return {"response": "Zero anomalies detected. The system is operating within nominal parameters."}
        return {"response": f"I've recorded {count} anomalies so far. Most recent event was handled by URLLC priority uplink."}

    if any(k in query for k in ["anomaly", "anomalies", "errors", "broken"]):
        status = STATE['system_status']
        if status == "Healthy":
            return {"response": "System is currently Healthy. Vibrations are stable."}
        return {"response": f"Current status is {status}. High-frequency vibrations detected! Transmitting to edge node."}
    
    if any(k in query for k in ["efficiency", "bandwidth", "saved", "performance"]):
        eff = round((1 - (STATE['transmitted_data_points'] / max(1, STATE['total_data_points']))) * 100, 1)
        return {"response": f"6G bandwidth efficiency is at {eff}%. Our Edge AI is filtering {STATE['total_data_points'] - STATE['transmitted_data_points']} redundant telemetry packets."}

    if any(k in query for k in ["co2", "carbon", "sustainability", "green"]):
        return {"response": f"We have mitigated {round(STATE['co2_saved'], 2)}g of CO₂ emissions by reducing cloud transmission frequency."}

    if any(k in query for k in ["csv", "file", "download", "data", "discuss"]):
        return {"response": f"The CSV log currently contains {STATE['total_data_points']} data points. It shows a clear correlation between vibration spikes and anomaly triggers."}

    if any(k in query for k in ["status", "mode", "radio"]):
        return {"response": f"System: {STATE['system_status']}. Radio State: {STATE['radio_state']} (Optimal power mode)."}

    if any(k in query for k in ["hello", "hi", "who are you"]):
        return {"response": "I'm Nibble AI, your 6G Edge Assistant. I monitor telemetry and help you optimize network performance."}

    return {"response": "I'm not sure about that. Try asking about 'anomalies', 'efficiency', or 'sustainability'."}

if __name__ == '__main__':
    # Start Serial Listener
    serial_thread = threading.Thread(target=serial_listener, daemon=True)
    serial_thread.start()
    
    logging.info("Dashboard server starting on http://localhost:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)
