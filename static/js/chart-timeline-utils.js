/**
 * Chart Timeline Utilities
 * 
 * Shared timeline generation functions for consistent x-axis handling
 * across all time series charts (HR, SpO2, breathing).
 */

/**
 * Generate 24-hour timeline for daily charts
 * Creates evenly spaced timeline from 00:00 to 23:59 (1440 minutes)
 * 
 * @param {string} dateLabel - Date in YYYY-MM-DD format
 * @returns {object} - {labels: Date[], chartDate: Date}
 */
function generate24HourTimeline(dateLabel) {
    const chartDate = new Date(dateLabel + 'T00:00:00');
    const labels = [];
    
    // Create evenly spaced 24-hour timeline (every 1 minute for high resolution)
    for (let hour = 0; hour < 24; hour++) {
        for (let minute = 0; minute < 60; minute += 1) {
            const timestamp = new Date(chartDate);
            timestamp.setHours(hour, minute, 0, 0);
            labels.push(timestamp);
        }
    }
    
    return { labels, chartDate };
}

/**
 * Generate activity timeline for activity charts
 * Creates timeline spanning the activity duration with optimal intervals
 * 
 * @param {Date} startTime - Activity start time
 * @param {Date} endTime - Activity end time
 * @param {number} activityDurationMinutes - Total activity duration
 * @returns {object} - {labels: Date[], optimalInterval: number}
 */
function generateActivityTimeline(startTime, endTime, activityDurationMinutes) {
    // Calculate optimal interval based on activity duration
    let optimalInterval;
    if (activityDurationMinutes <= 30) {
        optimalInterval = 0.5; // 30 seconds for short activities
    } else if (activityDurationMinutes <= 90) {
        optimalInterval = 1; // 1 minute for medium activities
    } else if (activityDurationMinutes <= 300) {
        optimalInterval = 5; // 5 minutes for longer activities
    } else {
        optimalInterval = 10; // 10 minutes for very long activities
    }
    
    // Create simplified timeline for chart area alignment
    const labels = [startTime, endTime];
    
    return { labels, optimalInterval };
}

/**
 * Create afterBuildTicks function for consistent gridlines
 * Used by activity charts to ensure aligned gridlines across HR, SpO2, and breathing
 * 
 * @param {Date} startTime - Activity start time
 * @param {number} optimalInterval - Interval in minutes
 * @param {number} activityDurationMinutes - Total duration
 * @returns {Function} - afterBuildTicks function for Chart.js
 */
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

/**
 * Map data points to timeline for daily charts
 * Maps time series data to 24-hour timeline with null for missing minutes
 * 
 * @param {Array} timeSeriesData - Array of [timestamp, value] pairs
 * @param {Date[]} timeline - 24-hour timeline array
 * @param {Date} chartDate - Base date for the chart
 * @returns {Array} - Data array aligned to timeline
 */
function mapDataToTimeline(timeSeriesData, timeline, chartDate) {
    const data = new Array(timeline.length).fill(null);
    
    timeSeriesData.forEach(point => {
        let timestamp, value;
        
        if (Array.isArray(point)) {
            [timestamp, value] = point;
        } else {
            timestamp = point.timestamp;
            value = point.value;
        }
        
        const pointDate = new Date(timestamp);
        const minutesFromStart = pointDate.getHours() * 60 + pointDate.getMinutes();
        
        if (minutesFromStart >= 0 && minutesFromStart < timeline.length) {
            data[minutesFromStart] = value;
        }
    });
    
    return data;
}
