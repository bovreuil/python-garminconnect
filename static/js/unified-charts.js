/**
 * Unified Chart Creation System
 * 
 * Page-aware chart functions that work with any data type based on page configuration.
 * This replaces the duplicated chart functions in each template.
 */

// Global chart variables
let fourteenWeekChart = null;
let twoWeekChart = null;
let activitiesChart = null;

// Current metric for the page
let currentMetric = null;

// Initialize page-specific charts
function initializePageCharts() {
    currentPageConfig = getCurrentPageConfig();
    
    // Set initial metric
    currentMetric = currentPageConfig.metrics.primary.key;
    
    console.log(`Initializing charts for ${currentPageConfig.name} page`);
    console.log(`Data type: ${currentPageConfig.dataType}, Zones: ${currentPageConfig.zones.length}`);
}

// Load 14 weeks of data (universal function)
function loadFourteenWeekData() {
    console.log('Loading 14-week data...');
    
    showLoading();
    
    // Calculate date range for 14 weeks (98 days)
    const endDate = new Date();
    endDate.setHours(0, 0, 0, 0);
    
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 97); // 98 days total (including today)
    
    // Generate date labels
    const dateLabels = [];
    const currentDate = new Date(startDate);
    while (currentDate <= endDate) {
        dateLabels.push(currentDate.toISOString().split('T')[0]);
        currentDate.setDate(currentDate.getDate() + 1);
    }
    
    console.log(`Loading data for ${dateLabels.length} days: ${dateLabels[0]} to ${dateLabels[dateLabels.length - 1]}`);
    
    // Fetch data using batch API
    fetch('/api/data/batch', {
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
            const dataResults = dateLabels.map(dateLabel => data.results[dateLabel] || null);
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
                        const weekStartDate = new Date(dateLabels[clickIndex * 7]);
                        const monday = getWeekStart(weekStartDate);
                        navigateToWeek(monday);
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
                        }
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
    
    console.log(`Updating 2-week chart with ${currentPageConfig.name} data`);
    
    // Prepare data for stacked column chart
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
            return currentPageConfig.dataExtractor.getZoneData(dayData, zone, currentMetric);
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
            plugins: {
                legend: {
                    display: currentPageConfig.zones.length <= 10 // Hide legend for pages with many zones
                },
                datalabels: {
                    display: false // No data labels on charts
                }
            },
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
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            return dateLabels[index];
                        },
                        afterBody: function(context) {
                            const dataIndex = context[0].dataIndex;
                            const dayData = dataResults[dataIndex];
                            const total = currentPageConfig.dataExtractor.getTotal(dayData, currentMetric);
                            return `Total: ${total.toFixed(1)}`;
                        }
                    }
                }
            }
        }
    });
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
    
    console.log(`Creating activities chart with ${currentPageConfig.name} data for ${activities.length} activities`);
    
    // Create datasets using page configuration
    const datasets = createZonedDatasets(currentPageConfig.zones, currentPageConfig.colors, zone => {
        return activities.map(activity => {
            return currentPageConfig.dataExtractor.getZoneData(activity, zone, currentMetric);
        });
    }, { borderColor: '#ffffff' });
    
    // Calculate x-axis maximum
    let maxValue = 0;
    activities.forEach(activity => {
        const activityTotal = currentPageConfig.dataExtractor.getTotal(activity, currentMetric);
        maxValue = Math.max(maxValue, activityTotal);
    });
    
    const { axisMax: xAxisMax } = calculateAxisScaling(maxValue, true, 100);
    
    activitiesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: activities.map(activity => activity.name || 'Activity'),
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Horizontal bars
            plugins: {
                legend: {
                    display: currentPageConfig.zones.length <= 10 // Hide legend for pages with many zones
                }
            },
            onClick: function(event, elements) {
                if (elements.length > 0) {
                    const activityIndex = elements[0].index;
                    const activity = activities[activityIndex];
                    if (activity && activity.activity_id) {
                        showSingleActivityView(activity.activity_id, selectedDate);
                    }
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
