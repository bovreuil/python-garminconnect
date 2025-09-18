// Modal Management Functions
// Shared functions for managing SpO2 editor, TRIMP editor, manual activity, and CSV upload modals

// SpO2 Editor Functions
let spo2Entries = [];

function openSpo2Editor() {
    if (!selectedActivity) {
        console.error('No activity selected for SpO2 editing');
        return;
    }
    
    // Load existing SpO2 data if available
    spo2Entries = [];
    if (selectedActivity.spo2_values && selectedActivity.spo2_values.length > 0) {
        // Convert existing SpO2 data to entries format
        const firstHrTimestamp = selectedActivity.heart_rate_values[0][0];
        selectedActivity.spo2_values.forEach(spo2Point => {
            const timeOffsetMs = spo2Point[0] - firstHrTimestamp;
            const minutes = Math.floor(timeOffsetMs / 60000);
            const seconds = Math.floor((timeOffsetMs % 60000) / 1000);
            const timeOffset = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            spo2Entries.push({
                time_offset: timeOffset,
                spo2_value: spo2Point[1]
            });
        });
    }
    
    // Populate the modal
    populateSpo2Entries();
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('spo2Modal'));
    modal.show();
}

function addSpo2Entry() {
    let defaultTime = '0:00';
    
    // If there are existing entries, calculate the next time (15 seconds after the last entry)
    if (spo2Entries.length > 0) {
        const lastEntry = spo2Entries[spo2Entries.length - 1];
        if (lastEntry.time_offset && lastEntry.time_offset.match(/^\d+:\d{2}$/)) {
            const [minutes, seconds] = lastEntry.time_offset.split(':').map(Number);
            let totalSeconds = minutes * 60 + seconds + 15; // Add 15 seconds
            const newMinutes = Math.floor(totalSeconds / 60);
            const newSeconds = totalSeconds % 60;
            defaultTime = `${newMinutes}:${newSeconds.toString().padStart(2, '0')}`;
        }
    }
    
    spo2Entries.push({
        time_offset: defaultTime,
        spo2_value: ''
    });
    populateSpo2Entries();
}

function removeSpo2Entry(index) {
    spo2Entries.splice(index, 1);
    populateSpo2Entries();
}

function populateSpo2Entries() {
    const container = document.getElementById('spo2Entries');
    container.innerHTML = '';
    
    spo2Entries.forEach((entry, index) => {
        const entryDiv = document.createElement('div');
        entryDiv.className = 'row mb-2 align-items-center';
        entryDiv.innerHTML = `
            <div class="col-5">
                <input type="text" class="form-control" placeholder="MM:SS" 
                       value="${entry.time_offset}" 
                       onchange="updateSpo2Entry(${index}, 'time_offset', this.value)">
            </div>
            <div class="col-5">
                <input type="number" class="form-control" placeholder="SpO2 %" min="0" max="100"
                       value="${entry.spo2_value}" 
                       onchange="updateSpo2Entry(${index}, 'spo2_value', parseInt(this.value))">
            </div>
            <div class="col-2">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSpo2Entry(${index})">
                    <span>×</span>
                </button>
            </div>
        `;
        container.appendChild(entryDiv);
    });
}

function updateSpo2Entry(index, field, value) {
    if (index >= 0 && index < spo2Entries.length) {
        spo2Entries[index][field] = value;
    }
}

function saveSpo2Data() {
    if (!selectedActivity) {
        console.error('No activity selected for saving SpO2 data');
        return;
    }
    
    // Validate entries
    const validEntries = spo2Entries.filter(entry => 
        entry.time_offset && entry.time_offset.match(/^\d+:\d{2}$/) && 
        entry.spo2_value !== '' && entry.spo2_value >= 0 && entry.spo2_value <= 100
    );
    
    // Allow empty entries - this will clear the SpO2 data
    
    // Send data to server
    fetch(`/api/activity/${selectedActivity.activity_id}/spo2`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            spo2_entries: validEntries
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the selected activity with new SpO2 data (null if empty)
            selectedActivity.spo2_values = data.spo2_series || [];
            
            // Refresh the activity chart to show SpO2 data
            createActivityHeartRateChart(selectedActivity);
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('spo2Modal'));
            modal.hide();
        } else {
            alert('Error saving SpO2 data: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving SpO2 data:', error);
        alert('Error saving SpO2 data');
    });
}

