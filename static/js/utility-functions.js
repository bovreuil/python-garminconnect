// Utility Functions
// Shared utility functions for downloads, SpO2 distribution, and other common operations

// Download Functions
function downloadActivityCsv() {
    if (!selectedActivity) {
        console.error('No activity selected for download');
        return;
    }
    
    const url = `/api/activity/${selectedActivity.activity_id}/csv`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `activity_${selectedActivity.activity_id}_hr.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function downloadDailyCsv() {
    if (!selectedDate) {
        console.error('No date selected for download');
        return;
    }
    
    const url = `/api/data/${selectedDate}/csv`;
    const link = document.createElement('a');
    link.href = url;
    link.download = `daily_${selectedDate}_hr.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// SpO2 Distribution Functions
/**
 * Unified SpO2 distribution loader for daily and activity views
 * Handles data fetching, chart creation, and notes loading
 * 
 * @param {string} identifier - Date label for daily view or activity ID for activity view
 * @param {string} viewType - 'daily' or 'activity'
 */
function loadSpO2Distribution(identifier, viewType) {
    // Determine API endpoint based on view type
    const apiEndpoint = viewType === 'daily' 
        ? `/api/data/${identifier}/spo2-distribution`
        : `/api/activity/${identifier}/spo2-distribution`;
    
    // Determine chart and container IDs based on view type
    const chartId = viewType === 'daily' 
        ? 'spo2AtOrBelowChart' 
        : 'activitySpo2AtOrBelowChart';
    const containerId = viewType === 'daily' 
        ? 'spo2DistributionChartsContainer' 
        : 'activitySpo2DistributionChartsContainer';
    
    fetch(apiEndpoint)
        .then(response => response.json())
        .then(data => {
            if (data.distribution) {
                // Create new SpO2 individual levels chart (with dummy data for now)
                const individualLevelsChartId = viewType === 'daily' 
                    ? 'spo2IndividualLevelsChart' 
                    : 'activitySpo2IndividualLevelsChart';
                const individualLevelsContainerId = viewType === 'daily' 
                    ? 'spo2IndividualLevelsContainer' 
                    : 'activitySpo2IndividualLevelsContainer';
                
                createSpo2IndividualLevelsChart(data.distribution, individualLevelsChartId, individualLevelsContainerId);
                
                // Create SpO2 distribution charts (identical logic for both view types)
                createSpo2DistributionCharts(data.distribution, chartId, containerId);
                
                // Load appropriate notes (different functions but same purpose)
                if (viewType === 'daily') {
                    loadDailyNotes(identifier);
                } else {
                    loadActivityNotes(identifier);
                }
            } else {
                // Hide charts if no data (different functions but same purpose)
                if (viewType === 'daily') {
                    hideSpo2DistributionCharts();
                } else {
                    hideActivitySpo2DistributionCharts();
                }
            }
        })
        .catch(error => {
            console.error(`Error loading ${viewType} SpO2 distribution:`, error);
            // Hide charts on error
            if (viewType === 'daily') {
                hideSpo2DistributionCharts();
            } else {
                hideActivitySpo2DistributionCharts();
            }
        });
}

// Legacy wrapper functions for backward compatibility
function loadDailySpo2Distribution(dateLabel) {
    loadSpO2Distribution(dateLabel, 'daily');
}

function loadActivitySpo2Distribution(activityId) {
    loadSpO2Distribution(activityId, 'activity');
}

function hideSpo2DistributionCharts() {
    const container = document.getElementById('spo2DistributionChartsContainer');
    if (container) {
        container.style.display = 'none';
    }
}

function hideActivitySpo2DistributionCharts() {
    const container = document.getElementById('activitySpo2DistributionChartsContainer');
    if (container) {
        container.style.display = 'none';
    }
}

function toggleSpo2ChartType(chartType, viewType) {
    if (viewType === 'daily') {
        const atOrBelowChart = document.getElementById('spo2AtOrBelowChart');
        const atChart = document.getElementById('spo2AtChart');
        const title = document.getElementById('spo2ChartTitle');
        
        if (chartType === 'at_or_below') {
            atOrBelowChart.style.display = 'block';
            atChart.style.display = 'none';
            title.textContent = 'SpO2 Time at or Below Level';
        } else {
            atOrBelowChart.style.display = 'none';
            atChart.style.display = 'block';
            title.textContent = 'SpO2 Time at Level';
        }
    } else {
        const atOrBelowChart = document.getElementById('activitySpo2AtOrBelowChart');
        const atChart = document.getElementById('activitySpo2AtChart');
        const title = document.getElementById('activitySpo2ChartTitle');
        
        if (chartType === 'at_or_below') {
            atOrBelowChart.style.display = 'block';
            atChart.style.display = 'none';
            title.textContent = 'SpO2 Time at or Below Level';
        } else {
            atOrBelowChart.style.display = 'none';
            atChart.style.display = 'block';
            title.textContent = 'SpO2 Time at Level';
        }
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

function updateOxygenDebtSummary(oxygenDebt) {
    // Update time under thresholds
    const time95Element = document.getElementById('timeUnder95');
    const time90Element = document.getElementById('timeUnder90');
    const time88Element = document.getElementById('timeUnder88');
    
    if (time95Element) time95Element.textContent = oxygenDebt.time_under_95 || 0;
    if (time90Element) time90Element.textContent = oxygenDebt.time_under_90 || 0;
    if (time88Element) time88Element.textContent = oxygenDebt.time_under_88 || 0;
    
    // Update area under thresholds
    const area95Element = document.getElementById('areaUnder95');
    const area90Element = document.getElementById('areaUnder90');
    const area88Element = document.getElementById('areaUnder88');
    
    if (area95Element) area95Element.textContent = oxygenDebt.area_under_95 || 0;
    if (area90Element) area90Element.textContent = oxygenDebt.area_under_90 || 0;
    if (area88Element) area88Element.textContent = oxygenDebt.area_under_88 || 0;
}
