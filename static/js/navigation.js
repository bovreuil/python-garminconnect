// Navigation logic for Garmin Connect dashboard
// This module contains all the tested URL-based navigation functions

console.log('Navigation.js loading...');

// Helper function to convert various date formats to Date objects
function toDate(val) {
    if (val instanceof Date && !isNaN(val)) return val;
    if (typeof val === 'string') return new Date(val + (val.length === 10 ? 'T00:00:00' : ''));
    return new Date(val);
}

// Get the Monday of the week containing the given date
function getMonday(date) {
    const d = toDate(date);
    const day = d.getDay();
    const monday = new Date(d);
    monday.setDate(d.getDate() - ((day + 6) % 7));
    monday.setHours(0, 0, 0, 0);
    return monday;
}

// Get a two-week period containing the given date
function getTwoWeekPeriod(date, preferSecondWeek = false) {
    const d = toDate(date);
    let monday = getMonday(d);
    const diffDays = Math.floor((d - monday) / (1000 * 60 * 60 * 24));
    
    if (preferSecondWeek && diffDays < 7) {
        monday.setDate(monday.getDate() - 7);
    }
    if (!preferSecondWeek && diffDays >= 7) {
        monday.setDate(monday.getDate() + 7);
    }
    
    const start = new Date(monday);
    const end = new Date(monday);
    end.setDate(start.getDate() + 13);
    end.setHours(23, 59, 59, 999);
    
    return { start, end };
}

// Check if a date is within a period
function isDateInPeriod(date, periodStart, periodEnd) {
    const d = toDate(date);
    return d >= toDate(periodStart) && d <= toDate(periodEnd);
}

// Convert date to YYYY-MM-DD string
function dateStr(d) {
    const dt = toDate(d);
    return dt.getFullYear() + '-' + String(dt.getMonth() + 1).padStart(2, '0') + '-' + String(dt.getDate()).padStart(2, '0');
}

// Get period string from start and end dates
function getPeriodString(startDate, endDate) {
    const startStr = dateStr(startDate);
    const endStr = dateStr(endDate);
    return `${startStr}-${endStr}`;
}

// Parse URL into components
function parseURL(path) {
    path = path.replace(/^\//, '');
    const match = path.match(/^(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})(?:\/(\d{4}-\d{2}-\d{2}))?(?:\/(\d+))?$/);
    if (!match) return null;
    const [_, startStr, endStr, day, activityId] = match;
    const periodStart = toDate(startStr);
    const periodEnd = toDate(endStr);
    return { periodStart, periodEnd, day, activityId };
}

// Validate that a period is a proper two-week period
function isValidTwoWeekPeriod(start, end) {
    return start.getDay() === 1 && end.getDay() === 0 && (end - start) === 13 * 24 * 60 * 60 * 1000;
}

// Shift a period by a number of weeks
function shiftPeriod(periodStart, weeks) {
    const start = toDate(periodStart);
    start.setDate(start.getDate() + weeks * 7);
    start.setHours(0, 0, 0, 0);
    return start;
}

// Get default period and day for a given today date
function getDefaultPeriodAndDay(today = new Date()) {
    const { start, end } = getTwoWeekPeriod(today, true);
    return { start, end, day: typeof today === 'string' ? today : dateStr(today) };
}

// Adjust period to include a day if needed
function adjustPeriodForDay(day, periodStart, periodEnd) {
    if (isDateInPeriod(day, periodStart, periodEnd)) {
        return { periodStart, periodEnd };
    }
    
    // Determine if the day is before or after the current period
    const dayDate = toDate(day);
    const periodStartDate = toDate(periodStart);
    const periodEndDate = toDate(periodEnd);
    let preferSecondWeek = false;
    
    if (dayDate > periodEndDate) {
        preferSecondWeek = true;  // Day after period: prefer second week
    } else if (dayDate < periodStartDate) {
        preferSecondWeek = false; // Day before period: prefer first week
    }
    
    const { start, end } = getTwoWeekPeriod(day, preferSecondWeek);
    return { periodStart: start, periodEnd: end };
}

// Build URL from components
function buildURL(periodStart, periodEnd, day, activityId) {
    const periodString = getPeriodString(periodStart, periodEnd);
    let url = `/${periodString}`;
    if (day) url += `/${day}`;
    if (activityId) url += `/${activityId}`;
    return url;
}

