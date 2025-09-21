/**
 * Unified Chart Creation System
 *
 * Universal chart functions that work with any data type based on page configuration.
 * This replaces the duplicated chart functions in each template.
 */

// Global chart variables
let fourteenWeekChart = null;
let twoWeekChart = null;
let activitiesChart = null;

// Current metric for the page
let currentMetric = null;

// Initialize universal charts
function initializePageCharts() {
    currentPageConfig = getCurrentPageConfig();

    // Set initial metric
    currentMetric = currentPageConfig.metrics.primary.key;

    console.log(`Initializing charts for ${currentPageConfig.name} page`);
}

// Apply current page toggle state to currentPageConfig (works for all pages)
function applyCurrentToggleState() {
    // Reset to original configuration first
    const originalConfig = getCurrentPageConfig();
    currentPageConfig = { ...originalConfig };
    
    // Apply SpO2 filtering if on SpO2 page
    if (currentPageConfig.dataType === 'spo2_distribution' && typeof window.currentSpO2View !== 'undefined') {
        if (window.currentSpO2View === 'below95') {
            // Filter out zones 95, 96, 97, 98, 99
            const filteredZones = currentPageConfig.zones.filter(zone => parseInt(zone) < 95);
            const filteredColors = {};
            
            // Filter colors to match filtered zones
            filteredZones.forEach(zone => {
                filteredColors[zone] = originalConfig.colors[zone];
            });
            
            console.log(`SpO2 Filtering: ${originalConfig.zones.length} zones -> ${filteredZones.length} zones`);
            console.log('Filtered zones:', filteredZones);
            
            // Update the current page config
            currentPageConfig = {
                ...currentPageConfig,
                zones: filteredZones,
                colors: filteredColors
            };
        }
    }
    
    // For dashboard and oxygen debt pages, currentMetric is handled by the data extraction functions
    // No additional filtering needed here as the metric is passed to dataExtractor functions
}

// Load two weeks of data (universal function)
function loadTwoWeekData(startDate, endDate) {
    // Normalize dates to start of day to avoid time component issues
    currentStartDate = new Date(startDate.getFullYear(), startDate.getMonth(), startDate.getDate());
    currentEndDate = new Date(endDate.getFullYear(), endDate.getMonth(), endDate.getDate());
    
    showLoading();
    updateDateRange();
    console.log(`Loading two-week data for ${startDate} to ${endDate}`);

    // Generate array of 14 date labels
    const dateLabels = [];
    const currentDate = new Date(startDate);
    for (let i = 0; i < 14; i++) {
        const year = currentDate.getFullYear();
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const day = String(currentDate.getDate()).padStart(2, '0');
        dateLabels.push(`${year}-${month}-${day}`);
        currentDate.setDate(currentDate.getDate() + 1);
    }

    // Determine the correct batch endpoint based on page data type
    let batchEndpoint = '/api/data/batch'; // fallback
    if (currentPageConfig.dataType === 'trimp') {
        batchEndpoint = '/api/data/batch/trimp';
    } else if (currentPageConfig.dataType === 'oxygen_debt') {
        batchEndpoint = '/api/data/batch/oxygen-debt';
    } else if (currentPageConfig.dataType === 'spo2_distribution') {
        batchEndpoint = '/api/data/batch/spo2-distribution';
    }

    fetch(batchEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ dates: dateLabels })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Two-week batch data loaded successfully');
            const dataResults = dateLabels.map(dateLabel => data.data[dateLabel] || null);
            window.currentTwoWeekResults = dataResults; // Store 2-week data separately
            window.currentTwoWeekLabels = dateLabels; // Store 2-week labels separately
            updateTwoWeekChart(dateLabels, dataResults);
        } else {
            console.error('Failed to load two-week batch data:', data.error);
        }
        hideLoading();
    })
    .catch(error => {
        console.error('Error loading two-week data:', error);
        hideLoading();
    });
}

