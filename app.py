import time
import random
import threading
import json
import serial
from flask import Flask, render_template, Response
from waitress import serve

app = Flask(__name__)

# --- CONFIGURATION ---
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200
# ---------------------

# State variables
system_status = "Healthy"
total_data_points = 0
transmitted_data_points = 0
current_data = {'x': 0, 'y': 0, 'z': 0}
co2_saved = 0.0 # in grams

def calculate_co2_saved(efficiency):
    """
    Estimate CO2 saved by not transmitting raw data.
    Standard metric: ~0.05g CO2 saved per 'message' not sent over 5G.
    """
    global co2_saved
    # If efficiency is 90%, it means we saved 9 out of 10 transmissions
    # For every point saved, we add to the cumulative CO2 savings
    co2_saved += 0.05 

def serial_listener():
    """Background thread that listens to the Serial port as provided by user."""
    global system_status, total_data_points, transmitted_data_points, current_data
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(0.1) # stabilize
        print(f"CONNECTED to sensor on {SERIAL_PORT}")
        
        while True:
            byte_string = ser.readline()
            if byte_string:
                line = byte_string.decode('utf-8').strip()
                try:
                    # Parse format: x,y,z
                    parts = line.split(',')
                    if len(parts) == 3:
                        x, y, z = map(float, parts)
                        current_data = {'x': x, 'y': y, 'z': z}
                        total_data_points += 1
                        
                        # Simple anomaly detection logic
                        if abs(x) > 1.2 or abs(y) > 1.2:
                            system_status = "Anomaly Detected"
                        else:
                            system_status = "Healthy"
                except Exception as e:
                    pass # Ignore malformed lines
    except Exception as e:
        print(f"Serial error (will fallback to mock): {e}")

def get_data_payload():
    """Generates the payload for the SSE stream."""
    global system_status, total_data_points, transmitted_data_points, current_data, co2_saved
    
    # Fallback to mock if no real data is coming (for demo/testing)
    if total_data_points == 0:
        total_data_points += 1
        x = random.uniform(-0.1, 0.1)
        y = random.uniform(-0.1, 0.1)
        z = random.uniform(0.9, 1.1)
        current_data = {'x': x, 'y': y, 'z': z}
        if random.random() < 0.05: system_status = "Anomaly Detected"
        else: system_status = "Healthy"

    # Edge AI Logic: 
    # In a real scenario, only anomalies or periodic heartbeats are sent to the cloud.
    # But for our Edge Dashboard, we show everything.
    
    is_cloud_transmitted = (system_status == "Anomaly Detected" or total_data_points % 20 == 0)
    
    if is_cloud_transmitted:
        transmitted_data_points += 1
    else:
        # We saved a transmission! Add to CO2 savings.
        calculate_co2_saved(0)

    efficiency = round((1 - (transmitted_data_points / total_data_points)) * 100, 1)
    
    return {
        'x': round(current_data['x'], 3),
        'y': round(current_data['y'], 3),
        'z': round(current_data['z'], 3),
        'status': system_status,
        'efficiency': efficiency,
        'co2_saved': round(co2_saved, 2),
        'transmitted': is_cloud_transmitted,
        'timestamp': time.strftime("%H:%M:%S")
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
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    # Start Serial Listener
    serial_thread = threading.Thread(target=serial_listener, daemon=True)
    serial_thread.start()
    
    print("Dashboard server starting on http://localhost:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)