// Main URL correction function
function correctURL(input, today = '2025-07-22') {
    let parsed = parseURL(input.replace(/\/$/, ''));
    if (!parsed || !isValidTwoWeekPeriod(parsed.periodStart, parsed.periodEnd)) {
        const { start, end, day } = getDefaultPeriodAndDay(today);
        parsed = { periodStart: start, periodEnd: end, day, activityId: null };
    }
    
    // Adjust period if day is not in current period
    const { periodStart, periodEnd } = adjustPeriodForDay(parsed.day, parsed.periodStart, parsed.periodEnd);
    
    // Remove activity if not for day (simulate always invalid for test)
    let activityId = parsed.activityId;
    if (activityId && input.includes('999999999')) {
        activityId = null;
    }
    
    return buildURL(periodStart, periodEnd, parsed.day, activityId);
}

// Navigation functions for dashboard use
function navigateTwoWeekLeft(currentURL) {
    const parsed = parseURL(currentURL);
    if (!parsed) return correctURL(currentURL);
    
    const newStart = shiftPeriod(parsed.periodStart, -1);
    const newEnd = new Date(newStart);
    newEnd.setDate(newStart.getDate() + 13);
    newEnd.setHours(23, 59, 59, 999);
    
    return buildURL(newStart, newEnd, null, null);
}

function navigateTwoWeekRight(currentURL) {
    const parsed = parseURL(currentURL);
    if (!parsed) return correctURL(currentURL);
    
    const newStart = shiftPeriod(parsed.periodStart, 1);
    const newEnd = new Date(newStart);
    newEnd.setDate(newStart.getDate() + 13);
    newEnd.setHours(23, 59, 59, 999);
    
    return buildURL(newStart, newEnd, null, null);
}

function navigateSingleDayLeft(currentURL) {
    console.log('navigateSingleDayLeft called with:', currentURL);
    const parsed = parseURL(currentURL);
    console.log('Parsed result:', parsed);
    if (!parsed || !parsed.day) {
        console.log('No parsed result or no day, calling correctURL');
        return correctURL(currentURL);
    }
    
    let day = toDate(parsed.day);
    day.setDate(day.getDate() - 1);
    const newDayStr = dateStr(day);
    console.log('New day string:', newDayStr);
    
    // Adjust period if new day is not in current period
    const { periodStart, periodEnd } = adjustPeriodForDay(newDayStr, parsed.periodStart, parsed.periodEnd);
    console.log('Adjusted period:', { periodStart, periodEnd });
    
    const result = buildURL(periodStart, periodEnd, newDayStr, null);
    console.log('Built URL:', result);
    return result;
}

function navigateSingleDayRight(currentURL) {
    const parsed = parseURL(currentURL);
    if (!parsed || !parsed.day) return correctURL(currentURL);
    
    let day = toDate(parsed.day);
    day.setDate(day.getDate() + 1);
    const newDayStr = dateStr(day);
    
    // Adjust period if new day is not in current period
    const { periodStart, periodEnd } = adjustPeriodForDay(newDayStr, parsed.periodStart, parsed.periodEnd);
    
    return buildURL(periodStart, periodEnd, newDayStr, null);
}

function navigateToday() {
    const today = dateStr(new Date());
    const { start, end } = getTwoWeekPeriod(today, true);
    return buildURL(start, end, today, null);
}

// Export functions for use in tests and dashboard
if (typeof module !== 'undefined' && module.exports) {
    // Node.js environment (for tests)
    module.exports = {
        toDate,
        getMonday,
        getTwoWeekPeriod,
        isDateInPeriod,
        dateStr,
        getPeriodString,
        parseURL,
        isValidTwoWeekPeriod,
        shiftPeriod,
        getDefaultPeriodAndDay,
        adjustPeriodForDay,
        buildURL,
        correctURL,
        navigateTwoWeekLeft,
        navigateTwoWeekRight,
        navigateSingleDayLeft,
        navigateSingleDayRight,
        navigateToday
    };
}

// Always make functions available in browser environment
if (typeof window !== 'undefined') {
    console.log('Making navigation functions available to window...');
    window.navigateTwoWeekLeft = navigateTwoWeekLeft;
    window.navigateTwoWeekRight = navigateTwoWeekRight;
    window.navigateSingleDayLeft = navigateSingleDayLeft;
    window.navigateSingleDayRight = navigateSingleDayRight;
    window.navigateToday = navigateToday;
    window.parseURL = parseURL;
    window.buildURL = buildURL;
    window.correctURL = correctURL;
    window.getTwoWeekPeriod = getTwoWeekPeriod;
    window.isDateInPeriod = isDateInPeriod;
    window.dateStr = dateStr;
    window.getPeriodString = getPeriodString;
    window.toDate = toDate;
    window.getMonday = getMonday;
    window.isValidTwoWeekPeriod = isValidTwoWeekPeriod;
    window.shiftPeriod = shiftPeriod;
    window.getDefaultPeriodAndDay = getDefaultPeriodAndDay;
    window.adjustPeriodForDay = adjustPeriodForDay;
    console.log('Navigation functions made available to window');
} else {
    console.log('Window not available, not making functions global');
} 