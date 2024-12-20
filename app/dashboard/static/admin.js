document.addEventListener('DOMContentLoaded', function() {
    function showModal(title, content) {
        // Verwijder bestaande modals
        const existingModal = document.querySelector('.modal');
        if (existingModal) {
            existingModal.remove();
        }
    
        // Maak nieuwe modal
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

    // Repository management
    window.deleteRepo = async function(name) {
        if (confirm(`Are you sure you want to delete repository "${name}"?`)) {
            try {
                const response = await fetch('/api/repositories', {
                    method: 'DELETE',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name: name })
                });
                if (response.ok) {
                    showNotification('Repository deleted successfully', 'success');
                    location.reload();
                } else {
                    showNotification('Failed to delete repository', 'error');
                }
            } catch (error) {
                showNotification('Error deleting repository', 'error');
            }
        }
    };

    window.editRepo = function(name) {
        const row = document.querySelector(`tr[data-repo="${name}"]`);
        const url = row.querySelector('.repo-url').textContent;
        const path = row.querySelector('.repo-path').textContent;

        showModal('Edit Repository', `
            <form id="edit-repo-form" class="repository-form">
                <div class="form-group">
                    <label>Repository Name</label>
                    <input type="hidden" name="old_name" value="${name}">
                    <input type="text" name="name" value="${name}" placeholder="Repository Name" required>
                </div>
                <div class="form-group">
                    <label>Repository URL</label>
                    <input type="text" name="url" value="${url}" placeholder="Repository URL" required>
                </div>
                <div class="form-group">
                    <label>Local Path</label>
                    <input type="text" name="local_path" value="${path}" placeholder="Local Path" required>
                </div>
                <button type="submit">Update Repository</button>
            </form>
        `);

        document.getElementById('edit-repo-form').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/repositories', {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    showNotification('Repository updated successfully', 'success');
                    location.reload();
                } else {
                    showNotification('Failed to update repository', 'error');
                }
            } catch (error) {
                showNotification('Error updating repository', 'error');
            }
        };
    };

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
    
        document.getElementById('add-repo-form').onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/api/repositories', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    showNotification('Repository added successfully', 'success');
                    location.reload();
                } else {
                    const errorData = await response.json();
                    showNotification(errorData.error || 'Failed to add repository', 'error');
                }
            } catch (error) {
                showNotification('Error adding repository', 'error');
            }
        };
    };
});