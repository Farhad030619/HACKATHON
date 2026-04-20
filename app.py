import time
import random
import threading
import json
from flask import Flask, render_template, Response
from waitress import serve

app = Flask(__name__)

# State variables for metrics
system_status = "Healthy"
total_data_points = 0
transmitted_data_points = 0

def get_data():
    """Generates a single data point following the event-driven logic."""
    global system_status, total_data_points, transmitted_data_points
    
    total_data_points += 1
    
    # Normal vibration levels
    x = random.uniform(-0.1, 0.1)
    y = random.uniform(-0.1, 0.1)
    z = random.uniform(0.9, 1.1)
    
    # Randomly trigger an anomaly
    if random.random() < 0.05: # Slightly higher chance for demo visibility
        system_status = "Anomaly Detected"
        x += random.uniform(-1.5, 1.5)
        y += random.uniform(-1.5, 1.5)
        z += random.uniform(-1.5, 1.5)
    else:
        # Gradually return to healthy
        if random.random() < 0.3:
            system_status = "Healthy"
    
    # Logic: Transmit if anomaly or heartbeat (every 20 points for demo)
    if system_status == "Anomaly Detected" or total_data_points % 20 == 0:
        transmitted_data_points += 1
        efficiency = round((1 - (transmitted_data_points / total_data_points)) * 100, 1)
        
        return {
            'x': round(x, 3),
            'y': round(y, 3),
            'z': round(z, 3),
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
            data = get_data()
            if data:
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.1) # 10Hz sampling
            
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("Dashboard server starting on http://localhost:5001")
    print("Using Waitress (Production WSGI Server)")
    serve(app, host='0.0.0.0', port=5001, threads=4)
