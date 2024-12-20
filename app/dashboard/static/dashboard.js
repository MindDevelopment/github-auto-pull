// app/dashboard/static/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Repository updates
    const updateStatus = async () => {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            // Update last sync times voor elke repository
            const repoCards = document.querySelectorAll('.repo-card');
            repoCards.forEach(card => {
                const repoName = card.dataset.repo;
                const lastSyncTime = data.last_sync_times?.[repoName];
                if (lastSyncTime) {
                    // Convert ISO timestamp to readable format
                    const date = new Date(lastSyncTime);
                    const formattedDate = date.toLocaleString();
                    card.querySelector('.last-sync').textContent = formattedDate;
                }
            });

            // Update global last sync time
            if (data.last_sync_times) {
                const lastSyncTimes = Object.values(data.last_sync_times);
                if (lastSyncTimes.length > 0) {
                    const mostRecent = new Date(Math.max(...lastSyncTimes.map(t => new Date(t))));
                    document.getElementById('last-sync').textContent = mostRecent.toLocaleString();
                }
            }
        } catch (error) {
            console.error('Error updating status:', error);
        }
    };

    // Update elke minuut
    setInterval(updateStatus, 60000);
    updateStatus(); // Initial update
});

// Utility functions
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
}
