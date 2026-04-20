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
    'co2_saved': 0.0, # in grams
    'radio_state': "DEEP SLEEP"
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
        STATE['system_status'] = "Mocking Data (No Sensor)"
    
    is_cloud_transmitted = (STATE['system_status'] in ["ANOMALY", "Anomaly Detected"] or STATE['total_data_points'] % 20 == 0)
    
    # Calculate Radio State based on transmission
    if is_cloud_transmitted:
        STATE['radio_state'] = "ACTIVE"
        STATE['last_tx_time'] = time.time()
        STATE['transmitted_data_points'] += 1
    else:
        # If not active, check if we are in "Tail" period (2 seconds after TX)
        time_since_tx = time.time() - STATE['last_tx_time']
        if time_since_tx < 2.0:
            STATE['radio_state'] = "TAIL"
        else:
            STATE['radio_state'] = "DEEP SLEEP"
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

if __name__ == '__main__':
    # Start Serial Listener
    serial_thread = threading.Thread(target=serial_listener, daemon=True)
    serial_thread.start()
    
    logging.info("Dashboard server starting on http://localhost:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)
