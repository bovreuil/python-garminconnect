/**
 * Time Series Extractors
 *
 * Clean, reusable functions for extracting time series data from raw data objects.
 * Separates data extraction logic from visualization concerns.
 *
 * Data Types Produced:
 * - Day HR Series: [[timestamp, hr_value], ...]
 * - Activity HR Series: [[timestamp, hr_value], ...]
 * - Day SpO2 Series: [[timestamp, spo2_value], ...]
 * - Activity SpO2 Series: [[timestamp, spo2_value], ...]
 * - Activity Breathing Series: [[timestamp, breathing_value], ...]
 *
 * All timestamps are JavaScript Date objects or millisecond timestamps.
 * All series are sorted by timestamp in ascending order.
 */

/**
 * Extract day HR time series from daily data
 * Returns standardized format: [[timestamp, hr_value], ...]
 *
 * @param {Object} dayData - Daily data object from API
 * @returns {Array} Array of [timestamp, hr_value] pairs, sorted by timestamp
 */
function getDayHRTimeSeries(dayData) {
    if (!dayData || !dayData.heart_rate_values) {
        return [];
    }

    // dayData.heart_rate_values is already in [[timestamp, hr_value], ...] forma
    const hrSeries = dayData.heart_rate_values;

    if (!Array.isArray(hrSeries) || hrSeries.length === 0) {
        return [];
    }

    // Filter out null/invalid values and ensure proper forma
    const cleanSeries = hrSeries
        .filter(point => {
            return Array.isArray(point) &&
                   point.length >= 2 &&
                   point[0] != null &&
                   point[1] != null &&
                   typeof point[1] === 'number' &&
                   point[1] > 0;
        })
        .map(point => [point[0], point[1]]); // Ensure [timestamp, value] forma

    // Sort by timestamp (ascending)
    cleanSeries.sort((a, b) => a[0] - b[0]);

    return cleanSeries;
}

/**
 * Extract activity HR time series from activity data
 * Returns standardized format: [[timestamp, hr_value], ...]
 *
 * @param {Object} activity - Activity data object from API
 * @returns {Array} Array of [timestamp, hr_value] pairs, sorted by timestamp
 */
function getActivityHRTimeSeries(activity) {
    if (!activity || !activity.heart_rate_values) {
        return [];
    }

    let hrSeries = activity.heart_rate_values;

    if (!Array.isArray(hrSeries) || hrSeries.length === 0) {
        return [];
    }

    // Handle different data formats that might exis
    const cleanSeries = hrSeries
        .filter(point => {
            if (Array.isArray(point)) {
                // Format: [timestamp, hr_value]
                return point.length >= 2 &&
                       point[0] != null &&
                       point[1] != null &&
                       typeof point[1] === 'number' &&
                       point[1] > 0;
            } else if (typeof point === 'object' && point !== null) {
                // Format: {timestamp: x, value: y} or {x: timestamp, y: value}
                const timestamp = point.timestamp || point.x;
                const value = point.value || point.y;
                return timestamp != null &&
                       value != null &&
                       typeof value === 'number' &&
                       value > 0;
            }
            return false;
        })
        .map(point => {
            if (Array.isArray(point)) {
                return [point[0], point[1]];
            } else {
                // Convert object format to [timestamp, value]
                const timestamp = point.timestamp || point.x;
                const value = point.value || point.y;
                return [timestamp, value];
            }
        });

    // Sort by timestamp (ascending)
    cleanSeries.sort((a, b) => a[0] - b[0]);

    return cleanSeries;
}

/**
 * Extract day SpO2 time series from daily data
 * Returns standardized format: [[timestamp, spo2_value], ...]
 *
 * @param {Object} dayData - Daily data object from API
 * @returns {Array} Array of [timestamp, spo2_value] pairs, sorted by timestamp
 */
function getDaySpO2TimeSeries(dayData) {
    if (!dayData || !dayData.spo2_values) {
        return [];
    }

    const spo2Series = dayData.spo2_values;

    if (!Array.isArray(spo2Series) || spo2Series.length === 0) {
        return [];
    }

    // spo2_values format: [[timestamp, spo2_value, spo2_reminder], ...]
    // We only need timestamp and spo2_value
    const cleanSeries = spo2Series
        .filter(point => {
            return Array.isArray(point) &&
                   point.length >= 2 &&
                   point[0] != null &&
                   point[1] != null &&
                   typeof point[1] === 'number' &&
                   point[1] >= 0 &&
                   point[1] <= 100;
        })
        .map(point => [point[0], point[1]]); // Extract [timestamp, spo2_value]

    // Sort by timestamp (ascending)
    cleanSeries.sort((a, b) => a[0] - b[0]);

    return cleanSeries;
}

/**
 * Extract activity SpO2 time series from activity data
 * Returns standardized format: [[timestamp, spo2_value], ...]
 *
 * @param {Object} activity - Activity data object from API
 * @returns {Array} Array of [timestamp, spo2_value] pairs, sorted by timestamp
 */
function getActivitySpO2TimeSeries(activity) {
    if (!activity) {
        return [];
    }

    // Activity SpO2 can come from two sources:
    // 1. activity.spo2_values (manual SpO2 entries)
    // 2. activity.o2ring_data (O2Ring data filtered to activity period)

    let spo2Series = [];

    // Check for manual SpO2 entries firs
    if (activity.spo2_values && Array.isArray(activity.spo2_values)) {
        spo2Series = activity.spo2_values;
    }
    // Fallback to O2Ring data if no manual entries
    else if (activity.o2ring_data && Array.isArray(activity.o2ring_data)) {
        spo2Series = activity.o2ring_data;
    }

    if (spo2Series.length === 0) {
        return [];
    }

    // Handle different SpO2 data formats
    const cleanSeries = spo2Series
        .filter(point => {
            if (Array.isArray(point)) {
                // Format: [timestamp, spo2_value] or [timestamp, spo2_value, reminder]
                return point.length >= 2 &&
                       point[0] != null &&
                       point[1] != null &&
                       typeof point[1] === 'number' &&
                       point[1] >= 0 &&
                       point[1] <= 100;
            }
            return false;
        })
        .map(point => [point[0], point[1]]); // Extract [timestamp, spo2_value]

    // Sort by timestamp (ascending)
    cleanSeries.sort((a, b) => a[0] - b[0]);

    return cleanSeries;
}

/**
 * Extract activity breathing time series from activity data
 * Returns standardized format: [[timestamp, breathing_value], ...]
 *
 * @param {Object} activity - Activity data object from API
 * @returns {Array} Array of [timestamp, breathing_value] pairs, sorted by timestamp
 */
function getActivityBreathingTimeSeries(activity) {
    if (!activity || !activity.breathing_rate_values) {
        return [];
    }

    const breathingSeries = activity.breathing_rate_values;

    if (!Array.isArray(breathingSeries) || breathingSeries.length === 0) {
        return [];
    }

    // breathing_rate_values format: [[timestamp, breathing_value], ...]
    const cleanSeries = breathingSeries
        .filter(point => {
            return Array.isArray(point) &&
                   point.length >= 2 &&
                   point[0] != null &&
                   point[1] != null &&
                   typeof point[1] === 'number' &&
                   point[1] > 0;
        })
        .map(point => [point[0], point[1]]); // Ensure [timestamp, value] forma

    // Sort by timestamp (ascending)
    cleanSeries.sort((a, b) => a[0] - b[0]);

    return cleanSeries;
}
