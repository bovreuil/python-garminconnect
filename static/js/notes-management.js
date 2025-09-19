// Notes Management Functions
// Shared functions for managing daily notes and activity notes

// Daily Notes Functions
function loadDailyNotes(dateLabel) {
    fetch(`/api/data/${dateLabel}/notes`)
        .then(response => response.json())
        .then(data => {
            const notesElement = document.getElementById('dailyNotes');
            if (data.success && data.notes) {
                notesElement.innerHTML = `<p class="mb-0">${data.notes.replace(/\n/g, '<br>')}</p>`;
            } else {
                notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
            }
        })
        .catch(error => {
            console.error('Error loading daily notes:', error);
            const notesElement = document.getElementById('dailyNotes');
            notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
        });
}

function editDailyNotes(dateLabel) {
    const notesElement = document.getElementById('dailyNotes');
    const currentNotes = notesElement.textContent === 'Click to add notes...' ? '' : notesElement.textContent;
    
    notesElement.innerHTML = `
        <textarea class="form-control" rows="3" id="dailyNotesEditor">${currentNotes}</textarea>
        <div class="mt-2">
            <button class="btn btn-sm btn-primary" onclick="saveDailyNotes('${dateLabel}')">Save</button>
            <button class="btn btn-sm btn-secondary" onclick="cancelDailyNotes('${dateLabel}')">Cancel</button>
        </div>
    `;
    
    document.getElementById('dailyNotesEditor').focus();
}

function saveDailyNotes(dateLabel) {
    const notesElement = document.getElementById('dailyNotes');
    const editor = document.getElementById('dailyNotesEditor');
    const notes = editor.value.trim();
    
    fetch(`/api/data/${dateLabel}/notes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: notes })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (notes) {
                notesElement.innerHTML = `<p class="mb-0">${notes.replace(/\n/g, '<br>')}</p>`;
            } else {
                notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
            }
        } else {
            alert('Error saving notes: ' + data.error);
            loadDailyNotes(dateLabel);
        }
    })
    .catch(error => {
        console.error('Error saving daily notes:', error);
        alert('Error saving notes');
        loadDailyNotes(dateLabel);
    });
}

function cancelDailyNotes(dateLabel) {
    loadDailyNotes(dateLabel);
}

// Activity Notes Functions
function loadActivityNotes(activityId) {
    fetch(`/api/activity/${activityId}/notes`)
        .then(response => response.json())
        .then(data => {
            const notesElement = document.getElementById('activityNotes');
            if (data.success && data.notes) {
                notesElement.innerHTML = `<p class="mb-0">${data.notes.replace(/\n/g, '<br>')}</p>`;
            } else {
                notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
            }
        })
        .catch(error => {
            console.error('Error loading activity notes:', error);
            const notesElement = document.getElementById('activityNotes');
            notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
        });
}

function editActivityNotes(activityId) {
    const notesElement = document.getElementById('activityNotes');
    const currentNotes = notesElement.textContent === 'Click to add notes...' ? '' : notesElement.textContent;
    
    notesElement.innerHTML = `
        <textarea class="form-control" rows="3" id="activityNotesEditor">${currentNotes}</textarea>
        <div class="mt-2">
            <button class="btn btn-sm btn-primary" onclick="saveActivityNotes('${activityId}')">Save</button>
            <button class="btn btn-sm btn-secondary" onclick="cancelActivityNotes('${activityId}')">Cancel</button>
        </div>
    `;
    
    document.getElementById('activityNotesEditor').focus();
}

function saveActivityNotes(activityId) {
    const notesElement = document.getElementById('activityNotes');
    const editor = document.getElementById('activityNotesEditor');
    const notes = editor.value.trim();
    
    fetch(`/api/activity/${activityId}/notes`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: notes })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (notes) {
                notesElement.innerHTML = `<p class="mb-0">${notes.replace(/\n/g, '<br>')}</p>`;
            } else {
                notesElement.innerHTML = '<p class="mb-0 text-muted">Click to add notes...</p>';
            }
        } else {
            alert('Error saving activity notes: ' + data.error);
            loadActivityNotes(activityId);
        }
    })
    .catch(error => {
        console.error('Error saving activity notes:', error);
        alert('Error saving activity notes');
        loadActivityNotes(activityId);
    });
}

function cancelActivityNotes(activityId) {
    loadActivityNotes(activityId);
}
