const categoryData = JSON.parse(document.body.dataset.categoryCounts);
const statusData = JSON.parse(document.body.dataset.statusCounts);
const categoryLabels = Object.keys(categoryData);
const categoryValues = Object.values(categoryData);

new Chart(document.getElementById('categoryChart'), {
    type: 'bar',
    data: {
        labels: categoryLabels,
        datasets: [{
            label: 'Complaints',
            data: categoryValues,
            backgroundColor: ['#003366', '#0057b8', '#4e8ad8', '#7db4ff', '#dbeafe', '#cfe2ff'],
            borderRadius: 6
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
    }
});

new Chart(document.getElementById('statusChart'), {
    type: 'doughnut',
    data: {
        labels: ['Pending', 'In-Progress', 'Rejected', 'Resolved'],
        datasets: [{
            data: [
                statusData['Pending'] || 0,
                statusData['In-Progress'] || 0,
                statusData['Rejected'] || 0,
                statusData['Resolved'] || 0
            ],
            backgroundColor: ['#f4b942', '#0057b8', '#d9534f', '#2ca66b'],
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' },
            tooltip: {
                callbacks: {
                    label(context) {
                        const value = context.raw || 0;
                        const total = Object.values(statusData).reduce((sum, item) => sum + item, 0) || 1;
                        const percentage = ((value / total) * 100).toFixed(1);
                        return `${context.label}: ${value} (${percentage}%)`;
                    }
                }
            }
        }
    }
});
