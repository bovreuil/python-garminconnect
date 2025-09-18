/**
 * Chart Creation Functions
 * 
 * Shared chart creation functions extracted from dashboard templates.
 * These functions are identical across pages and handle the complex
 * Chart.js creation logic for various chart types.
 */

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
    
    // Group SpO2 data by minute and average
    for (let i = 0; i < labels.length; i++) {
        const currentMinute = labels[i];
        const nextMinute = new Date(currentMinute.getTime() + 60000); // Add 1 minute
        
        // Find all SpO2 readings within this minute
        const readingsInMinute = spo2Data.filter(reading => {
            const readingTime = new Date(reading[0]);
            return readingTime >= currentMinute && readingTime < nextMinute;
        });
        
        if (readingsInMinute.length > 0) {
            // Average the SpO2 values for this minute
            const avgSpo2 = readingsInMinute.reduce((sum, reading) => sum + reading[1], 0) / readingsInMinute.length;
            chartLabels.push(currentMinute);
            chartData.push({
                x: currentMinute,
                y: avgSpo2
            });
        }
    }
    
    // Process alert data for display
    const alertData = spo2Alerts.filter(alert => alert.y !== null).map(alert => ({
        x: new Date(alert.x),
        y: alert.y
    }));
    
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
                    fill: true,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    order: 3
                },
                // SpO2 data line
                {
                    label: 'SpO2 %',
                    data: chartData,
                    borderColor: '#000000',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.1,
                    order: 1
                },
                // Alert points
                {
                    label: 'SpO2 Alerts',
                    data: alertData,
                    borderColor: '#ff0000',
                    backgroundColor: '#ff0000',
                    borderWidth: 0,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    showLine: false,
                    order: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        filter: function(legendItem, chartData) {
                            // Hide the background dataset from legend
                            return legendItem.text !== 'Background';
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            if (context && context[0]) {
                                const date = new Date(context[0].parsed.x);
                                return date.toLocaleTimeString('en-GB', { 
                                    hour: '2-digit', 
                                    minute: '2-digit',
                                    hour12: false 
                                });
                            }
                            return '';
                        },
                        label: function(context) {
                            if (context.dataset.label === 'Background') {
                                return null; // Hide background dataset from tooltip
                            }
                            const value = context.parsed.y;
                            if (context.dataset.label === 'SpO2 Alerts') {
                                return `Alert: ${value.toFixed(1)}%`;
                            }
                            return `${context.dataset.label}: ${value.toFixed(1)}%`;
                        }
                    }
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
                    title: {
                        display: true,
                        text: 'Time'
                    },
                    min: labels[0],
                    max: labels[labels.length - 1]
                },
                y: {
                    beginAtZero: false,
                    min: 80,
                    max: 100,
                    title: {
                        display: true,
                        text: 'SpO2 (%)'
                    },
                    ticks: {
                        stepSize: 2
                    }
                }
            }
        }
    });
    
    // Store the chart reference globally based on chartId
    if (chartId === 'spo2Chart') {
        spo2Chart = newChart;
    } else if (chartId === 'activitySpo2Chart') {
        activitySpo2Chart = newChart;
    }
}

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

