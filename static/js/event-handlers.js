// Event Handler Setup
// Shared event handler initialization for dashboard and oxygen debt pages

function setupEventHandlers() {
    // Navigation event handlers
    document.getElementById('prevWeek').addEventListener('click', () => navigateWeek(-1));
    document.getElementById('nextWeek').addEventListener('click', () => navigateWeek(1));
    document.getElementById('todayBtn').addEventListener('click', goToToday);
    document.getElementById('prevDay').addEventListener('click', () => navigateSingleDay(-1));
    document.getElementById('singleDateTodayBtn').addEventListener('click', goToSingleDateToday);
    document.getElementById('nextDay').addEventListener('click', () => navigateSingleDay(1));
    
    // View control event handlers
    document.getElementById('closeSingleDate').addEventListener('click', closeSingleDateView);
    document.getElementById('closeSingleActivity').addEventListener('click', closeSingleActivityView);
    
    // Download event handlers
    document.getElementById('downloadActivityCsv').addEventListener('click', downloadActivityCsv);
    document.getElementById('downloadDailyCsv').addEventListener('click', downloadDailyCsv);
    
    // Modal event handlers
    document.getElementById('editSpo2').addEventListener('click', openSpo2Editor);
    document.getElementById('addSpo2Entry').addEventListener('click', addSpo2Entry);
    document.getElementById('saveSpo2').addEventListener('click', saveSpo2Data);
    document.getElementById('editTrimp').addEventListener('click', openTrimpEditor);
    document.getElementById('saveTrimpOverrides').addEventListener('click', saveTrimpOverrides);
    document.getElementById('clearTrimpOverrides').addEventListener('click', clearTrimpOverrides);
    
    // Manual activity event handlers
    document.getElementById('createManualActivityBtn').addEventListener('click', openManualActivityModal);
    document.getElementById('createManualActivity').addEventListener('click', createManualActivity);
    document.getElementById('uploadActivityCsv').addEventListener('click', openCsvUploadEditor);
    document.getElementById('uploadCsv').addEventListener('click', uploadCsvData);
    document.getElementById('deleteActivity').addEventListener('click', function() {
        if (selectedActivity) {
            deleteActivity(selectedActivity.activity_id);
        }
    });
    document.getElementById('clearCsvOverride').addEventListener('click', clearCsvOverride);
    
    // SpO2 chart type toggle event listeners
    document.getElementById('spo2AtOrBelowRadio').addEventListener('change', function() {
        if (this.checked) toggleSpo2ChartType('at_or_below', 'daily');
    });
    document.getElementById('spo2AtRadio').addEventListener('change', function() {
        if (this.checked) toggleSpo2ChartType('at', 'daily');
    });
    document.getElementById('activitySpo2AtOrBelowRadio').addEventListener('change', function() {
        if (this.checked) toggleSpo2ChartType('at_or_below', 'activity');
    });
    document.getElementById('activitySpo2AtRadio').addEventListener('change', function() {
        if (this.checked) toggleSpo2ChartType('at', 'activity');
    });
    
    // Window resize handler for chart responsiveness
    window.addEventListener('resize', function() {
        setTimeout(() => {
            if (twoWeekChart) twoWeekChart.resize();
            if (fourteenWeekChart) fourteenWeekChart.resize();
            if (hrChart) hrChart.resize();
            if (spo2Chart) spo2Chart.resize();
            if (activitiesChart) activitiesChart.resize();
            if (activityHrChart) activityHrChart.resize();
            if (activityBreathingChart) activityBreathingChart.resize();
            if (activitySpo2Chart) activitySpo2Chart.resize();
            if (spo2AtOrBelowChart) spo2AtOrBelowChart.resize();
            if (spo2AtChart) spo2AtChart.resize();
            if (activitySpo2AtOrBelowChart) activitySpo2AtOrBelowChart.resize();
            if (activitySpo2AtChart) activitySpo2AtChart.resize();
        }, 100);
    });
}