// Load 14 weeks of data (universal function)
function loadFourteenWeekData() {
    console.log('Loading 14-week data...');

    showLoading();

    // Use the proper 14-week calculation function
    const { startDate, endDate, dateLabels } = calculate14WeekPeriod();

    console.log(`Loading data for ${dateLabels.length} days: ${dateLabels[0]} to ${dateLabels[dateLabels.length - 1]}`);

    // Determine the correct batch endpoint based on page data type
    let batchEndpoint = '/api/data/batch'; // fallback
    if (currentPageConfig.dataType === 'trimp') {
        batchEndpoint = '/api/data/batch/trimp';
    } else if (currentPageConfig.dataType === 'oxygen_debt') {
        batchEndpoint = '/api/data/batch/oxygen-debt';
    } else if (currentPageConfig.dataType === 'spo2_distribution') {
        batchEndpoint = '/api/data/batch/spo2-distribution';
    }

    // Fetch data using batch API
    fetch(batchEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ dates: dateLabels })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('14-week batch data loaded successfully');
            const dataResults = dateLabels.map(dateLabel => data.data[dateLabel] || null);
            updateFourteenWeekChart(dateLabels, dataResults);
        } else {
            console.error('Failed to load 14-week batch data:', data.error);
        }
        hideLoading();
    })
    .catch(error => {
        console.error('Error loading 14-week data:', error);
        hideLoading();
    });
}

