document.addEventListener('DOMContentLoaded', function() {
    function showModal(title, content) {
        const existingModal = document.querySelector('.modal');
        if (existingModal) {
            existingModal.remove();
        }
    
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>${title}</h2>
                    <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
                </div>
                ${content}
            </div>
        `;
    
        document.body.appendChild(modal);
    }

    // Webhook management
    const webhookForm = document.getElementById('webhook-form');
    if (webhookForm) {
        webhookForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const webhookUrl = document.getElementById('webhook-url').value;
            try {
                const response = await fetch('/api/webhook', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ webhook: webhookUrl })
                });
                if (response.ok) {
                    showNotification('Webhook successfully updated', 'success');
                } else {
                    showNotification('Failed to update webhook', 'error');
                }
            } catch (error) {
                showNotification('Error updating webhook', 'error');
            }
        });
    }

    // Add repository form handler
    const addRepoForm = document.getElementById('add-repo-form');
    if (addRepoForm) {
        addRepoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/repositories', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to add repository');
                }
                
                showNotification('Repository successfully added', 'success');
                location.reload();
            } catch (error) {
                showNotification(error.message, 'error');
            }
        });
    }

    // Delete repository handler
    window.deleteRepository = async function(id) {
        if (!confirm('Are you sure you want to delete this repository?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/repositories?id=${id}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete repository');
            }
            
            showNotification('Repository successfully deleted', 'success');
            location.reload();
        } catch (error) {
            showNotification(error.message, 'error');
        }
    };

    // Show add repository modal
    window.showAddRepoForm = function() {
        showModal('Add Repository', `
            <form id="add-repo-form" class="repository-form">
                <div class="form-group">
                    <label><i class="fas fa-tag"></i> Repository Name</label>
                    <input type="text" name="name" placeholder="Repository Name" required>
                </div>
                <div class="form-group">
                    <label><i class="fas fa-link"></i> Repository URL</label>
                    <input type="text" name="url" placeholder="Repository URL" required>
                </div>
                <div class="form-group">
                    <label><i class="fas fa-folder"></i> Local Path</label>
                    <input type="text" name="local_path" placeholder="Local Path" required>
                </div>
                <button type="submit">
                    <i class="fas fa-plus"></i>
                    Add Repository
                </button>
            </form>
        `);
    };
});
