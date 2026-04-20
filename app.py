import time
import random
import threading
import json
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

# State variables
system_status = "Healthy"
total_data_points = 0
transmitted_data_points = 0
last_real_data_time = 0
current_data = {
    'ax': 0, 'ay': 0, 'az': 0,
    'gx': 0, 'gy': 0, 'gz': 0
}
co2_saved = 0.0 # in grams

def calculate_co2_saved(efficiency):
    global co2_saved
    co2_saved += 0.05 

def serial_listener():
    """Background thread that listens to the Serial port."""
    global system_status, total_data_points, transmitted_data_points, current_data, last_real_data_time
    
    if not HAS_SERIAL:
        return

    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        ser.flushInput()
        time.sleep(1) 
        print(f"SERIAL: Connected to {SERIAL_PORT} at {BAUD_RATE} baud.")
        
        while True:
            if ser.in_waiting > 0:
                byte_string = ser.readline()
                try:
                    line = byte_string.decode('utf-8', errors='ignore').strip()
                    if not line: continue
                    
                    # Log the raw line for debugging
                    print(f"SERIAL Received: {line}")
                    
                    if "aX" in line: continue # Skip header
                    
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 7:
                        try:
                            ax, ay, az = map(float, parts[0:3])
                            gx, gy, gz = map(float, parts[3:6])
                            status_str = parts[6]
                            
                            current_data = {
                                'ax': ax, 'ay': ay, 'az': az,
                                'gx': gx, 'gy': gy, 'gz': gz
                            }
                            total_data_points += 1
                            last_real_data_time = time.time()
                            
                            if status_str.upper() == "OK":
                                system_status = "Healthy"
                            else:
                                system_status = status_str
                        except ValueError:
                            print(f"SERIAL ERROR: Could not parse floats in line: {line}")
                except Exception as e:
                    print(f"SERIAL DECODE ERROR: {e}")
            else:
                time.sleep(0.01) # Small sleep to prevent CPU hogging
    except Exception as e:
        print(f"SERIAL ERROR: {e}")
        time.sleep(2) # Wait before retry if port fails

def get_data_payload():
    global system_status, total_data_points, transmitted_data_points, current_data, co2_saved, last_real_data_time
    
    # If no data has arrived in the last 2 seconds, use mock data
    is_mocking = (time.time() - last_real_data_time > 2.0)
    
    if is_mocking:
        ax = random.uniform(-0.05, 0.05)
        ay = random.uniform(-0.05, 0.05)
        az = random.uniform(0.95, 1.05)
        gx = random.uniform(-1, 1)
        gy = random.uniform(-1, 1)
        gz = random.uniform(-1, 1)
        current_data = {
            'ax': ax, 'ay': ay, 'az': az,
            'gx': gx, 'gy': gy, 'gz': gz
        }
        # In mock mode, we still increment total_points to keep the dashboard "alive"
        # but we don't update last_real_data_time
        total_data_points += 1
        system_status = "Mocking Data (No Sensor)"
    
    is_cloud_transmitted = (system_status == "ANOMALY" or system_status == "Anomaly Detected" or total_data_points % 20 == 0)
    
    if is_cloud_transmitted:
        transmitted_data_points += 1
    else:
        calculate_co2_saved(0)

    efficiency = round((1 - (transmitted_data_points / total_data_points)) * 100, 1)
    
    return {
        'ax': round(current_data['ax'], 3),
        'ay': round(current_data['ay'], 3),
        'az': round(current_data['az'], 3),
        'gx': round(current_data['gx'], 3),
        'gy': round(current_data['gy'], 3),
        'gz': round(current_data['gz'], 3),
        'status': system_status,
        'efficiency': efficiency,
        'co2_saved': round(co2_saved, 2),
        'transmitted': is_cloud_transmitted,
        'timestamp': time.strftime("%H:%M:%S"),
        'total_points': total_data_points,
        'transmitted_points': transmitted_data_points,
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
            time.sleep(0.1)
            
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

if __name__ == '__main__':
    # Start Serial Listener
    serial_thread = threading.Thread(target=serial_listener, daemon=True)
    serial_thread.start()
    
    print("Dashboard server starting on http://localhost:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)
