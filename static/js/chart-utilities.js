/**
 * Chart Utilities and Configuration
 * 
 * Shared chart configuration, colors, and utility functions
 * used across dashboard pages.
 */

// TRIMP zone colors (9 zones)
const zoneColors = {
    '80-89': '#002040',    // Midnight
    '90-99': '#004080',    // Night sky blue
    '100-109': '#006d5b',  // Deep teal
    '110-119': '#28a745',  // Green
    '120-129': '#9acd32',  // Yellow-green
    '130-139': '#ffc107',  // Yellow
    '140-149': '#fd7e14',  // Orange
    '150-159': '#e74c3c',  // Red
    '160+': '#dc3545'      // Hot red
};

// SpO2 zone colors for distribution charts
const spo2ZoneColors = {
    '80-82.5': '#dc3545',   // Hot red
    '82.5-85': '#dc3545',   // Hot red
    '85-87.5': '#e74c3c',   // Red
    '87.5-90': '#fd7e14',   // Orange
    '90-92.5': '#ffc107',   // Yellow
    '92.5-95': '#9acd32',   // Yellow-green
    '95-97.5': '#28a745',   // Green
    '97.5-100': '#28a745'   // Green
};

// Oxygen debt zone colors (3 zones)
const oxygenDebtColors = {
    'Below 95': '#9acd32',  // Yellow-green
    'Below 90': '#fd7e14',  // Orange  
    'Below 88': '#e74c3c'   // Red
};

// Zone order for stacking (bottom to top)
const zoneOrder = [
    '80-89',
    '90-99',
    '100-109', 
    '110-119',
    '120-129',
    '130-139',
    '140-149',
    '150-159',
    '160+'
];

// Oxygen debt zone order for consistent display (bottom to top in stacked bars)
const oxygenDebtZoneOrder = ['Below 95', 'Below 90', 'Below 88'];

/**
 * Calculate appropriate step size and axis maximum for charts
 * Uses Chart.js-like logic for nice number intervals
 * 
 * @param {number} maxValue - Maximum value in the data
 * @param {boolean} addExtraStep - Whether to add extra step for label space (true for Y-axis, false for X-axis)
 * @param {number} minConstraint - Minimum axis value (optional)
 * @returns {object} - {step, axisMax}
 */
function calculateAxisScaling(maxValue, addExtraStep = false, minConstraint = null) {
    if (maxValue === 0) {
        const defaultMax = minConstraint || 10;
        return { step: 10, axisMax: defaultMax };
    }
    
    // Unified step size logic - uses the perfected oxygen debt logic that handles all ranges
    let step;
    if (maxValue <= 1000) step = 100;        // 497 → 100, 809 → 100
    else if (maxValue <= 2000) step = 200;   // 1113 → 200
    else if (maxValue <= 5000) step = 500;
    else if (maxValue <= 10000) step = 1000;
    else if (maxValue <= 20000) step = 2000;
    else if (maxValue <= 50000) step = 5000;
    else if (maxValue <= 70000) step = 10000; // 65091 → 10000
    else if (maxValue <= 150000) step = 20000; // 93739 → 20000
    else if (maxValue <= 400000) step = 50000; // 191404 → 50000
    else step = 100000;
    
    // Round up to next tick boundary
    let axisMax = Math.ceil(maxValue / step) * step;
    
    // Add extra step for label space if requested (Y-axis charts)
    if (addExtraStep) {
        axisMax += step;
    }
    
    // Apply minimum constraint if specified
    if (minConstraint) {
        axisMax = Math.max(axisMax, minConstraint);
    }
    
    return { step, axisMax };
}

/**
 * Calculate axis maximum with minimum constraint
 * Used for activities charts that need a minimum axis size
 * 
 * @param {number} maxValue - Maximum value in the data
 * @param {number} minConstraint - Minimum axis value (default 100)
 * @returns {number} - Calculated axis maximum
 */
function calculateAxisMaxWithMinimum(maxValue, minConstraint = 100) {
    if (maxValue === 0) {
        return minConstraint;
    }
    
    const { axisMax } = calculateAxisScaling(maxValue, false);
    return Math.max(axisMax, minConstraint);
}

/**
 * Get chart title based on metric type
 * 
 * @param {string} metric - Current metric ('trimp', 'minutes', 'area')
 * @returns {string} - Appropriate chart title
 */
function getChartTitle(metric) {
    switch (metric) {
        case 'trimp': return 'TRIMP Score';
        case 'area': return 'Oxygen Debt Area';
        case 'minutes': return 'Minutes';
        default: return 'Value';
    }
}

/**
 * Common chart options for consistent styling
 */
const commonChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top',
            labels: {
                usePointStyle: true,
                padding: 20
            }
        }
    }
};

/**
 * Common stacked bar chart options
 */
const stackedBarOptions = {
    ...commonChartOptions,
    scales: {
        x: {
            stacked: true
        },
        y: {
            stacked: true,
            beginAtZero: true
        }
    }
};

/**
 * Common horizontal bar chart options
 */
const horizontalBarOptions = {
    ...commonChartOptions,
    indexAxis: 'y',
    scales: {
        x: {
            stacked: true,
            beginAtZero: true
        },
        y: {
            stacked: true
        }
    }
};

/**
 * Create zoned datasets for stacked bar charts
 * Used by all TRIMP and oxygen debt charts for consistent colored bar creation
 * 
 * @param {string[]} zones - Array of zone names (e.g., zoneOrder or oxygenDebtZoneOrder)
 * @param {object} colors - Color mapping object (e.g., zoneColors or oxygenDebtColors)
 * @param {function} dataExtractor - Function that takes a zone and returns data array
 * @param {object} options - Additional dataset options (e.g., {stack: 'activities'})
 * @returns {Array} - Chart.js datasets array with proper colors and structure
 */
function createZonedDatasets(zones, colors, dataExtractor, options = {}) {
    return zones.map(zone => ({
        label: zone,
        data: dataExtractor(zone),
        backgroundColor: colors[zone] || '#6c757d',
        borderColor: colors[zone] || '#6c757d',
        borderWidth: 1,
        ...options
    }));
}