// TRIMP Editor Functions
let currentTrimpOverrides = {};
let currentDayData = null;

function openTrimpEditor() {
    if (!selectedDate) {
        console.error('No date selected for TRIMP editing');
        return;
    }
    
    // Load current day data and TRIMP overrides
    loadTrimpOverrides(selectedDate);
}

function loadTrimpOverrides(dateLabel) {
    // First, get the current day data to show calculated TRIMP values
    fetch(`/api/data/${dateLabel}`)
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            return null;
        })
        .then(dayData => {
            currentDayData = dayData;
            
            // Then load existing TRIMP overrides
            return fetch(`/api/data/${dateLabel}/trimp-overrides`);
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentTrimpOverrides = data.trimp_overrides || {};
            } else {
                currentTrimpOverrides = {};
            }
            
            // Populate the modal
            populateTrimpOverridesForm();
            
            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('trimpModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error loading TRIMP overrides:', error);
            currentDayData = null;
            currentTrimpOverrides = {};
            populateTrimpOverridesForm();
            
            const modal = new bootstrap.Modal(document.getElementById('trimpModal'));
            modal.show();
        });
}

function populateTrimpOverridesForm() {
    const container = document.getElementById('trimpOverridesForm');
    container.innerHTML = '';
    
    // Create form fields for each zone
    zoneOrder.forEach(zone => {
        const zoneDiv = document.createElement('div');
        zoneDiv.className = 'row mb-2 align-items-center';
        
        // Get calculated value for this zone
        let calculatedValue = 0;
        if (currentDayData && currentDayData.presentation_buckets && currentDayData.presentation_buckets[zone]) {
            calculatedValue = currentDayData.presentation_buckets[zone].trimp || 0;
        }
        
        // Get override value if it exists
        const overrideValue = currentTrimpOverrides[zone] !== undefined ? currentTrimpOverrides[zone] : '';
        
        zoneDiv.innerHTML = `
            <div class="col-3">
                <label class="form-label">${zone}</label>
            </div>
            <div class="col-3">
                <span class="text-muted">${calculatedValue.toFixed(1)}</span>
            </div>
            <div class="col-4">
                <input type="number" class="form-control" placeholder="Override" 
                       value="${overrideValue}" step="0.1" min="0"
                       onchange="updateTrimpOverride('${zone}', parseFloat(this.value) || null)">
            </div>
            <div class="col-2">
                <span style="color: ${zoneColors[zone]};">●</span>
            </div>
        `;
        container.appendChild(zoneDiv);
    });
    
    // Update total
    updateTotalTrimpOverride();
}

function updateTrimpOverride(zone, value) {
    if (value === '' || value === null || value === undefined) {
        delete currentTrimpOverrides[zone];
    } else {
        currentTrimpOverrides[zone] = value;
    }
    updateTotalTrimpOverride();
}

function updateTotalTrimpOverride() {
    const total = Object.values(currentTrimpOverrides).reduce((sum, value) => sum + value, 0);
    document.getElementById('totalTrimpOverride').textContent = total.toFixed(1);
}

function clearTrimpOverrides() {
    if (!selectedDate) {
        console.error('No date selected for clearing TRIMP overrides');
        return;
    }
    
    fetch(`/api/data/${selectedDate}/trimp-overrides`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentTrimpOverrides = {};
            
            // Refresh the form
            populateTrimpOverridesForm();
            
            // Update the icon
            updateTrimpIcon(false);
            
            // Refresh charts if we're on the single date view
            if (selectedDate) {
                loadDateData(selectedDate);
            }
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('trimpModal'));
            modal.hide();
        } else {
            alert('Error clearing TRIMP overrides: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error clearing TRIMP overrides:', error);
        alert('Error clearing TRIMP overrides');
    });
}

function saveTrimpOverrides() {
    if (!selectedDate) {
        console.error('No date selected for saving TRIMP overrides');
        return;
    }
    
    fetch(`/api/data/${selectedDate}/trimp-overrides`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            trimp_overrides: currentTrimpOverrides
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the icon
            updateTrimpIcon(Object.keys(currentTrimpOverrides).length > 0);
            
            // Refresh charts if we're on the single date view
            if (selectedDate) {
                loadDateData(selectedDate);
            }
            
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('trimpModal'));
            modal.hide();
        } else {
            alert('Error saving TRIMP overrides: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error saving TRIMP overrides:', error);
        alert('Error saving TRIMP overrides');
    });
}