// Update 14-week chart (universal function)
function updateFourteenWeekChart(dateLabels, dataResults) {
    const ctx = document.getElementById('fourteenWeekChart').getContext('2d');

    if (fourteenWeekChart) {
        fourteenWeekChart.destroy();
    }

    // Apply current toggle state for all pages
    applyCurrentToggleState();

    console.log(`Updating 14-week chart with ${currentPageConfig.name} data`);

    // Group data by weeks using page-specific aggregation
    const { weeklyData, weekLabels } = groupDataByWeeks(dateLabels, dataResults, (weekData) => {
        return currentPageConfig.aggregateWeekData(weekData, currentMetric);
    });

    // Create datasets using page configuration
    const datasets = createZonedDatasets(currentPageConfig.zones, currentPageConfig.colors, zone =>
        weekLabels.map((_, index) => {
            const weekData = weeklyData[index];
            if (!weekData || !weekData[zone]) {
                return 0;
            }
            return weekData[zone];
        })
    , { borderColor: '#ffffff' });

    // Calculate Y-axis maximum
    let maxValue = 0;
    weeklyData.forEach(weekData => {
        if (weekData) {
            const weekTotal = currentPageConfig.zones.reduce((sum, zone) => sum + (weekData[zone] || 0), 0);
            maxValue = Math.max(maxValue, weekTotal);
        }
    });

    const { axisMax: yAxisMax } = calculateAxisScaling(maxValue, true);

    fourteenWeekChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: weekLabels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: function(event, elements) {
                // Handle week click navigation
                const canvas = event.native.target;
                const rect = canvas.getBoundingClientRect();
                const x = event.native.x - rect.left;
                const y = event.native.y - rect.top;

                const chartArea = fourteenWeekChart.chartArea;
                if (!chartArea) return;

                if (x >= chartArea.left && x <= chartArea.right &&
                    y >= chartArea.top && y <= chartArea.bottom) {

                    const xAxis = fourteenWeekChart.scales.x;
                    const clickIndex = xAxis.getValueForPixel(x);

                    if (clickIndex >= 0 && clickIndex < weekLabels.length) {
                        // Get the week start date (Monday) for this week
                        const weekStartDate = new Date(dateLabels[clickIndex * 7]);
                        navigateToWeek(weekStartDate);
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Week'
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: currentPageConfig.metrics.primary.label
                    },
                    beginAtZero: true,
                    max: yAxisMax
                }
            },
            plugins: {
                legend: {
                    display: currentPageConfig.zones.length <= 10, // Hide legend for pages with many zones
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            return weekLabels[context[0].dataIndex];
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            const zone = context.dataset.label;
                            
                            // For SpO2 distribution page, show minutes instead of percentages
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `SpO2 ${zone}%: ${value.toFixed(1)} minutes`;
                            } else {
                                return `${zone}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                },
                datalabels: {
                    display: function(context) {
                        // Only show total value on the top segment of each bar
                        const datasetIndex = context.datasetIndex;
                        const dataIndex = context.dataIndex;
                        const dataset = context.chart.data.datasets[datasetIndex];
                        
                        // Check if this is the last dataset (top segment)
                        const isLastDataset = datasetIndex === context.chart.data.datasets.length - 1;
                        
                        if (isLastDataset) {
                            // Calculate total for this bar
                            const weekData = weeklyData[dataIndex];
                            if (weekData) {
                                const total = currentPageConfig.zones.reduce((sum, zone) => sum + (weekData[zone] || 0), 0);
                                return total > 0; // Only show if there's data
                            }
                        }
                        return false;
                    },
                    anchor: 'end',
                    align: 'top',
                    color: '#2c3e50',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value, context) {
                        // Calculate total for this bar
                        const dataIndex = context.dataIndex;
                        const weekData = weeklyData[dataIndex];
                        if (weekData) {
                            const total = currentPageConfig.zones.reduce((sum, zone) => sum + (weekData[zone] || 0), 0);
                            
                            // For SpO2 distribution page, show total minutes
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `${total.toFixed(1)}m`;
                            } else {
                                return `${total.toFixed(1)}`;
                            }
                        }
                        return '';
                    }
                }
            }
        }
    });
}

// Update two-week chart (universal function)
function updateTwoWeekChart(dateLabels, dataResults) {
    const ctx = document.getElementById('twoWeekChart').getContext('2d');

    if (twoWeekChart) {
        twoWeekChart.destroy();
    }

    // Apply current toggle state for all pages
    applyCurrentToggleState();

    console.log(`Updating 2-week chart with ${currentPageConfig.name} data`);

    // Prepare data for stacked column char
    const labels = dateLabels.map(dateLabel => {
        const date = new Date(dateLabel + 'T00:00:00');
        const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
        const dayNum = date.getDate();
        return `${dayName} ${dayNum}`;
    });

    // Create datasets using page configuration

    const datasets = createZonedDatasets(currentPageConfig.zones, currentPageConfig.colors, zone => {
        return labels.map((_, index) => {
            const dayData = dataResults[index];
            const value = currentPageConfig.dataExtractor.getZoneData(dayData, zone, currentMetric);
            return value;
        });
    }, { borderColor: '#ffffff' });

    // Calculate maximum value for Y-axis scaling
    let maxValue = 0;
    dataResults.forEach(dayData => {
        if (dayData) {
            const dayTotal = currentPageConfig.dataExtractor.getTotal(dayData, currentMetric);
            maxValue = Math.max(maxValue, dayTotal);
        }
    });

    const { axisMax: yAxisMax } = calculateAxisScaling(maxValue, true);


    twoWeekChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            onClick: function(event, elements) {
                // Handle day click navigation
                const canvas = event.native.target;
                const rect = canvas.getBoundingClientRect();
                const x = event.native.x - rect.left;
                const y = event.native.y - rect.top;

                const chartArea = twoWeekChart.chartArea;
                if (!chartArea) return;

                if (x >= chartArea.left && x <= chartArea.right &&
                    y >= chartArea.top && y <= chartArea.bottom) {

                    const xAxis = twoWeekChart.scales.x;
                    const clickIndex = xAxis.getValueForPixel(x);

                    if (clickIndex >= 0 && clickIndex < dateLabels.length) {
                        const dateLabel = dateLabels[clickIndex];
                        loadDateData(dateLabel).then(dayData => {
                            if (dayData) {
                                showSingleDateView(dateLabel, dayData);
                            }
                        });
                    }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: 'Date'
                    }
                },
                y: {
                    stacked: true,
                    title: {
                        display: true,
                        text: currentPageConfig.metrics.primary.label
                    },
                    beginAtZero: true,
                    max: yAxisMax
                }
            },
            plugins: {
                legend: {
                    display: currentPageConfig.zones.length <= 10, // Hide legend for pages with many zones
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            return dateLabels[index];
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            const zone = context.dataset.label;
                            
                            // For SpO2 distribution page, show minutes instead of percentages
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `SpO2 ${zone}%: ${value.toFixed(1)} minutes`;
                            } else {
                                return `${zone}: ${value.toFixed(1)}%`;
                            }
                        },
                        afterBody: function(context) {
                            const dataIndex = context[0].dataIndex;
                            const dayData = dataResults[dataIndex];
                            const total = currentPageConfig.dataExtractor.getTotal(dayData, currentMetric);
                            
                            // For SpO2 distribution page, show total minutes instead of percentage
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `Total: ${total.toFixed(1)} minutes`;
                            } else {
                                return `Total: ${total.toFixed(1)}`;
                            }
                        }
                    }
                },
                datalabels: {
                    display: function(context) {
                        // Only show total value on the top segment of each bar
                        const datasetIndex = context.datasetIndex;
                        const dataIndex = context.dataIndex;
                        
                        // Check if this is the last dataset (top segment)
                        const isLastDataset = datasetIndex === context.chart.data.datasets.length - 1;
                        
                        if (isLastDataset) {
                            // Calculate total for this bar
                            const dayData = dataResults[dataIndex];
                            if (dayData) {
                                const total = currentPageConfig.dataExtractor.getTotal(dayData, currentMetric);
                                return total > 0; // Only show if there's data
                            }
                        }
                        return false;
                    },
                    anchor: 'end',
                    align: 'top',
                    color: '#2c3e50',
                    font: {
                        weight: 'bold',
                        size: 11
                    },
                    formatter: function(value, context) {
                        // Calculate total for this bar
                        const dataIndex = context.dataIndex;
                        const dayData = dataResults[dataIndex];
                        if (dayData) {
                            const total = currentPageConfig.dataExtractor.getTotal(dayData, currentMetric);
                            
                            // For SpO2 distribution page, show total minutes
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `${total.toFixed(1)}m`;
                            } else {
                                return `${total.toFixed(1)}`;
                            }
                        }
                        return '';
                    }
                }
            }
        }
    });
    
    // Set global reference for toggle functionality
    window.twoWeekChart = twoWeekChart;
}

// Create activities chart (universal function)
function createActivitiesChart(activities, selectedDate) {
    const ctx = document.getElementById('activitiesChart').getContext('2d');

    if (activitiesChart) {
        activitiesChart.destroy();
    }

    if (!activities || activities.length === 0) {
        console.log('No activities to display');
        return;
    }

    // Apply current toggle state for all pages
    applyCurrentToggleState();

    console.log(`Creating activities chart with ${currentPageConfig.name} data for ${activities.length} activities`);

    // Create datasets using page configuration
    const datasets = createZonedDatasets(currentPageConfig.zones, currentPageConfig.colors, zone => {
        return activities.map(activity => {
            // Use activity-specific data extraction if available, otherwise fall back to regular
            if (currentPageConfig.dataExtractor.getActivityZoneData) {
                return currentPageConfig.dataExtractor.getActivityZoneData(activity, zone, currentMetric);
            } else {
                return currentPageConfig.dataExtractor.getZoneData(activity, zone, currentMetric);
            }
        });
    }, { borderColor: '#ffffff' });

    // Calculate x-axis maximum
    let maxValue = 0;
    activities.forEach(activity => {
        // Use activity-specific total calculation if available, otherwise fall back to regular
        if (currentPageConfig.dataExtractor.getActivityTotal) {
            const activityTotal = currentPageConfig.dataExtractor.getActivityTotal(activity, currentMetric);
            maxValue = Math.max(maxValue, activityTotal);
        } else {
            const activityTotal = currentPageConfig.dataExtractor.getTotal(activity, currentMetric);
            maxValue = Math.max(maxValue, activityTotal);
        }
    });

    const { axisMax: xAxisMax } = calculateAxisScaling(maxValue, true, 100);

    activitiesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: activities.map(activity => activity.activity_name || activity.name || 'Activity'),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Horizontal bars
            plugins: {
                legend: {
                    display: currentPageConfig.zones.length <= 10, // Hide legend for pages with many zones
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            return context[0].label;
                        },
                        label: function(context) {
                            const value = context.parsed.x;
                            const zone = context.dataset.label;
                            
                            // For SpO2 distribution page, show minutes instead of percentages
                            if (currentPageConfig.dataType === 'spo2_distribution') {
                                return `SpO2 ${zone}%: ${value.toFixed(1)} minutes`;
                            } else {
                                return `${zone}: ${value.toFixed(1)}%`;
                            }
                        }
                    }
                },
            },
            onClick: function(event, elements) {
                const canvas = event.native.target;
                const rect = canvas.getBoundingClientRect();
                const x = event.native.x - rect.left;
                const y = event.native.y - rect.top;

                const chartArea = activitiesChart.chartArea;
                if (!chartArea) return;

                if (x >= chartArea.left && x <= chartArea.right &&
                    y >= chartArea.top && y <= chartArea.bottom) {

                    const yAxis = activitiesChart.scales.y;
                    const clickIndex = yAxis.getValueForPixel(y);

                    if (clickIndex >= 0 && clickIndex < activities.length) {
                        const activity = activities[clickIndex];
                        showSingleActivityView(activity);
                    }
                }
            },
            onHover: function(event, elements) {
                const canvas = event.native.target;
                const rect = canvas.getBoundingClientRect();
                const x = event.native.x - rect.left;
                const y = event.native.y - rect.top;

                const chartArea = activitiesChart.chartArea;
                if (!chartArea) {
                    event.native.target.style.cursor = 'default';
                    return;
                }

                if (x >= chartArea.left && x <= chartArea.right &&
                    y >= chartArea.top && y <= chartArea.bottom) {
                    canvas.style.cursor = 'pointer';
                } else {
                    canvas.style.cursor = 'default';
                }
            },
            scales: {
                x: {
                    stacked: true,
                    title: {
                        display: true,
                        text: currentPageConfig.metrics.primary.label
                    },
                    beginAtZero: true,
                    max: xAxisMax
                },
                y: {
                    stacked: true
                }
            }
        }
    });
}
