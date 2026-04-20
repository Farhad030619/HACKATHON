const source = new EventSource("/chart-data");

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
            x: {
                display: false
            },
            y: {
                beginAtZero: false,
                grid: {
                    color: 'rgba(255, 255, 255, 0.05)'
                },
                ticks: {
                    color: '#a0a0a0'
                }
            }
        },
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    color: '#ffffff',
                    usePointStyle: true,
                    padding: 20
                }
            }
        },
        animation: {
            duration: 0 // Disable animation for smoother streaming
        }
    }
});

const MAX_DATA_POINTS = 50;
let timeIndex = 0;

source.onmessage = function(event) {
    const data = JSON.parse(event.data);
    // Update Chart
    chart.data.labels.push('');
    chart.data.datasets[0].data.push(data.x);
    chart.data.datasets[1].data.push(data.y);
    chart.data.datasets[2].data.push(data.z);

    if (chart.data.labels.length > MAX_DATA_POINTS) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
        chart.data.datasets[1].data.shift();
        chart.data.datasets[2].data.shift();
    }
    chart.update('none'); // Update without animation for performance

    // Update Status
    const statusIndicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    if (data.status === 'Healthy') {
        statusIndicator.className = 'status-indicator status-healthy';
        statusText.innerText = 'SYSTEM HEALTHY';
        statusText.style.color = '#00ff88';
    } else {
        statusIndicator.className = 'status-indicator status-anomaly';
        statusText.innerText = 'ANOMALY DETECTED';
        statusText.style.color = '#ff3366';
    }

    // Update Efficiency based on mode
    updateEfficiencyDisplay(data);

    // Update CO2
    document.getElementById('co2Value').innerText = data.co2_saved.toFixed(2);

    // Update Raw Telemetry
    document.getElementById('rawX').innerText = data.x.toFixed(3);
    document.getElementById('rawY').innerText = data.y.toFixed(3);
    document.getElementById('rawZ').innerText = data.z.toFixed(3);
    document.getElementById('lastUpdate').innerText = data.timestamp;

    // Visual feedback for 'Cloud Transmission'
    const efficiencyCard = document.getElementById('efficiencyCard');
    if (data.transmitted) {
        efficiencyCard.style.boxShadow = '0 0 20px rgba(0, 229, 255, 0.2)';
        setTimeout(() => {
            efficiencyCard.style.boxShadow = 'none';
        }, 300);
    }
});

let efficiencyMode = 'PERCENTAGE'; // 'PERCENTAGE' or 'REAL_WORLD'

function toggleEfficiencyMode() {
    efficiencyMode = (efficiencyMode === 'PERCENTAGE') ? 'REAL_WORLD' : 'PERCENTAGE';
    document.getElementById('efficiencyMode').innerText = efficiencyMode.replace('_', ' ');
    // Re-trigger update will happen on next message
}

function updateEfficiencyDisplay(data) {
    const valueEl = document.getElementById('efficiencyValue');
    const labelEl = document.getElementById('efficiencyLabel');

    if (efficiencyMode === 'PERCENTAGE') {
        valueEl.innerText = data.efficiency + '%';
        labelEl.innerText = 'Bandwidth Saved';
    } else {
        // Real world: 100 bytes per message
        const bytesSaved = (data.total_points - data.transmitted_points) * 100;
        if (bytesSaved > 1024 * 1024) {
            valueEl.innerText = (bytesSaved / (1024 * 1024)).toFixed(2) + ' MB';
        } else {
            valueEl.innerText = (bytesSaved / 1024).toFixed(1) + ' KB';
        }
        labelEl.innerText = 'Data Saved (Estimated)';
    }
}
