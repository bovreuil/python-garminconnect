// View Management Functions
// Shared functions for managing single date view, single activity view, and related UI

// Show/hide loading indicator
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// Show single date view
function showSingleDateView(dateLabel, dayData) {
    // Close single activity view when switching to a different date
    closeSingleActivityView();
    
    selectedDate = dateLabel; // Store the selected date label globally
    

    
    // Create a Date object just for display formatting
    const date = new Date(dateLabel + 'T00:00:00');
    const dateDisplayStr = date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    // Update the single date title with the formatted date
    document.getElementById('singleDateTitle').textContent = dateDisplayStr;
    
    if (!dayData) {
        // Clear heart rate chart
        if (hrChart) {
            hrChart.destroy();
            hrChart = null;
        }
        if (spo2Chart) {
            spo2Chart.destroy();
            spo2Chart = null;
        }
    } else {
        // Create 24-hour heart rate chart
        createHeartRateChart(dateLabel, dayData);
        
        // Load notes for this date
        loadDailyNotes(dateLabel);
        
        // Check for TRIMP overrides and update icon
        checkTrimpOverrides(dateLabel);
    }
    
    // Show the section
    document.getElementById('singleDateSection').style.display = 'block';
    
    // Load and display activities for this date
    loadActivitiesForDate(dateLabel);
    
    // Scroll to the section
    document.getElementById('singleDateSection').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

// Close single date view
function closeSingleDateView() {
    document.getElementById('singleDateSection').style.display = 'none';
    selectedDate = null; // Clear the selected date
    
    // Destroy activities chart if it exists
    if (activitiesChart) {
        activitiesChart.destroy();
        activitiesChart = null;
    }
    
    // Destroy heart rate chart if it exists
    if (hrChart) {
        hrChart.destroy();
        hrChart = null;
    }
    
    // Destroy spo2 chart if it exists
    if (spo2Chart) {
        spo2Chart.destroy();
        spo2Chart = null;
    }
    
    // Hide SpO2 distribution charts
    hideSpO2DistributionCharts('daily');
    
    // Close single activity view as well
    closeSingleActivityView();
}

// Show single activity view
function showSingleActivityView(activity) {
    selectedActivity = activity; // Store the selected activity globally
    
    // Create a Date object for display formatting using selectedDate
    const activityDate = new Date(selectedDate + 'T00:00:00');
    const activityDateStr = activityDate.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    
    // Update the single activity title with date and activity name
    document.getElementById('singleActivityTitle').textContent = `${activityDateStr} - ${activity.activity_name}`;
    document.getElementById('activityTitle').textContent = 'Activity Heart Rate';
    
    // Show the section
    document.getElementById('singleActivitySection').style.display = 'block';
    
    // Show/hide delete button for manual activities
    const deleteBtn = document.getElementById('deleteActivity');
    if (activity.activity_type === 'manual') {
        deleteBtn.style.display = 'inline-block';
    } else {
        deleteBtn.style.display = 'none';
    }
    
    // Small delay to ensure DOM is fully updated before creating chart
    setTimeout(() => {
        // Create the activity heart rate chart
        createActivityHeartRateChart(activity);
    }, 50);
    
    // Load notes for this activity
    loadActivityNotes(activity.activity_id);
    
    // Scroll to the section
    document.getElementById('singleActivitySection').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
}

// Close single activity view
function closeSingleActivityView() {
    document.getElementById('singleActivitySection').style.display = 'none';
    selectedActivity = null; // Clear the selected activity
    
    // Destroy activity heart rate chart if it exists
    if (activityHrChart) {
        activityHrChart.destroy();
        activityHrChart = null;
    }
    
    // Destroy activity breathing chart if it exists
    if (activityBreathingChart) {
        activityBreathingChart.destroy();
        activityBreathingChart = null;
    }
    
    // Destroy activity spo2 chart if it exists
    if (activitySpo2Chart) {
        activitySpo2Chart.destroy();
        activitySpo2Chart = null;
    }
    
    // Hide activity SpO2 distribution charts
    hideSpO2DistributionCharts('activity');
}

// Hide SpO2 distribution charts
function hideSpO2DistributionCharts(viewType) {
    const prefix = viewType === 'daily' ? '' : 'activity';
    const containerElement = document.getElementById(`${prefix}Spo2DistributionChartsContainer`);
    if (containerElement) {
        containerElement.style.display = 'none';
    }
}

// Update oxygen debt display
function updateOxygenDebtDisplay(oxygenDebt, viewType) {
    if (!oxygenDebt) return;
    
    const prefix = viewType === 'daily' ? 'daily' : 'activity';
    
    // Update time displays
    const time95Element = document.getElementById(`${prefix}TimeUnder95`);
    const time90Element = document.getElementById(`${prefix}TimeUnder90`);
    const time88Element = document.getElementById(`${prefix}TimeUnder88`);
    
    if (time95Element) time95Element.textContent = formatTime(oxygenDebt.time_under_95 || 0);
    if (time90Element) time90Element.textContent = formatTime(oxygenDebt.time_under_90 || 0);
    if (time88Element) time88Element.textContent = formatTime(oxygenDebt.time_under_88 || 0);
    
    // Update area displays
    const area95Element = document.getElementById(`${prefix}AreaUnder95`);
    const area90Element = document.getElementById(`${prefix}AreaUnder90`);
    const area88Element = document.getElementById(`${prefix}AreaUnder88`);
    
    if (area95Element) area95Element.textContent = oxygenDebt.area_under_95 || 0;
    if (area90Element) area90Element.textContent = oxygenDebt.area_under_90 || 0;
    if (area88Element) area88Element.textContent = oxygenDebt.area_under_88 || 0;
}
