// app/dashboard/static/dashboard.js

// Webhook update functionaliteit
document.getElementById('webhook-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const webhook = document.getElementById('webhook-url').value;
        const response = await fetch('/api/webhook', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({webhook})
        });

        if (response.ok) {
            alert('Webhook succesvol bijgewerkt');
        } else {
            throw new Error('Webhook update mislukt');
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    }
});

// Repository verwijderen
async function deleteRepo(name) {
    if (confirm(`Weet je zeker dat je "${name}" wilt verwijderen?`)) {
        try {
            const response = await fetch('/api/repo', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name})
            });

            if (response.ok) {
                location.reload();
            } else {
                throw new Error('Verwijderen mislukt');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    }
}

// Repository toevoegen
function showAddRepoForm() {
    const form = createModalForm('Repository Toevoegen');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const formData = new FormData(form);
            const response = await fetch('/api/repo', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(Object.fromEntries(formData))
            });

            if (response.ok) {
                location.reload();
            } else {
                throw new Error('Toevoegen mislukt');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });
}

// Repository bewerken
function editRepo(name) {
    const row = document.querySelector(`tr:has(td:first-child:contains('${name}'))`);
    const [nameCell, urlCell, pathCell] = row.cells;

    const form = createModalForm('Repository Bewerken', {
        name: nameCell.textContent,
        url: urlCell.textContent,
        local_path: pathCell.textContent
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        try {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);
            data.old_name = name;

            const response = await fetch('/api/repo', {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });

            if (response.ok) {
                location.reload();
            } else {
                throw new Error('Bewerken mislukt');
            }
        } catch (error) {
            alert(`Error: ${error.message}`);
        }
    });
}

// Helper functie voor het maken van een modal form
function createModalForm(title, values = {}) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close">&times;</span>
            <h2>${title}</h2>
            <form>
                <input type="text" name="name" placeholder="Repository naam" value="${values.name || ''}" required>
                <input type="text" name="url" placeholder="GitHub URL" value="${values.url || ''}" required>
                <input type="text" name="local_path" placeholder="Lokale pad" value="${values.local_path || ''}" required>
                <button type="submit">Opslaan</button>
            </form>
        </div>
    `;

    document.body.appendChild(modal);
    modal.style.display = 'block';

    const form = modal.querySelector('form');
    const closeBtn = modal.querySelector('.close');

    closeBtn.onclick = () => {
        modal.remove();
    };

    window.onclick = (e) => {
        if (e.target == modal) {
            modal.remove();
        }
    };

    return form;
}
