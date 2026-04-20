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

function updateDashboard(data) {
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

    // Visual feedback
    const efficiencyCard = document.getElementById('efficiencyCard');
    if (data.transmitted) {
        efficiencyCard.style.boxShadow = '0 0 20px rgba(0, 229, 255, 0.2)';
        setTimeout(() => { efficiencyCard.style.boxShadow = 'none'; }, 300);
    }
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

// Start connection
initEventSource();
