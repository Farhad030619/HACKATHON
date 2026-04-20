import time
import random
import threading
import json
import serial
import serial.tools.list_ports
from flask import Flask, render_template, Response
from waitress import serve

app = Flask(__name__)

# --- CONFIGURATION ---
BAUD_RATE = 115200
# ---------------------

# State variables for metrics
system_status = "Healthy"
total_data_points = 0
transmitted_data_points = 0
current_data = {'x': 0, 'y': 0, 'z': 0}

def find_serial_port():
    """Attempts to find the USB serial port for the sensor."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # Look for common Arduino/XIAO names
        if 'usbmodem' in port.device or 'ttyACM' in port.device:
            return port.device
    return None

def serial_listener():
    """Background thread that listens to the actual Serial port."""
    global system_status, total_data_points, transmitted_data_points, current_data
    
    port = find_serial_port()
    if not port:
        print("WARNING: No Serial port found. Falling back to Mock Data for demo.")
        return # Thread will exit and app continues with mock logic if needed

    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=1)
        print(f"CONNECTED to sensor on {port}")
        
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                try:
                    # Expecting format: x,y,z
                    parts = line.split(',')
                    if len(parts) == 3:
                        x, y, z = map(float, parts)
                        current_data = {'x': x, 'y': y, 'z': z}
                        
                        # Here you can add your Anomaly Detection logic
                        # For now, we'll just flag high vibrations
                        if abs(x) > 1.5 or abs(y) > 1.5:
                            system_status = "Anomaly Detected"
                        else:
                            system_status = "Healthy"
                            
                        total_data_points += 1
                except Exception as e:
                    print(f"Data parse error: {e}")
    except Exception as e:
        print(f"Serial error: {e}")

def get_data_payload():
    """Generates the payload for the SSE stream (Mock or Real)."""
    global system_status, total_data_points, transmitted_data_points, current_data
    
    # If we are using mock data (no real serial data coming in)
    if total_data_points == 0:
        total_data_points += 1
        x = random.uniform(-0.1, 0.1)
        y = random.uniform(-0.1, 0.1)
        z = random.uniform(0.9, 1.1)
        if random.random() < 0.05:
            system_status = "Anomaly Detected"
            x += random.uniform(-1.5, 1.5)
        else:
            if random.random() < 0.1: system_status = "Healthy"
        current_data = {'x': x, 'y': y, 'z': z}

    # Uplink Efficiency Logic: Only 'transmit' to UI if anomaly or heartbeat
    if system_status == "Anomaly Detected" or total_data_points % 20 == 0:
        transmitted_data_points += 1
        efficiency = round((1 - (transmitted_data_points / total_data_points)) * 100, 1)
        
        return {
            'x': round(current_data['x'], 3),
            'y': round(current_data['y'], 3),
            'z': round(current_data['z'], 3),
            'status': system_status,
            'efficiency': efficiency
        }
    return None

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
    # Start Serial Listener in background
    serial_thread = threading.Thread(target=serial_listener, daemon=True)
    serial_thread.start()
    
    print("Dashboard server starting on http://localhost:5001")
    serve(app, host='0.0.0.0', port=5001, threads=4)
