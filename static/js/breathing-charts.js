/**
 * Breathing Chart Functions
 * 
 * Chart creation functions for breathing rate time series data.
 * Handles activity-level breathing data visualization.
 */

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