function updateTrimpIcon(hasOverrides) {
    const icon = document.getElementById('trimpIcon');
    icon.textContent = hasOverrides ? '📊✓' : '📊';
}

function createTrimpIcon() {
    // Create an SVG icon with 9 colored bars representing the zones (vertical stacking)
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', '16');
    svg.setAttribute('height', '16');
    svg.setAttribute('viewBox', '0 0 16 16');
    
    // Create bars for each zone (stacked vertically)
    zoneOrder.forEach((zone, index) => {
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', '2');
        rect.setAttribute('y', 14 - (index + 1) * 1.5);
        rect.setAttribute('width', '12');
        rect.setAttribute('height', '1.5');
        rect.setAttribute('fill', zoneColors[zone]);
        svg.appendChild(rect);
    });
    
    return svg;
}

function checkTrimpOverrides(dateLabel) {
    fetch(`/api/data/${dateLabel}/trimp-overrides`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.trimp_overrides) {
                updateTrimpIcon(Object.keys(data.trimp_overrides).length > 0);
            } else {
                updateTrimpIcon(false);
            }
        })
        .catch(error => {
            console.error('Error checking TRIMP overrides:', error);
            updateTrimpIcon(false);
        });
}

// Manual Activity Functions
function openManualActivityModal() {
    if (!selectedDate) {
        alert('No date selected');
        return;
    }
    
    // Clear form fields
    document.getElementById('manualStartTime').value = '';
    document.getElementById('manualEndTime').value = '';
    document.getElementById('manualHeartRate').value = '';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('manualActivityModal'));
    modal.show();
}

function createManualActivity() {
    if (!selectedDate) {
        alert('No date selected');
        return;
    }
    
    const startTime = document.getElementById('manualStartTime').value;
    const endTime = document.getElementById('manualEndTime').value;
    const heartRate = document.getElementById('manualHeartRate').value;
    
    if (!startTime || !endTime || !heartRate) {
        alert('Please fill in all fields');
        return;
    }
    
    // Validate time format (HH:MM)
    const timePattern = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timePattern.test(startTime) || !timePattern.test(endTime)) {
        alert('Please enter times in HH:MM format (e.g., 14:30)');
        return;
    }
    
    // Validate heart rate
    const hr = parseInt(heartRate);
    if (isNaN(hr) || hr < 30 || hr > 220) {
        alert('Please enter a valid heart rate between 30 and 220');
        return;
    }
    
    // Create the manual activity
    fetch('/api/create-manual-activity', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            date: selectedDate,
            start_time: startTime,
            end_time: endTime,
            heart_rate: hr
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close the modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualActivityModal'));
            modal.hide();
            
            // Refresh the single date view to show the new activity
            loadDateData(selectedDate);
        } else {
            alert('Error creating manual activity: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error creating manual activity:', error);
        alert('Error creating manual activity');
    });
}

