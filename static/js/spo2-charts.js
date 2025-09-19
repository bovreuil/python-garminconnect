/**
 * SpO2 Chart Functions
 * 
 * Chart creation functions for SpO2 time series and distribution data.
 * Handles daily and activity-level SpO2 data visualization.
 */

// Create SpO2 distribution charts (horizontal bar charts)
function createSpo2DistributionCharts(distribution, atOrBelowChartId, containerId) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error('SpO2 distribution container not found');
        return;
    }
    
    // Show container
    container.style.display = 'block';
    
    // Store the distribution data for toggling
    if (containerId === 'spo2DistributionChartsContainer') {
        window.dailySpo2Distribution = distribution;
    } else if (containerId === 'activitySpo2DistributionChartsContainer') {
        window.activitySpo2Distribution = distribution;
    }
    
    // Create "At or Below Level" chart by default
    createSpo2HorizontalBarChart(atOrBelowChartId, distribution.at_or_below_level, 'Time at or Below Level');
    
    // Update oxygen debt display if available
    if (distribution.oxygen_debt) {
        const viewType = containerId === 'spo2DistributionChartsContainer' ? 'daily' : 'activity';
        updateOxygenDebtDisplay(distribution.oxygen_debt, viewType);
    }
}

function createSpo2HorizontalBarChart(chartId, data, title) {
    const ctx = document.getElementById(chartId);
    if (!ctx) {
        console.error(`Chart element ${chartId} not found`);
        return;
    }
    
    // Destroy existing chart if it exists
    let existingChart = null;
    if (chartId === 'spo2AtOrBelowChart') existingChart = spo2AtOrBelowChart;
    else if (chartId === 'spo2AtChart') existingChart = spo2AtChart;
    else if (chartId === 'activitySpo2AtOrBelowChart') existingChart = activitySpo2AtOrBelowChart;
    else if (chartId === 'activitySpo2AtChart') existingChart = activitySpo2AtChart;
    
    if (existingChart) {
        existingChart.destroy();
    }
    
    // SpO2 color mapping (81-98) - exact specification
    const spo2Colors = {
        98: '#28a745', 97: '#28a745', 96: '#28a745', 95: '#28a745', // Green
        94: '#9acd32', 93: '#9acd32', 92: '#ffc107', 91: '#ffc107', // Yellow-Green, Yellow
        90: '#fd7e14', 89: '#fd7e14', 88: '#e74c3c', 87: '#e74c3c', // Orange, Red
        86: '#dc3545', 85: '#dc3545', 84: '#dc3545', 83: '#dc3545', 82: '#dc3545', 81: '#dc3545' // Hot Red
    };
    
    // Convert seconds to hh:mm:ss format
    function formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    
    const chartData = {
        labels: data.map(item => item.spo2), // Remove % from labels
        datasets: [{
            label: title,
            data: data.map(item => item.seconds),
            backgroundColor: data.map(item => spo2Colors[item.spo2] || '#6c757d'),
            borderColor: data.map(item => spo2Colors[item.spo2] || '#6c757d'),
            borderWidth: 1,
            borderRadius: 2
        }]
    };
    
    const newChart = new Chart(ctx, {
        type: 'bar',
        data: chartData,
        options: {
            indexAxis: 'y', // Horizontal bar chart
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    right: 20 // Add some padding for the percentage labels
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const item = data[context.dataIndex];
                            return [
                                `Time: ${formatTime(item.seconds)}`,
                                `Percentage: ${Math.round(item.percent)}%`
                            ];
                        }
                    }
                },
                datalabels: {
                    display: true,
                    anchor: 'end',
                    align: 'right',
                    offset: 10,
                    color: '#333',
                    font: {
                        size: 11
                    },
                    formatter: function(value, context) {
                        const item = data[context.dataIndex];
                        return `${Math.round(item.percent)}%`;
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Seconds'
                    }
                },
                y: {
                    reverse: false, // 98 at top, 81 at bottom (data comes in descending order, so reverse=false puts 98 at top)
                    title: {
                        display: true,
                        text: 'SpO2 Level'
                    },
                    ticks: {
                        stepSize: 1, // Show every integer value
                        maxTicksLimit: 18, // Force showing all 18 values (98-81)
                        autoSkip: false, // Don't skip any ticks
                        callback: function(value, index, values) {
                            // Map the index to the actual SpO2 value (98 down to 81)
                            const spo2Values = [98, 97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81];
                            return spo2Values[index] || value;
                        }
                    }
                }
            }
        }
    });
    
    // Store the chart reference globally
    if (chartId === 'spo2AtOrBelowChart') spo2AtOrBelowChart = newChart;
    else if (chartId === 'spo2AtChart') spo2AtChart = newChart;
    else if (chartId === 'activitySpo2AtOrBelowChart') activitySpo2AtOrBelowChart = newChart;
    else if (chartId === 'activitySpo2AtChart') activitySpo2AtChart = newChart;
}

