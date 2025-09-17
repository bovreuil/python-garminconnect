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
