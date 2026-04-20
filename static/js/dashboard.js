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

    // Update Efficiency
    document.getElementById('efficiencyValue').innerText = data.efficiency + '%';
});