// Create activity breathing chart
function createActivityBreathingChart(activity, breathingData, chartId, containerId, startTime, endTime, optimalInterval, activityDurationMinutes) {
    const chartElement = document.getElementById(chartId);
    const containerElement = document.getElementById(containerId);
    
    if (!chartElement || !containerElement) {
        console.error('Activity breathing chart elements not found');
        return;
    }
    
    // Destroy existing chart if it exists
    if (activityBreathingChart) {
        activityBreathingChart.destroy();
    }
    
    // Check if we have breathing data
    if (!breathingData || breathingData.length === 0) {
        containerElement.style.display = 'none';
        containerElement.style.height = '0px';
        return;
    }
    
    // Show container and set height (20% higher than SpO2 chart)
    containerElement.style.display = 'block';
    containerElement.style.height = '144px'; // 120px * 1.2 = 144px
    
    const ctx = chartElement.getContext('2d');
    
    // Sort breathing data by timestamp
    const sortedBreathingData = breathingData.sort((a, b) => a.x.getTime() - b.x.getTime());
    
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
    
    // Process breathing data
    const chartLabels = [];
    const chartData = [];
    
    // Add data points and insert null values for gaps > 5 minutes
    for (let i = 0; i < sortedBreathingData.length; i++) {
        const currentPoint = sortedBreathingData[i];
        
        // Add the current data point
        chartLabels.push(currentPoint.x);
        chartData.push(currentPoint.y);
        
        // Check if there's a gap to the next point
        if (i < sortedBreathingData.length - 1) {
            const nextPoint = sortedBreathingData[i + 1];
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
                // Background dataset with solid grey background
                {
                    label: 'Background',
                    data: [
                        { x: startTime, y: 100 },
                        { x: endTime, y: 100 }
                    ],
                    borderColor: 'transparent',
                    backgroundColor: '#f8f9fa', // Light grey background
                    borderWidth: 0,
                    fill: true,
                    tension: 0,
                    pointRadius: 0,
                    order: 100
                },
                // Breathing line on top
                {
                    label: 'Breathing (BRPM)',
                    data: chartLabels.map((label, index) => ({ x: label, y: chartData[index] })),
                    borderColor: '#6c757d', // Grey color for breathing line
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    pointHoverBackgroundColor: '#6c757d',
                    order: 0
                },
                // Dummy alert dataset to match SpO2 chart area calculation
                {
                    label: 'Dummy Alerts',
                    data: [{ x: startTime, y: 40 }],
                    borderColor: '#f8f9fa',
                    backgroundColor: '#f8f9fa',
                    borderWidth: 0,
                    fill: false,
                    tension: 0.1,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: '#f8f9fa',
                    order: 1
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
                            if (context.dataset.label === 'Breathing (BRPM)') {
                                return `Breathing: ${context.parsed.y.toFixed(1)} BRPM`;
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
                        text: 'Breathing (BRPM)'
                    },
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20
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
    activityBreathingChart = newChart;
    // Force resize to match HR chart container
    setTimeout(() => {
        if (activityBreathingChart && activityHrChart) {
            // Copy the HR chart's width to ensure perfect alignment
            const hrContainer = document.querySelector('.chart-container canvas#activityHrChart').parentElement;
            const breathingContainer = document.querySelector('.chart-container canvas#activityBreathingChart').parentElement;
            if (hrContainer && breathingContainer) {
                breathingContainer.style.width = hrContainer.offsetWidth + 'px';
                activityBreathingChart.resize();
            }
        }
    }, 100);
}

// Create 24-hour heart rate chart
function createHeartRateChart(dateLabel, dayData) {
    
    const chartElement = document.getElementById('hrChart');
    if (!chartElement) {
        console.error('hrChart element not found');
        return;
    }
    
    const chartContainer = chartElement.parentElement;
    if (!chartContainer) {
        console.error('Chart container not found');
        return;
    }
    
    console.log('Chart element:', chartElement);
    console.log('Chart container:', chartContainer);
    console.log('Chart container dimensions:', chartContainer.offsetWidth, 'x', chartContainer.offsetHeight);
    console.log('Chart element dimensions:', chartElement.offsetWidth, 'x', chartElement.offsetHeight);
    
    const ctx = chartElement.getContext('2d');
    console.log('Chart context:', ctx);
    
    // Clean up any existing message overlay and restore canvas visibility
    const existingMessage = document.getElementById('hrChartMessage');
    if (existingMessage) {
        existingMessage.remove();
    }
    chartElement.style.display = 'block';
    
    // Destroy existing chart if it exists
    if (hrChart) {
        hrChart.destroy();
    }
    
    // Check if we have heart rate values
    if (!dayData.heart_rate_values || !Array.isArray(dayData.heart_rate_values) || dayData.heart_rate_values.length === 0) {
        // No raw data available - show message
        hrChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Heart Rate',
                    data: [],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    fill: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                scales: {
                    x: {
                        display: false
                    },
                    y: {
                        display: false
                    }
                }
            }
        });
        
        // Hide the canvas and show a message overlay
        chartElement.style.display = 'none';
        const messageDiv = document.createElement('div');
        messageDiv.className = 'd-flex align-items-center justify-content-center h-100';
        messageDiv.innerHTML = '<p class="text-muted">No heart rate time-series data available</p>';
        messageDiv.id = 'hrChartMessage';
        chartContainer.appendChild(messageDiv);
        return;
    }
    
    // Process heart rate values
    const hrData = dayData.heart_rate_values;
    
    // Get the date from the selected date label
    const chartDate = new Date(dateLabel + 'T00:00:00');
    
    // Create evenly spaced 24-hour timeline (every 1 minute for high resolution)
    const labels = [];
    const data = [];
    
    for (let hour = 0; hour < 24; hour++) {
        for (let minute = 0; minute < 60; minute += 1) {
            const timestamp = new Date(chartDate);
            timestamp.setHours(hour, minute, 0, 0);
            labels.push(timestamp);
            data.push(null);
        }
    }
    
    // Sort data by timestamp
    const sortedData = hrData.sort((a, b) => {
        const timestampA = Array.isArray(a) ? a[0] : a.timestamp;
        const timestampB = Array.isArray(b) ? b[0] : b.timestamp;
        return timestampA - timestampB;
    });
    

    
    // Map heart rate data to the 24-hour timeline
    sortedData.forEach(point => {
        let timestamp, hr;
        
        if (Array.isArray(point)) {
            // Format: [timestamp, value]
            timestamp = point[0];
            hr = point[1];
        } else {
            // Format: {"value": x, "timestamp": y}
            timestamp = point.timestamp;
            hr = point.value;
        }
        
        // Skip null values
        if (hr === null || hr === undefined) return;
        
        // Convert timestamp to Date object
        const date = new Date(timestamp);
        
        // Find the exact index in our labels array (1-minute precision)
        const hour = date.getHours();
        const minute = date.getMinutes();
        
        // Create a timestamp for comparison (same date, specific hour/minute)
        const comparisonTimestamp = new Date(chartDate);
        comparisonTimestamp.setHours(hour, minute, 0, 0);
        
        const index = labels.findIndex(label => label.getTime() === comparisonTimestamp.getTime());
        if (index !== -1) {
            data[index] = hr;
        }
    });
    

    
    // Create a smart dataset that only includes null values for actual gaps
    const chartLabels = [];
    const chartData = [];
    
    // Sort the actual data points by timestamp
    const actualDataPoints = [];
    for (let i = 0; i < labels.length; i++) {
        if (data[i] !== null) {
            actualDataPoints.push({
                timestamp: labels[i],
                value: data[i]
            });
        }
    }
    
    // Add data points and insert null values for gaps > 5 minutes
    for (let i = 0; i < actualDataPoints.length; i++) {
        const currentPoint = actualDataPoints[i];
        
        // Add the current data point
        chartLabels.push(currentPoint.timestamp);
        chartData.push(currentPoint.value);
        
        // Check if there's a gap to the next point
        if (i < actualDataPoints.length - 1) {
            const nextPoint = actualDataPoints[i + 1];
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
    
    // Process SpO2 data if available
    const spo2Data = [];
    const spo2Alerts = [];
    if (dayData.spo2_values && Array.isArray(dayData.spo2_values) && dayData.spo2_values.length > 0) {
        console.log('Processing SpO2 data for day:', dayData.spo2_values.length, 'points');
        let alertCount = 0;
        dayData.spo2_values.forEach(spo2Point => {
            const timestamp = new Date(spo2Point[0]);
            const spo2Value = spo2Point[1];
            const spo2Reminder = spo2Point[2] || 0; // SpO2 Reminder column
            
            // Only include SpO2 data for this day
            if (timestamp.getDate() === chartDate.getDate() && 
                timestamp.getMonth() === chartDate.getMonth() && 
                timestamp.getFullYear() === chartDate.getFullYear()) {
                spo2Data.push({
                    x: timestamp,
                    y: spo2Value
                });
                
                // Add alert data (87 if SpO2 <= 87, null otherwise)
                const alertValue = spo2Value <= 87 ? 87 : null;
                spo2Alerts.push({
                    x: timestamp,
                    y: alertValue
                });
                
                if (spo2Value <= 87) {
                    alertCount++;
                    console.log('Found SpO2 alert at:', timestamp, 'SpO2:', spo2Value);
                }
            }
        });
        console.log('Day SpO2 processing complete. Total alerts found:', alertCount);
        console.log('SpO2 data points:', spo2Data.length);
        console.log('SpO2 alert points:', spo2Alerts.length);
    }
    
    // Create SpO2 chart if data exists
    createSpo2Chart(dateLabel, spo2Data, spo2Alerts, 'spo2Chart', 'spo2ChartContainer');
    
    // Load SpO2 distribution data if SpO2 data exists
    if (spo2Data && spo2Data.length > 0) {
        loadDailySpo2Distribution(dateLabel);
    } else {
        hideSpo2DistributionCharts();
    }
    
    // Small delay to ensure DOM is ready
    setTimeout(() => {
        // Create datasets array (HR only - SpO2 is in separate chart)
        const datasets = [
            // Single background dataset with gradient (only 2 points to avoid tooltip interference)
            {
                label: 'Background',
                data: [
                    { x: labels[0], y: 160 },
                    { x: labels[labels.length - 1], y: 160 }
                ], // Full height background for 24-hour timeline
                borderColor: 'transparent',
                backgroundColor: function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    
                    if (!chartArea) {
                        return 'transparent';
                    }
                    
                    // Create gradient
                    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    
                    // Add color stops for each zone
                    gradient.addColorStop(0, '#e74c3c'); // 160+ Red
                    gradient.addColorStop(1/12, '#e74c3c'); // 150-159 Red
                    gradient.addColorStop(1/12, '#fd7e14'); // 150-159 Orange
                    gradient.addColorStop(1/6, '#fd7e14'); // 140-149 Orange
                    gradient.addColorStop(1/6, '#ffc107'); // 140-149 Yellow
                    gradient.addColorStop(3/12, '#ffc107'); // 130-139 Yellow
                    gradient.addColorStop(3/12, '#9acd32'); // 130-139 Yellow-green
                    gradient.addColorStop(1/3, '#9acd32'); // 120-129 Yellow-green
                    gradient.addColorStop(1/3, '#28a745'); // 120-129 Green
                    gradient.addColorStop(5/12, '#28a745'); // 110-119 Green
                    gradient.addColorStop(5/12, '#006d5b'); // 110-119 Deep teal
                    gradient.addColorStop(1/2, '#006d5b'); // 100-109 Deep teal
                    gradient.addColorStop(1/2, '#004080'); // 100-109 Night sky blue
                    gradient.addColorStop(7/12, '#004080'); // 90-99 Night sky blue
                    gradient.addColorStop(7/12, '#002040'); // 80-89 Midnight
                    gradient.addColorStop(2/3, '#002040'); // 80-89 Midnight
                    gradient.addColorStop(2/3, '#000000'); // 80-89 Black
                    gradient.addColorStop(1, '#000000'); // Below 80 Black
                    
                    return gradient;
                },
                borderWidth: 0,
                fill: true,
                tension: 0,
                pointRadius: 0,
                order: 100 // Draw background first
            },
            // Heart rate line on top
            {
                label: 'Heart Rate (BPM)',
                data: chartLabels.map((label, index) => ({ x: label, y: chartData[index] })), // Use data with null values for gaps
                borderColor: '#e74c3c',
                backgroundColor: 'transparent',
                borderWidth: 2,
                fill: false,
                tension: 0.1,
                pointRadius: 0,
                pointHoverRadius: 4,
                pointHoverBackgroundColor: '#e74c3c',
                order: 0
            },
            // Dummy alert dataset to match SpO2 chart area calculation
            {
                label: 'Dummy Alerts',
                data: [{ x: new Date(chartDate.getFullYear(), chartDate.getMonth(), chartDate.getDate(), 12, 0, 0), y: 40 }],
                borderColor: '#002040',
                backgroundColor: '#002040',
                borderWidth: 0,
                fill: false,
                tension: 0.1,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#002040',
                order: 1
            }
        ];
        
        // Create the chart
        hrChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels, // Use full 24-hour timeline for consistent x-axis
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                spanGaps: false, // Don't draw lines across gaps
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'nearest',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                // Get the raw timestamp from the data point
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
                                // Fallback to the label if raw data not available
                                return `Time: ${context[0].label}`;
                            },
                            label: function(context) {
                                // Show tooltip for heart rate and SpO2 data
                                if (context.dataset.label === 'Heart Rate (BPM)') {
                                    return `Heart Rate: ${context.parsed.y} BPM`;
                                } else if (context.dataset.label === 'SpO2 (%)') {
                                    return `SpO2: ${context.parsed.y.toFixed(1)}%`;
                                }
                                return null; // Hide background dataset from tooltip
                            }
                        }
                    },
                    datalabels: {
                        display: false,
                        formatter: function() {
                            return ''; // Return empty string to ensure no labels
                        }
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
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        min: new Date(chartDate.getFullYear(), chartDate.getMonth(), chartDate.getDate(), 0, 0, 0),
                        max: new Date(chartDate.getFullYear(), chartDate.getMonth(), chartDate.getDate(), 23, 59, 0),
                        ticks: {
                            maxRotation: 0,
                            stepSize: 2,
                            source: 'auto'
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.3)', // Same as activity chart
                            drawBorder: false,
                            z: 1 // Try to ensure gridlines are drawn above background
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Heart Rate (BPM)'
                        },
                        min: 40,
                        max: 160,
                        ticks: {
                            stepSize: 20
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
        
        
    }, 100);
}

