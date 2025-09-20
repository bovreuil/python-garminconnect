/**
 * Data Loading Functions
 * 
 * Shared data loading and view management functions
 * used across dashboard pages.
 */

// Load data for a single date label (string)
function loadDateData(dateLabel) {
    console.log(`Loading data for ${dateLabel}`);
    
    return fetch(`/api/data/${dateLabel}`)
        .then(response => {
            if (!response.ok) {
                // Return null for dates with no data
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                
                // Load TRIMP overrides for this date
                return fetch(`/api/data/${dateLabel}/trimp-overrides`)
                    .then(response => response.json())
                    .then(overridesData => {
                        if (overridesData.success && overridesData.trimp_overrides && Object.keys(overridesData.trimp_overrides).length > 0) {
                            // Apply TRIMP overrides (even if all values are 0)
                            data.trimp_overrides = overridesData.trimp_overrides;
                            
                            // Update total TRIMP if we're on dashboard and viewing TRIMP metric
                            if (typeof currentMetric !== 'undefined' && currentMetric === 'trimp') {
                                let totalOverride = 0;
                                Object.values(overridesData.trimp_overrides).forEach(value => {
                                    totalOverride += value;
                                });
                                data.total_trimp = totalOverride;
                            }
                            
                            // For minutes view, set minutes to 0 when overrides exist
                            if (typeof currentMetric !== 'undefined' && currentMetric === 'minutes' && data.presentation_buckets) {
                                Object.keys(data.presentation_buckets).forEach(zone => {
                                    data.presentation_buckets[zone].minutes = 0;
                                });
                            }
                        }
                        return data;
                    })
                    .catch(error => {
                        console.error(`Error loading TRIMP overrides for ${dateLabel}:`, error);
                        return data;
                    });
            } else {
                // Check for TRIMP overrides even when there's no HR data
                return fetch(`/api/data/${dateLabel}/trimp-overrides`)
                    .then(response => response.json())
                    .then(overridesData => {
                        if (overridesData.success && overridesData.trimp_overrides && Object.keys(overridesData.trimp_overrides).length > 0) {
                            // Create minimal data structure with overrides
                            const overrideData = {
                                total_trimp: Object.values(overridesData.trimp_overrides).reduce((sum, value) => sum + value, 0),
                                trimp_overrides: overridesData.trimp_overrides,
                                presentation_buckets: {} // Empty buckets for zones
                            };
                            
                            // Create empty buckets for all zones
                            zoneOrder.forEach(zone => {
                                overrideData.presentation_buckets[zone] = {
                                    minutes: 0,
                                    trimp: 0
                                };
                            });
                            
                            return overrideData;
                        }
                        return null;
                    })
                    .catch(error => {
                        console.error(`Error loading TRIMP overrides for ${dateLabel}:`, error);
                        return null;
                    });
            }
        })
        .catch(error => {
            console.error(`Error loading data for ${dateLabel}:`, error);
            return null;
        });
}

// loadTwoWeekData function moved to unified-charts.js

// Load activities for a specific date label
function loadActivitiesForDate(dateLabel) {
    fetch(`/api/activities/${dateLabel}`)
        .then(response => {
            if (!response.ok) {
                console.log(`No activities found for ${dateLabel}`);
                return [];
            }
            return response.json();
        })
        .then(activities => {
            console.log(`Activities for ${dateLabel}:`, activities);
            createActivitiesChart(activities);
        })
        .catch(error => {
            console.error(`Error loading activities for ${dateLabel}:`, error);
            createActivitiesChart([]);
        });
}

// Show single date view
function showSingleDateView(dateLabel, dayData) {
    // Close single activity view when switching to a different date
    closeSingleActivityView();
    
    selectedDate = dateLabel; // Store the selected date label globally
    
    // Update the title with the formatted date
    const date = new Date(dateLabel);
    const formattedDate = date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    document.getElementById('singleDateTitle').textContent = formattedDate;
    
    // Show the section
    document.getElementById('singleDateSection').style.display = 'block';
    
    // Load activities for this date
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
    selectedDate = null;
    
    if (activitiesChart) {
        activitiesChart.destroy();
        activitiesChart = null;
    }
    
    // Destroy SpO2 distribution charts if they exist
    if (spo2AtOrBelowChart) {
        spo2AtOrBelowChart.destroy();
        spo2AtOrBelowChart = null;
    }
    if (spo2AtChart) {
        spo2AtChart.destroy();
        spo2AtChart = null;
    }
}

