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
 * @param {string} dateLabel - Date in YYYY-MM-DD forma
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

    // Create simplified timeline for chart area alignmen
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
 * @param {Date} chartDate - Base date for the char
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

/**
 * Create HR zone background dataset for time series charts
 * Creates the TRIMP zone colored background (160+ red to 80- black)
 *
 * @param {Date[]} timeline - Timeline array (24-hour or activity duration)
 * @returns {object} - Chart.js dataset object for HR zone background
 */
function createHRTimeSeriesBackground(timeline) {
    return {
        label: 'HR Zone Background',
        data: [
            { x: timeline[0], y: 160 },
            { x: timeline[timeline.length - 1], y: 160 }
        ],
        borderColor: 'transparent',
        backgroundColor: function(context) {
            const chart = context.chart;
            const {ctx, chartArea} = chart;

            if (!chartArea) {
                return 'transparent';
            }

            // Create HR zone gradient (TRIMP zones: 160+ to 80-89)
            const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
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
            gradient.addColorStop(7/12, '#002040'); // 80-89 Midnigh
            gradient.addColorStop(2/3, '#002040'); // 80-89 Midnigh
            gradient.addColorStop(2/3, '#000000'); // 80-89 Black
            gradient.addColorStop(1, '#000000'); // Below 80 Black

            return gradient;
        },
        borderWidth: 0,
        fill: true,
        tension: 0,
        pointRadius: 0,
        order: 100 // Behind all other datasets
    };
}

/**
 * Create SpO2 zone background dataset for time series charts
 * Creates the SpO2 zone colored background (98% green to 81% red)
 *
 * @param {Date[]} timeline - Timeline array (24-hour or activity duration)
 * @returns {object} - Chart.js dataset object for SpO2 zone background
 */
function createSpO2TimeSeriesBackground(timeline) {
    return {
        label: 'SpO2 Zone Background',
        data: [
            { x: timeline[0], y: 100 },
            { x: timeline[timeline.length - 1], y: 100 }
        ],
        borderColor: 'transparent',
        backgroundColor: function(context) {
            const chart = context.chart;
            const {ctx, chartArea} = chart;

            if (!chartArea) {
                return 'transparent';
            }

            // Create SpO2 zone gradient (98% to 81%)
            const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
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
        order: 100 // Behind all other datasets
    };
}
