import time
import random
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ericsson-6g-hackathon'
socketio = SocketIO(app, cors_allowed_origins="*")

# State variables
system_status = "Healthy"
data_saved_percentage = 0.0
total_data_points = 0
transmitted_data_points = 0

def generate_mock_data():
    """Generates mock accelerometer data and system status for demo purposes."""
    global system_status, data_saved_percentage, total_data_points, transmitted_data_points
    
    while True:
        # Simulate high-frequency internal sampling (100Hz)
        # But we only 'transmit' if there's an anomaly or a heartbeat
        for _ in range(10):
            total_data_points += 1
            
            # Normal vibration levels
            x = random.uniform(-0.1, 0.1)
            y = random.uniform(-0.1, 0.1)
            z = random.uniform(0.9, 1.1) # Gravity
            
            # Randomly trigger an anomaly
            if random.random() < 0.01:
                system_status = "Anomaly Detected"
                # High vibration
                x += random.uniform(-1.5, 1.5)
                y += random.uniform(-1.5, 1.5)
                z += random.uniform(-1.5, 1.5)
            
            # Logic: Transmit if anomaly or every 100 points (heartbeat)
            if system_status == "Anomaly Detected" or total_data_points % 100 == 0:
                transmitted_data_points += 1
                
                socketio.emit('sensor_data', {
                    'x': round(x, 3),
                    'y': round(y, 3),
                    'z': round(z, 3),
                    'status': system_status,
                    'efficiency': round((1 - (transmitted_data_points / total_data_points)) * 100, 1)
                })
                
                # Reset status after some time if it was an anomaly
                if system_status == "Anomaly Detected":
                    time.sleep(0.1) # Stay in anomaly state for a bit
                    if random.random() < 0.2:
                        system_status = "Healthy"
            
            time.sleep(0.1) # 10Hz transmission for the web UI

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Start mock data generator in a background thread
    data_thread = threading.Thread(target=generate_mock_data, daemon=True)
    data_thread.start()
    
    print("Dashboard server starting on http://localhost:5001")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