// Show single activity view
function showSingleActivityView(activity) {
    selectedActivity = activity; // Store the selected activity globally
    
    // Create a Date object for display formatting
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
    
    // Display activity summary
    let summaryHtml = '<div class="row">';
    
    if (activity.total_trimp !== undefined) {
        summaryHtml += `
            <div class="col-6">
                <div class="text-center p-3 bg-light rounded">
                    <h4 class="text-primary mb-1">${activity.total_trimp.toFixed(1)}</h4>
                    <small class="text-muted">Total TRIMP</small>
                </div>
            </div>
        `;
    }
    
    if (activity.presentation_buckets) {
        let totalMinutes = 0;
        Object.values(activity.presentation_buckets).forEach(bucket => {
            totalMinutes += bucket.minutes || 0;
        });
        
        summaryHtml += `
            <div class="col-6">
                <div class="text-center p-3 bg-light rounded">
                    <h4 class="text-success mb-1">${totalMinutes.toFixed(0)}</h4>
                    <small class="text-muted">Total Minutes</small>
                </div>
            </div>
        `;
    }
    
    summaryHtml += '</div>';
    document.getElementById('activitySummary').innerHTML = summaryHtml;
    
    // Display zone breakdown
    if (activity.presentation_buckets) {
        let zoneHtml = '<div class="table-responsive"><table class="table table-sm">';
        zoneHtml += '<thead><tr><th>Zone</th><th>Minutes</th><th>TRIMP</th><th>%</th></tr></thead><tbody>';
        
        const sortedZones = zoneOrder.filter(zone => activity.presentation_buckets[zone]).reverse();
        let totalMinutes = 0;
        let totalTrimp = 0;
        
        // Calculate totals first
        sortedZones.forEach(zone => {
            const bucket = activity.presentation_buckets[zone];
            totalMinutes += bucket.minutes || 0;
            totalTrimp += bucket.trimp || 0;
        });
        
        // Display each zone
        sortedZones.forEach(zone => {
            const bucket = activity.presentation_buckets[zone];
            const minutes = bucket.minutes || 0;
            const trimp = bucket.trimp || 0;
            const percentage = totalMinutes > 0 ? ((minutes / totalMinutes) * 100).toFixed(1) : '0.0';
            
            zoneHtml += `
                <tr>
                    <td>
                        <span class="badge" style="background-color: ${zoneColors[zone]}; color: white;">${zone}</span>
                    </td>
                    <td>${minutes.toFixed(0)}</td>
                    <td>${trimp.toFixed(1)}</td>
                    <td>${percentage}%</td>
                </tr>
            `;
        });
        
        zoneHtml += '</tbody></table></div>';
        document.getElementById('activityZoneBreakdown').innerHTML = zoneHtml;
    } else {
        document.getElementById('activityZoneBreakdown').innerHTML = '<p class="text-muted">No zone data available</p>';
    }
    
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
    selectedActivity = null;
    
    if (activityHrChart) {
        activityHrChart.destroy();
        activityHrChart = null;
    }
    if (activitySpo2Chart) {
        activitySpo2Chart.destroy();
        activitySpo2Chart = null;
    }
    if (activityBreathingChart) {
        activityBreathingChart.destroy();
        activityBreathingChart = null;
    }
    if (activitySpo2AtOrBelowChart) {
        activitySpo2AtOrBelowChart.destroy();
        activitySpo2AtOrBelowChart = null;
    }
    if (activitySpo2AtChart) {
        activitySpo2AtChart.destroy();
        activitySpo2AtChart = null;
    }
}