// Create SpO2 chart for daily view
function createSpo2Chart(dateLabel, spo2Data, spo2Alerts, chartId, containerId) {
    console.log('createSpo2Chart called with:', {
        dateLabel,
        spo2DataLength: spo2Data.length,
        spo2AlertsLength: spo2Alerts.length,
        chartId,
        containerId
    });
    
    // Log alert data
    const alertPoints = spo2Alerts.filter(alert => alert.y !== null);
    console.log('Alert points to display:', alertPoints.length);
    if (alertPoints.length > 0) {
        console.log('First few alert points:', alertPoints.slice(0, 3));
    }
    
    const chartElement = document.getElementById(chartId);
    const containerElement = document.getElementById(containerId);
    
    if (!chartElement || !containerElement) {
        console.error('SpO2 chart elements not found');
        return;
    }
    
    // Destroy existing chart if it exists
    const existingChart = chartId === 'spo2Chart' ? spo2Chart : activitySpo2Chart;
    if (existingChart) {
        existingChart.destroy();
    }
    
    // Check if we have SpO2 data
    if (!spo2Data || spo2Data.length === 0) {
        containerElement.style.display = 'none';
        containerElement.style.height = '0px';
        return;
    }
    
    // Show container and set height
    containerElement.style.display = 'block';
    containerElement.style.height = '120px'; // Proportional to HR chart
    
    const ctx = chartElement.getContext('2d');
    
    // Get the date from the selected date label
    const chartDate = new Date(dateLabel + 'T00:00:00');
    
    // Create evenly spaced 24-hour timeline (every 1 minute for high resolution)
    const labels = [];
    for (let hour = 0; hour < 24; hour++) {
        for (let minute = 0; minute < 60; minute += 1) {
            const timestamp = new Date(chartDate);
            timestamp.setHours(hour, minute, 0, 0);
            labels.push(timestamp);
        }
    }
    
    // Process SpO2 data with smoothing (one point per minute, averaged from raw data)
    const chartLabels = [];
    const chartData = [];
    
    // Sort SpO2 data by timestamp
    const sortedSpo2Data = spo2Data.sort((a, b) => a.x.getTime() - b.x.getTime());
    
    // First, create averaged data points for each minute
    const averagedDataPoints = [];
    
    // Process each minute
    for (let hour = 0; hour < 24; hour++) {
        for (let minute = 0; minute < 60; minute += 1) {
            const minuteStart = new Date(chartDate);
            minuteStart.setHours(hour, minute, 0, 0);
            
            const minuteEnd = new Date(chartDate);
            minuteEnd.setHours(hour, minute, 59, 999);
            
            // Find all data points within this minute
            const pointsInMinute = sortedSpo2Data.filter(point => {
                const pointTime = point.x.getTime();
                return pointTime >= minuteStart.getTime() && pointTime <= minuteEnd.getTime();
            });
            
            if (pointsInMinute.length > 0) {
                // Calculate average of all points in this minute
                const sum = pointsInMinute.reduce((acc, point) => acc + point.y, 0);
                const average = sum / pointsInMinute.length;
                
                // Add the average point at the middle of the minute
                const minuteMiddle = new Date(minuteStart.getTime() + 30 * 1000); // 30 seconds into the minute
                averagedDataPoints.push({
                    timestamp: minuteMiddle,
                    value: average
                });
            }
        }
    }
    
    // Add data points and insert null values for gaps > 5 minutes (same logic as HR chart)
    for (let i = 0; i < averagedDataPoints.length; i++) {
        const currentPoint = averagedDataPoints[i];
        
        // Add the current data point
        chartLabels.push(currentPoint.timestamp);
        chartData.push(currentPoint.value);
        
        // Check if there's a gap to the next point
        if (i < averagedDataPoints.length - 1) {
            const nextPoint = averagedDataPoints[i + 1];
            const gapMinutes = (nextPoint.timestamp.getTime() - currentPoint.timestamp.getTime()) / (1000 * 60);
            
            // If gap is > 5 minutes, add a null point to create a visual break
            if (gapMinutes > 5) {
                // Add a null point 1 minute after the current segment
                const gapTimestamp = new Date(currentPoint.timestamp.getTime() + (1 * 60 * 1000)); // 1 minute after current
                chartLabels.push(gapTimestamp);
                chartData.push(null);
                
                // Add a null point 1 minute before the next segment
                const nextGapTimestamp = new Date(nextPoint.timestamp.getTime() - (1 * 60 * 1000)); // 1 minute before next
                chartLabels.push(nextGapTimestamp);
                chartData.push(null);
            }
        }
    }
    
    // Create the chart
    const newChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                // Background dataset with SpO2 color bands (only 2 points to avoid tooltip interference)
                {
                    label: 'Background',
                    data: [
                        { x: labels[0], y: 100 },
                        { x: labels[labels.length - 1], y: 100 }
                    ],
                    borderColor: 'transparent',
                    backgroundColor: function(context) {
                        const chart = context.chart;
                        const {ctx, chartArea} = chart;
                        
                        if (!chartArea) {
                            return 'transparent';
                        }
                        
                        // Create gradient for SpO2 zones
                        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        
                        // Add color stops for 8 equal SpO2 bands (top to bottom)
                        gradient.addColorStop(0, '#28a745');     // Band 1: Green (top)
                        gradient.addColorStop(0.25, '#28a745');  // Band 2: Green
                        gradient.addColorStop(0.25, '#9acd32');  // Band 3: Yellow-Green
                        gradient.addColorStop(0.375, '#9acd32'); // Band 4: Yellow
                        gradient.addColorStop(0.375, '#ffc107'); // Band 5: Orange
                        gradient.addColorStop(0.5, '#ffc107');   // Band 6: Red
                        gradient.addColorStop(0.5, '#fd7e14');   // Band 7: Hot Red
                        gradient.addColorStop(0.625, '#fd7e14'); // Band 8: Hot Red
                        gradient.addColorStop(0.625, '#e74c3c'); // Band 8: Hot Red
                        gradient.addColorStop(0.75, '#e74c3c');  // Band 8: Hot Red
                        gradient.addColorStop(0.75, '#dc3545');  // Band 8: Hot Red
                        gradient.addColorStop(1, '#dc3545');     // Band 8: Hot Red (bottom)
                        
                        return gradient;
                    },
                    borderWidth: 0,
                    fill: true,
                    tension: 0,
                    pointRadius: 0,
                    order: 100
                },
                // SpO2 line on top
                {
                    label: 'SpO2 (%)',
                    data: chartLabels.map((label, index) => ({ x: label, y: chartData[index] })),
                    borderColor: '#000080',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: '#000080',
                    order: 0
                },
                // SpO2 alert line
                {
                    label: 'SpO2 Alerts',
                    data: spo2Alerts,
                    borderColor: '#ffc107',
                    backgroundColor: '#ffc107',
                    borderWidth: 0,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#ffc107',
                    order: 1 // Draw on top of SpO2 line
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            spanGaps: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            const rawData = context[0].raw;
                            if (rawData && rawData.x) {
                                const date = new Date(rawData.x);
                                const year = date.getFullYear();
                                const month = String(date.getMonth() + 1).padStart(2, '0');
                                const day = String(date.getDate()).padStart(2, '0');
                                const hour = String(date.getHours()).padStart(2, '0');
                                const minute = String(date.getMinutes()).padStart(2, '0');
                                const second = String(date.getSeconds()).padStart(2, '0');
                                return `Time: ${year}-${month}-${day} ${hour}:${minute}:${second}`;
                            }
                            return `Time: ${context[0].label}`;
                        },
                        label: function(context) {
                            if (context.dataset.label === 'SpO2 (%)') {
                                return `SpO2: ${context.parsed.y.toFixed(1)}%`;
                            } else if (context.dataset.label === 'SpO2 Alerts') {
                                return `SpO2 Alert: ${context.parsed.y.toFixed(1)}%`;
                            }
                            return null;
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
                            scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour',
                            displayFormats: {
                                hour: 'HH:mm'
                            }
                        },
                        display: true, // Show x-axis for gridlines
                        min: new Date(chartDate.getFullYear(), chartDate.getMonth(), chartDate.getDate(), 0, 0, 0),
                        max: new Date(chartDate.getFullYear(), chartDate.getMonth(), chartDate.getDate(), 23, 59, 0),
                        ticks: {
                            display: false, // Hide tick labels but keep gridlines
                            maxRotation: 0,
                            stepSize: 2,
                            source: 'auto'
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.3)', // Same as HR chart
                            drawBorder: false,
                            z: 1 // Try to ensure gridlines are drawn above background
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'SpO2 (%)'
                        },
                        min: 80,
                        max: 100,
                        ticks: {
                            stepSize: 5
                        }
                    }
                },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    // Store the chart reference
    if (chartId === 'spo2Chart') {
        spo2Chart = newChart;
        // Force resize to match HR chart container
        setTimeout(() => {
            if (spo2Chart && hrChart) {
                // Copy the HR chart's width to ensure perfect alignment
                const hrContainer = document.querySelector('.chart-container canvas#hrChart').parentElement;
                const spo2Container = document.querySelector('.chart-container canvas#spo2Chart').parentElement;
                if (hrContainer && spo2Container) {
                    spo2Container.style.width = hrContainer.offsetWidth + 'px';
                    spo2Chart.resize();
                }
            }
        }, 100);
    } else {
        activitySpo2Chart = newChart;
        // Force resize to match HR chart container
        setTimeout(() => {
            if (activitySpo2Chart && activityHrChart) {
                // Copy the HR chart's width to ensure perfect alignment
                const hrContainer = document.querySelector('.chart-container canvas#activityHrChart').parentElement;
                const spo2Container = document.querySelector('.chart-container canvas#activitySpo2Chart').parentElement;
                if (hrContainer && spo2Container) {
                    spo2Container.style.width = hrContainer.offsetWidth + 'px';
                    activitySpo2Chart.resize();
                }
            }
        }, 100);
    }
}