// Create activity heart rate chart
function createActivityHeartRateChart(activity) {
    console.log('Creating activity heart rate chart for activity:', activity);
    
    // Ensure the single activity section is visible
    const singleActivitySection = document.getElementById('singleActivitySection');
    if (!singleActivitySection || singleActivitySection.style.display === 'none') {
        console.error('Single activity section is not visible');
        return;
    }
    
    // Ensure we have clean canvas elements
    const chartContainer = document.querySelector('#singleActivitySection .chart-container');
    const spo2ChartContainer = document.getElementById('activitySpo2ChartContainer');
    
    if (!chartContainer) {
        console.error('Activity chart container not found');
        return;
    }
    
    if (!spo2ChartContainer) {
        console.error('Activity SpO2 chart container not found');
        return;
    }
    
    // Clear the containers and recreate the canvases
    chartContainer.innerHTML = '<canvas id="activityHrChart"></canvas>';
    spo2ChartContainer.innerHTML = '<canvas id="activitySpo2Chart"></canvas>';
    
    const breathingChartContainer = document.getElementById('activityBreathingChartContainer');
    if (breathingChartContainer) {
        breathingChartContainer.innerHTML = '<canvas id="activityBreathingChart"></canvas>';
    }
    
    // Clear SpO2 distribution chart containers
    const spo2DistributionContainer = document.getElementById('activitySpo2DistributionChartsContainer');
    if (spo2DistributionContainer) {
        spo2DistributionContainer.style.display = 'none';
    }
    
    const chartElement = document.getElementById('activityHrChart');
    if (!chartElement) {
        console.error('Activity chart element not found after recreation');
        return;
    }
    
    console.log('Activity chart element:', chartElement);
    console.log('Activity chart container:', chartContainer);
    
    const ctx = chartElement.getContext('2d');
    if (!ctx) {
        console.error('Could not get 2D context for activity chart');
        return;
    }
    console.log('Activity chart context:', ctx);
    
    // Destroy existing chart if it exists
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
    
    // Destroy SpO2 distribution charts if they exist
    if (activitySpo2AtOrBelowChart) {
        activitySpo2AtOrBelowChart.destroy();
        activitySpo2AtOrBelowChart = null;
    }
    if (activitySpo2AtChart) {
        activitySpo2AtChart.destroy();
        activitySpo2AtChart = null;
    }
    
    // Check if we have heart rate values for this activity
    if (!activity.heart_rate_values || !Array.isArray(activity.heart_rate_values) || activity.heart_rate_values.length === 0) {
        console.log('No heart rate values available for activity');
        console.log('Activity data keys:', Object.keys(activity));
        console.log('heart_rate_values value:', activity.heart_rate_values);
        console.log('heart_rate_values type:', typeof activity.heart_rate_values);
        console.log('heart_rate_values length:', activity.heart_rate_values ? activity.heart_rate_values.length : 'N/A');
        console.log('Full activity data:', activity);
        
        // Wait for DOM to be ready before creating chart
        setTimeout(() => {
            // No raw data available - show message
            activityHrChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Heart Rate',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 2,
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: false
                        }
                    },
                    scales: {
                        x: {
                            display: false
                        },
                        y: {
                            display: false
                        }
                    }
                }
            });
            
            // Add a message overlay
            chartContainer.innerHTML = '<div class="d-flex align-items-center justify-content-center h-100"><p class="text-muted">No heart rate time-series data available for this activity</p></div>';
            spo2ChartContainer.innerHTML = '<canvas id="activitySpo2Chart"></canvas>';
            if (breathingChartContainer) {
                breathingChartContainer.innerHTML = '<canvas id="activityBreathingChart"></canvas>';
            }
        }, 100);
        return;
    }
    
    // Process heart rate values (Garmin activity data only)
    const hrData = activity.heart_rate_values;
    console.log('Activity heart rate values length:', hrData.length);
    
    // Calculate standardized x-axis range from Garmin activity data only
    const sortedHrData = hrData.sort((a, b) => {
        const timestampA = Array.isArray(a) ? a[0] : a.timestamp;
        const timestampB = Array.isArray(b) ? b[0] : b.timestamp;
        return timestampA - timestampB;
    });
    
    // Get the standardized x-axis range from Garmin activity data
    const garminStartTime = new Date(sortedHrData[0][0]); // First Garmin timestamp
    const garminEndTime = new Date(sortedHrData[sortedHrData.length - 1][0]); // Last Garmin timestamp
    
    console.log('Standardized x-axis range - Start:', garminStartTime);
    console.log('Standardized x-axis range - End:', garminEndTime);
    
    // Process SpO2 data if available - filter to fit within Garmin activity range
    const spo2Data = [];
    const spo2Alerts = [];
    if (activity.spo2_values && activity.spo2_values.length > 0) {
        console.log('Processing SpO2 data for activity:', activity.spo2_values.length, 'points');
        let alertCount = 0;
        activity.spo2_values.forEach(spo2Point => {
            const spo2Timestamp = new Date(spo2Point[0]);
            const spo2Value = spo2Point[1];
            const spo2Reminder = spo2Point[2] || 0; // SpO2 Reminder column
            
            // Only include SpO2 data that falls within the Garmin activity range
            if (spo2Timestamp >= garminStartTime && spo2Timestamp <= garminEndTime) {
                spo2Data.push({
                    x: spo2Timestamp,
                    y: spo2Value
                });
                
                // Add alert data (87 if SpO2 <= 87, null otherwise)
                const alertValue = spo2Value <= 87 ? 87 : null;
                spo2Alerts.push({
                    x: spo2Timestamp,
                    y: alertValue
                });
                
                if (spo2Value <= 87) {
                    alertCount++;
                    console.log('Found activity SpO2 alert at:', spo2Timestamp, 'SpO2:', spo2Value);
                }
            }
        });
        console.log('Activity SpO2 processing complete. Total alerts found:', alertCount);
        console.log('Filtered SpO2 data points within Garmin range:', spo2Data.length);
        console.log('SpO2 alert points:', spo2Alerts.length);
    }
    
    // Process breathing data if available - filter to fit within Garmin activity range
    const breathingData = [];
    if (activity.breathing_rate_values && activity.breathing_rate_values.length > 0) {
        console.log('Processing breathing data for activity:', activity.breathing_rate_values.length, 'points');
        activity.breathing_rate_values.forEach(breathingPoint => {
            const breathingTimestamp = new Date(breathingPoint[0]);
            // Only include breathing data that falls within the Garmin activity range
            if (breathingTimestamp >= garminStartTime && breathingTimestamp <= garminEndTime) {
                breathingData.push({
                    x: breathingTimestamp,
                    y: breathingPoint[1]
                });
            }
        });
        console.log('Filtered breathing data points within Garmin range:', breathingData.length);
    }
    
    console.log('First few HR data points:', hrData.slice(0, 5));
    
    // Use the already sorted HR data from above
    const sortedData = sortedHrData;
    
    console.log('Sorted activity data length:', sortedData.length);
    
    // Extract timestamps and heart rate values
    const timestamps = [];
    const hrValues = [];
    const breathingValues = [];
    
    sortedData.forEach(point => {
        let timestamp, hr;
        
        if (Array.isArray(point)) {
            // Format: [timestamp, value]
            timestamp = point[0];
            hr = point[1];
        } else {
            // Format: {"value": x, "timestamp": y}
            timestamp = point.timestamp;
            hr = point.value;
        }
        
        // Skip null values
        if (hr === null || hr === undefined) return;
        
        timestamps.push(new Date(timestamp));
        hrValues.push(hr);
    });
    
    // Breathing data removed from scope for alignment consistency
    
    console.log('Processed activity timestamps length:', timestamps.length);
    console.log('Processed activity HR values length:', hrValues.length);
    console.log('First few timestamps:', timestamps.slice(0, 5));
    console.log('First few HR values:', hrValues.slice(0, 5));
    
    // Create a smart dataset that only includes null values for actual gaps
    const chartLabels = [];
    const chartData = [];
    
    // Add data points and insert null values for gaps > 5 minutes
    for (let i = 0; i < timestamps.length; i++) {
        const currentPoint = timestamps[i];
        const currentHR = hrValues[i];
        
        // Add the current data point
        chartLabels.push(currentPoint);
        chartData.push(currentHR);
        
        // Check if there's a gap to the next point
        if (i < timestamps.length - 1) {
            const nextPoint = timestamps[i + 1];
            const gapMinutes = (nextPoint.getTime() - currentPoint.getTime()) / (1000 * 60);
            
            // If gap is > 5 minutes, add a null point to create a visual break
            if (gapMinutes > 5) {
                // Add a null point 1 minute after the current segment
                const gapTimestamp = new Date(currentPoint.getTime() + (1 * 60 * 1000)); // 1 minute after current
                chartLabels.push(gapTimestamp);
                chartData.push(null);
                
                // Add a null point 1 minute before the next segment
                const nextGapTimestamp = new Date(nextPoint.getTime() - (1 * 60 * 1000)); // 1 minute before next
                chartLabels.push(nextGapTimestamp);
                chartData.push(null);
            }
        }
    }
    
    console.log('Chart labels length:', chartLabels.length);
    console.log('Chart data length:', chartData.length);
    console.log('First few chart labels:', chartLabels.slice(0, 5));
    console.log('First few chart data points:', chartData.slice(0, 5));
    
    // Use standardized x-axis range from Garmin activity data
    const startTime = garminStartTime;
    const endTime = garminEndTime;
    
    console.log('Using standardized activity start time:', startTime);
    console.log('Using standardized activity end time:', endTime);
    
    // Calculate activity duration and determine smart tick intervals
    const activityDurationMs = endTime.getTime() - startTime.getTime();
    const activityDurationMinutes = activityDurationMs / (1000 * 60);
    
    // Define possible tick intervals in minutes
    const possibleIntervals = [0.5, 1, 5, 15, 30, 60, 120, 300, 600]; // 30s, 1m, 5m, 15m, 30m, 1h, 2h, 5h, 10h
    
    // Find the optimal interval that gives us ≤ 23 ticks
    let optimalInterval = 1; // Default to 1 minute
    for (let i = 0; i < possibleIntervals.length; i++) {
        const interval = possibleIntervals[i];
        const numTicks = Math.ceil(activityDurationMinutes / interval) + 1; // +1 for the start tick
        if (numTicks <= 23) {
            optimalInterval = interval;
            break;
        }
    }
    
    // Generate custom tick positions at round intervals from start
    const customTicks = [];
    let currentTime = 0; // Start at 0 minutes
    while (currentTime <= activityDurationMinutes) {
        customTicks.push(new Date(startTime.getTime() + (currentTime * 60 * 1000)));
        currentTime += optimalInterval;
    }
    
    console.log('Activity duration:', activityDurationMinutes.toFixed(1), 'minutes');
    console.log('Using tick interval:', optimalInterval, 'minutes');
    console.log('Number of ticks:', customTicks.length);
    
    // Helper function to format time based on interval
    function formatTickLabel(timestamp) {
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
    
    console.log('Custom tick positions:', customTicks.map(t => formatTickLabel(t)));
    
    // Shared function to create afterBuildTicks for consistent gridlines
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
    
    // Small delay to ensure DOM is ready and chart element is properly set up
    setTimeout(() => {
        // Re-get the chart element and context after the delay to ensure they're still valid
        const chartElement = document.getElementById('activityHrChart');
        if (!chartElement) {
            console.error('Activity chart element not found after delay');
            return;
        }
        
        const ctx = chartElement.getContext('2d');
        if (!ctx) {
            console.error('Could not get 2D context for activity chart after delay');
            return;
        }
        
        // Create datasets array
        const datasets = [
            // Single background dataset with gradient
            {
                label: 'Background',
                data: chartLabels.map(timestamp => ({ x: timestamp, y: 160 })), // Full height background
                borderColor: 'transparent',
                backgroundColor: function(context) {
                    const chart = context.chart;
                    const {ctx, chartArea} = chart;
                    
                    if (!chartArea) {
                        return 'transparent';
                    }
                    
                    // Create gradient
                    const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
                    
                                         // Add color stops for each zone
                     gradient.addColorStop(0, '#e74c3c'); // 160+ Red
                     gradient.addColorStop(1/12, '#e74c3c'); // 150-159 Red
                     gradient.addColorStop(1/12, '#fd7e14'); // 150-159 Orange
                     gradient.addColorStop(1/6, '#fd7e14'); // 140-149 Orange
                     gradient.addColorStop(1/6, '#ffc107'); // 140-149 Yellow
                     gradient.addColorStop(3/12, '#ffc107'); // 130-139 Yellow
                     gradient.addColorStop(3/12, '#9acd32'); // 130-139 Yellow-green
                     gradient.addColorStop(1/3, '#9acd32'); // 120-129 Yellow-green
                     gradient.addColorStop(1/3, '#28a745'); // 120-129 Green
                     gradient.addColorStop(5/12, '#28a745'); // 110-119 Green
                     gradient.addColorStop(5/12, '#006d5b'); // 110-119 Deep teal
                     gradient.addColorStop(1/2, '#006d5b'); // 100-109 Deep teal
                     gradient.addColorStop(1/2, '#004080'); // 100-109 Night sky blue
                     gradient.addColorStop(7/12, '#004080'); // 90-99 Night sky blue
                     gradient.addColorStop(7/12, '#002040'); // 80-89 Midnight
                     gradient.addColorStop(2/3, '#002040'); // 80-89 Midnight
                     gradient.addColorStop(2/3, '#000000'); // 80-89 Black
                     gradient.addColorStop(1, '#000000'); // Below 80 Black
                     
                     return gradient;
                 },
                 borderWidth: 0,
                 fill: true,
                 tension: 0,
                 pointRadius: 0,
                 order: 2
             },
             // Heart rate line on top
             {
                 label: 'Heart Rate (BPM)',
                 data: chartLabels.map((timestamp, index) => ({ x: timestamp, y: chartData[index] })),
                 borderColor: '#e74c3c',
                 backgroundColor: 'transparent',
                 borderWidth: 2,
                 fill: false,
                 tension: 0.1,
                 pointRadius: 0,
                 pointHoverRadius: 4,
                 pointHoverBackgroundColor: '#e74c3c',
                 order: 0,
                 yAxisID: 'y'
             },
             // Dummy alert dataset to match SpO2 chart area calculation
             {
                 label: 'Dummy Alerts',
                 data: [{ x: startTime, y: 40 }],
                 borderColor: '#002040',
                 backgroundColor: '#002040',
                 borderWidth: 0,
                 fill: false,
                 tension: 0.1,
                 pointRadius: 4,
                 pointHoverRadius: 6,
                 pointHoverBackgroundColor: '#002040',
                 order: 1
             }
        ];
        
        // Breathing data removed from scope for alignment consistency
        // SpO2 is now in separate chart
        console.log('SpO2 data available for activity:', activity.spo2_values ? activity.spo2_values.length : 0, 'points');
        
        // Create the chart
        activityHrChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: chartLabels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                spanGaps: false, // Don't draw lines across gaps
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'nearest',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                // Get the raw timestamp from the data point
                                const rawData = context[0].raw;
                                if (rawData && rawData.x) {
                                    const timestamp = new Date(rawData.x);
                                    const timeSinceStart = timestamp.getTime() - startTime.getTime();
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
                                // Fallback to the label if raw data not available
                                return `Time: ${context[0].label}`;
                            },
                            label: function(context) {
                                // Show tooltip for heart rate data only
                                if (context.dataset.label === 'Heart Rate (BPM)') {
                                    return `Heart Rate: ${context.parsed.y} BPM`;
                                }
                                return null; // Hide background dataset from tooltip
                            }
                        }
                    },
                    datalabels: {
                        display: false,
                        formatter: function() {
                            return ''; // Return empty string to ensure no labels
                        }
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
                        title: {
                            display: true,
                            text: 'Time Since Activity Start'
                        },
                        min: startTime,
                        max: endTime,
                        ticks: {
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
                        time: {
                            unit: 'minute',
                            displayFormats: {
                                minute: 'mm:ss',
                                second: 'mm:ss'
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.3)', // Even darker for visibility
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
                            text: 'Heart Rate (BPM)'
                        },
                        min: 40,
                        max: 160,
                        ticks: {
                            stepSize: 20
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
        
        console.log('Activity chart created successfully:', activityHrChart);
        console.log('Activity chart dimensions after creation:', chartElement.offsetWidth, 'x', chartElement.offsetHeight);
        
        // Create SpO2 chart if data exists (using standardized range and gridlines)
        createActivitySpo2Chart(activity, spo2Data, spo2Alerts, 'activitySpo2Chart', 'activitySpo2ChartContainer', garminStartTime, garminEndTime, optimalInterval, activityDurationMinutes);
        
        // Load SpO2 distribution data if SpO2 data exists
        if (spo2Data && spo2Data.length > 0) {
            loadActivitySpo2Distribution(activity.activity_id);
        } else {
            hideActivitySpo2DistributionCharts();
        }
        
        // Create breathing chart if data exists (using standardized range and gridlines)
        createActivityBreathingChart(activity, breathingData, 'activityBreathingChart', 'activityBreathingChartContainer', garminStartTime, garminEndTime, optimalInterval, activityDurationMinutes);
    }, 100);
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
