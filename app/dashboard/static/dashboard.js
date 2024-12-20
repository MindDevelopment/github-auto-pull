// app/dashboard/static/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Repository updates
    const updateStatus = () => {
        const repoCards = document.querySelectorAll('.repo-card');
        repoCards.forEach(async card => {
            try {
                const response = await fetch(`/api/status/${card.dataset.repo}`);
                const data = await response.json();
                card.querySelector('.last-sync').textContent = data.lastSync;
                card.querySelector('.status-badge').className = 
                    `status-badge ${data.status}`;
            } catch (error) {
                console.error('Error updating status:', error);
            }
        });
    };

    // Update status elke minuut
    setInterval(updateStatus, 60000);
    updateStatus();

    // System status updates
    const updateSystemStatus = async () => {
        try {
            const response = await fetch('/api/system-status');
            const data = await response.json();
            document.getElementById('sync-status').className = 
                `status-badge ${data.syncStatus}`;
            document.getElementById('webhook-status').className = 
                `status-badge ${data.webhookStatus}`;
            document.getElementById('last-sync').textContent = data.lastSync;
        } catch (error) {
            console.error('Error updating system status:', error);
        }
    };

    // Update system status elke 30 seconden
    setInterval(updateSystemStatus, 30000);
    updateSystemStatus();
});

// Utility functions
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
}