function deleteActivity(activityId) {
    if (!confirm('Are you sure you want to delete this activity?')) {
        return;
    }
    
    fetch(`/api/activity/${activityId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Close the single activity view
            closeSingleActivityView();
            
            // Refresh the single date view to remove the deleted activity
            if (selectedDate) {
                loadDateData(selectedDate);
            }
        } else {
            alert('Error deleting activity: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting activity:', error);
        alert('Error deleting activity');
    });
}

// CSV Upload Functions
function openCsvUploadEditor() {
    if (!selectedActivity) {
        console.error('No activity selected for CSV upload');
        return;
    }
    
    // Clear the file input and status
    document.getElementById('csvFile').value = '';
    document.getElementById('csvStatus').innerHTML = '';
    
    // Check current CSV override status
    checkCsvOverrideStatus();
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('csvUploadModal'));
    modal.show();
}

function checkCsvOverrideStatus() {
    if (!selectedActivity) return;
    
    fetch(`/api/activity/${selectedActivity.activity_id}/csv-status`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateCsvIcon(data.has_override);
                updateCsvStatus(data.has_override);
            }
        })
        .catch(error => {
            console.error('Error checking CSV override status:', error);
        });
}

function updateCsvIcon(hasOverride) {
    const icon = document.getElementById('csvIcon');
    if (hasOverride) {
        icon.textContent = '📤✅ CSV';
        icon.parentElement.title = 'HR data has been overridden with CSV';
    } else {
        icon.textContent = '📤 CSV';
        icon.parentElement.title = 'Upload CSV to override HR data';
    }
}

function updateCsvStatus(hasOverride) {
    const statusDiv = document.getElementById('csvStatus');
    if (hasOverride) {
        statusDiv.innerHTML = '<div class="alert alert-success">This activity has HR data overridden with CSV.</div>';
    } else {
        statusDiv.innerHTML = '';
    }
}

function uploadCsvData() {
    if (!selectedActivity) {
        console.error('No activity selected for CSV upload');
        return;
    }
    
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a CSV file to upload');
        return;
    }
    
    if (!file.name.toLowerCase().endsWith('.csv')) {
        alert('Please select a CSV file');
        return;
    }
    
    const formData = new FormData();
    formData.append('csv_file', file);
    
    // Show uploading status
    const statusDiv = document.getElementById('csvStatus');
    statusDiv.innerHTML = '<div class="alert alert-info">Uploading and processing CSV...</div>';
    
    fetch(`/api/activity/${selectedActivity.activity_id}/upload-csv`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the selected activity with new HR data
            selectedActivity.heart_rate_values = data.heart_rate_series;
            selectedActivity.has_hr_override = true;
            
            // Update CSV icon
            updateCsvIcon(true);
            
            // Refresh the activity chart
            createActivityHeartRateChart(selectedActivity);
            
            // Show success status
            statusDiv.innerHTML = '<div class="alert alert-success">CSV uploaded successfully! HR data has been updated.</div>';
            
            // Close the modal after a short delay
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('csvUploadModal'));
                modal.hide();
            }, 2000);
            
            // Refresh the 14-week chart
            if (typeof loadFourteenWeekData === 'function') {
                loadFourteenWeekData();
            }
            
            // Refresh the two-week chart
            if (selectedDate) {
                loadDateData(selectedDate);
            }
        } else {
            statusDiv.innerHTML = `<div class="alert alert-danger">Error uploading CSV: ${data.error}</div>`;
        }
    })
    .catch(error => {
        console.error('Error uploading CSV:', error);
        statusDiv.innerHTML = '<div class="alert alert-danger">Error uploading CSV file</div>';
    });
}

function clearCsvOverride() {
    if (!selectedActivity) {
        console.error('No activity selected for clearing CSV override');
        return;
    }
    
    if (!confirm('Are you sure you want to clear the CSV override and restore original HR data?')) {
        return;
    }
    
    fetch(`/api/activity/${selectedActivity.activity_id}/clear-csv-override`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update the selected activity with original HR data
            selectedActivity.heart_rate_values = data.heart_rate_series;
            selectedActivity.has_hr_override = false;
            
            // Update CSV icon
            updateCsvIcon(false);
            
            // Refresh the activity chart
            createActivityHeartRateChart(selectedActivity);
            
            // Show success status
            const statusDiv = document.getElementById('csvStatus');
            statusDiv.innerHTML = '<div class="alert alert-success">CSV override cleared! Original HR data restored.</div>';
            
            // Close the modal after a short delay
            setTimeout(() => {
                const modal = bootstrap.Modal.getInstance(document.getElementById('csvUploadModal'));
                modal.hide();
            }, 2000);
            
            // Refresh the 14-week chart
            if (typeof loadFourteenWeekData === 'function') {
                loadFourteenWeekData();
            }
            
            // Refresh the two-week chart
            if (selectedDate) {
                loadDateData(selectedDate);
            }
        } else {
            const statusDiv = document.getElementById('csvStatus');
            statusDiv.innerHTML = `<div class="alert alert-danger">Error clearing CSV override: ${data.error}</div>`;
        }
    })
    .catch(error => {
        console.error('Error clearing CSV override:', error);
        const statusDiv = document.getElementById('csvStatus');
        statusDiv.innerHTML = '<div class="alert alert-danger">Error clearing CSV override</div>';
    });
}