// Create SpO2 chart for activity view
function createActivitySpo2Chart(activity, spo2Data, spo2Alerts, chartId, containerId, startTime, endTime, optimalInterval, activityDurationMinutes) {
    console.log('createActivitySpo2Chart called with:', {
        activityId: activity.activity_id,
        spo2DataLength: spo2Data.length,
        spo2AlertsLength: spo2Alerts.length,
        chartId,
        containerId
    });
    
    // Log alert data
    const alertPoints = spo2Alerts.filter(alert => alert.y !== null);
    console.log('Activity alert points to display:', alertPoints.length);
    if (alertPoints.length > 0) {
        console.log('First few activity alert points:', alertPoints.slice(0, 3));
    }
    
    const chartElement = document.getElementById(chartId);
    const containerElement = document.getElementById(containerId);
    
    if (!chartElement || !containerElement) {
        console.error('Activity SpO2 chart elements not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (activitySpo2Chart) {
        activitySpo2Chart.destroy();
    }
    
    // Check if we have SpO2 data
    if (!spo2Data || spo2Data.length === 0) {
        containerElement.style.display = 'none';
        containerElement.style.height = '0px';
        return;
    }
    
    // Show container and set height
    containerElement.style.display = 'block';
    containerElement.style.height = '120px'; // Proportional to HR chart
    
    const ctx = chartElement.getContext('2d');
    
    // Sort SpO2 data by timestamp
    const sortedSpo2Data = spo2Data.sort((a, b) => a.x.getTime() - b.x.getTime());
    
    // Use standardized x-axis range passed from HR chart
    // startTime and endTime are now parameters from the standardized Garmin activity range
    
    // Use shared gridline parameters passed from HR chart
    // activityDurationMinutes and optimalInterval are now parameters
    
    // Create evenly spaced timeline for the standardized activity duration - simplified for exact chart area alignment
    const labels = [startTime, endTime];
    
    // Create the same afterBuildTicks function for consistent gridlines
    function createAfterBuildTicks(startTime, optimalInterval, activityDurationMinutes) {
        return function(axis) {
            // Replace the ticks with our custom ones at optimal intervals
            const newTicks = [];
            let currentTime = 0;
            while (currentTime <= activityDurationMinutes) {
                const tickTime = new Date(startTime.getTime() + (currentTime * 60 * 1000));
                newTicks.push({
                    value: tickTime.getTime(),
                    label: (() => {
                        const timeSinceStart = tickTime.getTime() - startTime.getTime();
                        const totalMinutes = timeSinceStart / (1000 * 60);
                        
                        if (optimalInterval <= 1) {
                            const minutes = Math.floor(totalMinutes);
                            const seconds = Math.floor((timeSinceStart % (1000 * 60)) / 1000);
                            return `${minutes}:${seconds.toString().padStart(2, '0')}`;
                        } else {
                            const hours = Math.floor(totalMinutes / 60);
                            const minutes = Math.floor(totalMinutes % 60);
                            return `${hours}:${minutes.toString().padStart(2, '0')}`;
                        }
                    })()
                });
                currentTime += optimalInterval;
            }
            axis.ticks = newTicks;
        };
    }
    
    // Process SpO2 data
    const chartLabels = [];
    const chartData = [];
    
    // Add data points and insert null values for gaps > 5 minutes
    for (let i = 0; i < sortedSpo2Data.length; i++) {
        const currentPoint = sortedSpo2Data[i];
        
        // Add the current data point
        chartLabels.push(currentPoint.x);
        chartData.push(currentPoint.y);
        
        // Check if there's a gap to the next point
        if (i < sortedSpo2Data.length - 1) {
            const nextPoint = sortedSpo2Data[i + 1];
            const gapMinutes = (nextPoint.x.getTime() - currentPoint.x.getTime()) / (1000 * 60);
            
            // If gap is > 5 minutes, add a null point to create a visual break
            if (gapMinutes > 5) {
                // Add a null point 1 minute after the current segment
                const gapTimestamp = new Date(currentPoint.x.getTime() + (1 * 60 * 1000));
                chartLabels.push(gapTimestamp);
                chartData.push(null);
                
                // Add a null point 1 minute before the next segment
                const nextGapTimestamp = new Date(nextPoint.x.getTime() - (1 * 60 * 1000));
                chartLabels.push(nextGapTimestamp);
                chartData.push(null);
            }
        }
    }
    
    // Create the chart
    const newChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                // Background dataset with SpO2 color bands
                {
                    label: 'Background',
                    data: [
                        { x: startTime, y: 100 },
                        { x: endTime, y: 100 }
                    ],
                    borderColor: 'transparent',
                    backgroundColor: function(context) {
                        const chart = context.chart;
                        const {ctx, chartArea} = chart;
                        
                        if (!chartArea) {
                            return 'transparent';
                        }
                        
                        // Create gradient for SpO2 zones
                        const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                        
                        // Add color stops for 8 equal SpO2 bands (top to bottom)
                        gradient.addColorStop(0, '#28a745');     // Band 1: Green (top)
                        gradient.addColorStop(0.25, '#28a745');  // Band 2: Green
                        gradient.addColorStop(0.25, '#9acd32');  // Band 3: Yellow-Green
                        gradient.addColorStop(0.375, '#9acd32'); // Band 4: Yellow
                        gradient.addColorStop(0.375, '#ffc107'); // Band 5: Orange
                        gradient.addColorStop(0.5, '#ffc107');   // Band 6: Red
                        gradient.addColorStop(0.5, '#fd7e14');   // Band 7: Hot Red
                        gradient.addColorStop(0.625, '#fd7e14'); // Band 8: Hot Red
                        gradient.addColorStop(0.625, '#e74c3c'); // Band 8: Hot Red
                        gradient.addColorStop(0.75, '#e74c3c');  // Band 8: Hot Red
                        gradient.addColorStop(0.75, '#dc3545');  // Band 8: Hot Red
                        gradient.addColorStop(1, '#dc3545');     // Band 8: Hot Red (bottom)
                        
                        return gradient;
                    },
                    borderWidth: 0,
                    fill: true,
                    tension: 0,
                    pointRadius: 0,
                    order: 100
                },
                // SpO2 line on top
                {
                    label: 'SpO2 (%)',
                    data: chartLabels.map((label, index) => ({ x: label, y: chartData[index] })),
                    borderColor: '#000080',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: '#000080',
                    order: 0
                },
                // SpO2 alert line
                {
                    label: 'SpO2 Alerts',
                    data: spo2Alerts,
                    borderColor: '#ffc107',
                    backgroundColor: '#ffc107',
                    borderWidth: 0,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#ffc107',
                    order: 1 // Draw on top of SpO2 line
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            spanGaps: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'nearest',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            const rawData = context[0].raw;
                            if (rawData && rawData.x) {
                                const date = new Date(rawData.x);
                                const timeSinceStart = date.getTime() - startTime.getTime();
                                const totalMinutes = timeSinceStart / (1000 * 60);
                                
                                if (optimalInterval <= 1) {
                                    // For 30s and 1m intervals: use m:ss format
                                    const minutes = Math.floor(totalMinutes);
                                    const seconds = Math.floor((timeSinceStart % (1000 * 60)) / 1000);
                                    return `Time: ${minutes}:${seconds.toString().padStart(2, '0')}`;
                                } else {
                                    // For 5m and larger intervals: use h:mm:ss format
                                    const hours = Math.floor(totalMinutes / 60);
                                    const minutes = Math.floor(totalMinutes % 60);
                                    const seconds = Math.floor((timeSinceStart % (1000 * 60)) / 1000);
                                    return `Time: ${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                                }
                            }
                            return `Time: ${context[0].label}`;
                        },
                        label: function(context) {
                            if (context.dataset.label === 'SpO2 (%)') {
                                return `SpO2: ${context.parsed.y.toFixed(1)}%`;
                            } else if (context.dataset.label === 'SpO2 Alerts') {
                                return `SpO2 Alert: ${context.parsed.y.toFixed(1)}%`;
                            }
                            return null;
                        }
                    }
                },
                datalabels: {
                    display: false
                }
            },
                            scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'mm:ss',
                                second: 'mm:ss'
                            }
                        },
                        display: true, // Show x-axis for gridlines
                        min: startTime,
                        max: endTime,
                        ticks: {
                            display: false, // Hide tick labels but keep gridlines
                            maxRotation: 0,
                            source: 'auto',
                            callback: function(value, index, values) {
                                // Calculate time since activity start
                                const timestamp = new Date(value);
                                const timeSinceStart = timestamp.getTime() - startTime.getTime();
                                const totalMinutes = timeSinceStart / (1000 * 60);
                                
                                if (optimalInterval <= 1) {
                                    // For 30s and 1m intervals: use m:ss format
                                    const minutes = Math.floor(totalMinutes);
                                    const seconds = Math.floor((timeSinceStart % (1000 * 60)) / 1000);
                                    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
                                } else {
                                    // For 5m and larger intervals: use h:mm format
                                    const hours = Math.floor(totalMinutes / 60);
                                    const minutes = Math.floor(totalMinutes % 60);
                                    return `${hours}:${minutes.toString().padStart(2, '0')}`;
                                }
                            }
                        },
                        afterBuildTicks: createAfterBuildTicks(startTime, optimalInterval, activityDurationMinutes),
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.3)', // Same as HR chart
                            drawBorder: false,
                            z: 1 // Try to ensure gridlines are drawn above background
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'SpO2 (%)'
                        },
                        min: 80,
                        max: 100,
                        ticks: {
                            stepSize: 5
                        }
                    }
                },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
    
    // Store the chart reference
    activitySpo2Chart = newChart;
    // Force resize to match HR chart container
    setTimeout(() => {
        if (activitySpo2Chart && activityHrChart) {
            // Copy the HR chart's width to ensure perfect alignment
            const hrContainer = document.querySelector('.chart-container canvas#activityHrChart').parentElement;
            const spo2Container = document.querySelector('.chart-container canvas#activitySpo2Chart').parentElement;
            if (hrContainer && spo2Container) {
                spo2Container.style.width = hrContainer.offsetWidth + 'px';
                activitySpo2Chart.resize();
            }
        }
    }, 100);
}
