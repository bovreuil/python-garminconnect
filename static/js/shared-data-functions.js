/**
 * Shared Data Functions
 *
 * Data loading and processing functions that are identical across
 * dashboard and oxygen debt pages.
 */

// Load data for a single date label (string) - IDENTICAL in both pages
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

                            // For minutes view, set minutes to 0 when overrides exis
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

// Load activities for a specific date label - IDENTICAL in both pages
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
            // Debug: Check if activities have raw_hr_data (dashboard comment)
            if (activities && activities.length > 0) {
                activities.forEach((activity, index) => {
                    console.log(`Activity ${index} (${activity.activity_name}):`, {
                        has_heart_rate_values: !!activity.heart_rate_values,
                        heart_rate_values_type: typeof activity.heart_rate_values,
                        heart_rate_values_length: activity.heart_rate_values ? activity.heart_rate_values.length : 'N/A',
                        heart_rate_values_sample: activity.heart_rate_values ? activity.heart_rate_values.slice(0, 3) : 'N/A'
                    });
                });
            }
            createActivitiesChart(activities, dateLabel);
        })
        .catch(error => {
            console.error(`Error loading activities for ${dateLabel}:`, error);
            createActivitiesChart([], dateLabel);
        });
}

// Download activity HR data as CSV - IDENTICAL in both pages
function downloadActivityCsv() {
    if (!selectedActivity) {
        console.error('No activity selected for download');
        return;
    }

    const activityId = selectedActivity.activity_id;
    const downloadUrl = `/api/activity/${activityId}/hr-csv`;

    // Create a temporary link element to trigger the download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `activity_${activityId}_hr_data.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Download daily HR data as CSV - IDENTICAL in both pages
function downloadDailyCsv() {
    if (!selectedDate) {
        console.error('No date selected for download');
        return;
    }

    const downloadUrl = `/api/data/${selectedDate}/hr-csv`;

    // Create a temporary link element to trigger the download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `daily_${selectedDate}_hr_data.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}
