let source;

function initEventSource() {
    if (source) source.close();
    source = new EventSource("/chart-data");

    source.onmessage = function(event) {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };

    source.onerror = function(err) {
        console.error("EventSource connection lost. Retrying in 1s...");
        source.close();
        setTimeout(initEventSource, 1000);
    };
}

// Chart Configuration
const ctx = document.getElementById('vibrationChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'X-Axis',
                borderColor: '#00e5ff',
                backgroundColor: 'rgba(0, 229, 255, 0.1)',
                data: [],
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0
            },
            {
                label: 'Y-Axis',
                borderColor: '#ff00ff',
                backgroundColor: 'rgba(255, 0, 255, 0.1)',
                data: [],
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0
            },
            {
                label: 'Z-Axis',
                borderColor: '#ffffff',
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                data: [],
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 0
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            x: { display: false },
            y: {
                beginAtZero: false,
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#a0a0a0' }
            }
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#ffffff', usePointStyle: true, padding: 20 }
            }
        },
        animation: { duration: 0 }
    }
});

const MAX_DATA_POINTS = 50;
let efficiencyMode = 'PERCENTAGE';
let telemetryHistory = [];

function updateDashboard(data) {
    // Save to history for CSV export
    telemetryHistory.push({
        timestamp: data.timestamp,
        ax: data.ax,
        ay: data.ay,
        az: data.az,
        gx: data.gx,
        gy: data.gy,
        gz: data.gz,
        status: data.status,
        is_real: data.is_real
    });

    // Keep history manageable (e.g., last 1000 points)
    if (telemetryHistory.length > 1000) {
        telemetryHistory.shift();
    }

    // Update Chart
    chart.data.labels.push('');
    chart.data.datasets[0].data.push(data.ax);
    chart.data.datasets[1].data.push(data.ay);
    chart.data.datasets[2].data.push(data.az);

    if (chart.data.labels.length > MAX_DATA_POINTS) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
        chart.data.datasets[2].data.shift();
    }
    chart.update('none');

    // Update Status
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (data.status === 'Healthy') {
        statusIndicator.className = 'status-indicator status-healthy';
        statusText.innerText = 'SYSTEM HEALTHY';
        statusText.style.color = '#00ff88';
    } else {
        statusIndicator.className = 'status-indicator status-anomaly';
        statusText.innerText = data.status.toUpperCase();
        statusText.style.color = '#ff3366';
    }

    // Update Efficiency
    updateEfficiencyDisplay(data);

    // Update Radio State
    updateRadioStateDisplay(data);

    // Update CO2
    document.getElementById('co2Value').innerText = data.co2_saved.toFixed(2);

    // Update Telemetry
    document.getElementById('rawAX').innerText = data.ax.toFixed(3);
    document.getElementById('rawAY').innerText = data.ay.toFixed(3);
    document.getElementById('rawAZ').innerText = data.az.toFixed(3);
    
    if (document.getElementById('rawGX')) {
        document.getElementById('rawGX').innerText = data.gx.toFixed(2);
        document.getElementById('rawGY').innerText = data.gy.toFixed(2);
        document.getElementById('rawGZ').innerText = data.gz.toFixed(2);
    }
    
    document.getElementById('lastUpdate').innerText = data.timestamp;

    // Update Console
    updateConsole(data);

    // Visual feedback
    const efficiencyCard = document.getElementById('efficiencyCard');
    if (data.transmitted) {
        efficiencyCard.style.boxShadow = '0 0 20px rgba(0, 229, 255, 0.2)';
        setTimeout(() => { efficiencyCard.style.boxShadow = 'none'; }, 300);
    }
}

function updateConsole(data) {
    const consoleOutput = document.getElementById('consoleOutput');
    const line = document.createElement('div');
    line.className = 'console-line';
    
    const isAnomaly = data.status !== 'Healthy' && data.status !== 'OK';
    const messageClass = isAnomaly ? 'console-message anomaly' : 'console-message';
    
    // Format: [HH:MM:SS] aX: 0.000, aY: 0.000, aZ: 0.000 | Status: OK
    line.innerHTML = `
        <span class="console-timestamp">[${data.timestamp}]</span>
        <span class="${messageClass}">
            ACCEL: ${data.ax.toFixed(3)}, ${data.ay.toFixed(3)}, ${data.az.toFixed(3)} | 
            GYRO: ${data.gx.toFixed(2)}, ${data.gy.toFixed(2)}, ${data.gz.toFixed(2)} | 
            STATUS: ${data.status}
        </span>
    `;
    
    consoleOutput.appendChild(line);
    
    // Limit console lines to 50
    if (consoleOutput.children.length > 50) {
        consoleOutput.removeChild(consoleOutput.firstChild);
    }
    
    // Auto-scroll
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function downloadCSV() {
    if (telemetryHistory.length === 0) {
        alert("No data to export yet!");
        return;
    }

    const headers = ["Timestamp", "aX", "aY", "aZ", "gX", "gY", "gZ", "Status", "IsReal"];
    const csvRows = [headers.join(",")];

    telemetryHistory.forEach(d => {
        const row = [
            d.timestamp,
            d.ax.toFixed(3),
            d.ay.toFixed(3),
            d.az.toFixed(3),
            d.gx.toFixed(2),
            d.gy.toFixed(2),
            d.gz.toFixed(2),
            d.status,
            d.is_real ? "YES" : "NO"
        ];
        csvRows.push(row.join(","));
    });

    const csvString = csvRows.join("\n");
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    const fileName = `nibble_ai_log_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function toggleEfficiencyMode() {
    efficiencyMode = (efficiencyMode === 'PERCENTAGE') ? 'REAL_WORLD' : 'PERCENTAGE';
    document.getElementById('efficiencyMode').innerText = efficiencyMode.replace('_', ' ');
}

function updateEfficiencyDisplay(data) {
    const valueEl = document.getElementById('efficiencyValue');
    const labelEl = document.getElementById('efficiencyLabel');

    if (efficiencyMode === 'PERCENTAGE') {
        valueEl.innerText = data.efficiency + '%';
        labelEl.innerText = 'Bandwidth Saved';
    } else {
        const bytesSaved = (data.total_points - data.transmitted_points) * 100;
        if (bytesSaved > 1024 * 1024) {
            valueEl.innerText = (bytesSaved / (1024 * 1024)).toFixed(2) + ' MB';
        } else {
            valueEl.innerText = (bytesSaved / 1024).toFixed(1) + ' KB';
        }
        labelEl.innerText = 'Data Saved (Estimated)';
    }
}


function updateRadioStateDisplay(data) {
    const radioEl = document.getElementById('radioState');
    if (!radioEl) return;

    const state = data.radio_state;
    radioEl.innerText = state;
    
    // Convert "DEEP SLEEP" to "DEEP-SLEEP" for CSS class
    const cssClass = state.replace(' ', '-');
    radioEl.className = `radio-state ${cssClass}`;
}

// Start connection
initEventSource();
