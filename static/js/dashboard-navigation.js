/**
 * Dashboard Navigation and Utility Functions
 *
 * Common functions used across dashboard pages for navigation,
 * date calculations, and utility operations.
 */

// Calculate two-week period with target date in the second week
function calculateTwoWeekPeriod(targetDate, preferSecondWeek = true) {
    const startDate = new Date(targetDate);
    const endDate = new Date(targetDate);

    if (preferSecondWeek) {
        // Put the target date in the second week
        // Calculate the Monday of the target date's week
        const targetMonday = getWeekStart(targetDate);

        // The two-week period starts one week before this Monday
        startDate.setTime(targetMonday.getTime() - (7 * 24 * 60 * 60 * 1000));

        // The two-week period ends on the Sunday of the target date's week
        endDate.setTime(targetMonday.getTime() + (6 * 24 * 60 * 60 * 1000));
    } else {
        // Put the target date in the first week (original behavior)
        const endOfWeek = new Date(targetDate);
        endOfWeek.setDate(targetDate.getDate() + (6 - targetDate.getDay()));

        const startOfTwoWeeks = new Date(endOfWeek);
        startOfTwoWeeks.setDate(endOfWeek.getDate() - 13);

        startDate.setTime(startOfTwoWeeks.getTime());
        endDate.setTime(endOfWeek.getTime());
    }

    return { startDate, endDate };
}

// Navigate by one week
function navigateWeek(direction) {
    if (!currentStartDate || !currentEndDate) return;

    // Close single date view and single activity view when navigating
    closeSingleDateView();
    closeSingleActivityView();

    // Calculate new start and end dates
    const newStartDate = new Date(currentStartDate);
    const newEndDate = new Date(currentEndDate);
    newStartDate.setDate(currentStartDate.getDate() + (direction * 7));
    newEndDate.setDate(currentEndDate.getDate() + (direction * 7));

    loadTwoWeekData(newStartDate, newEndDate);
}

// Go to today's two-week period
function goToToday() {
    // Close single date view and single activity view when going to today
    closeSingleDateView();
    closeSingleActivityView();

    const today = new Date();
    const { startDate, endDate } = calculateTwoWeekPeriod(today);

    loadTwoWeekData(startDate, endDate);

    // Also open single day view for today
    const todayString = today.toISOString().split('T')[0];
    loadDateData(todayString).then(dayData => {
        showSingleDateView(todayString, dayData);
    });
}

// Navigate single day left or righ
function navigateSingleDay(direction) {
    if (!selectedDate) {
        return;
    }

    // Close single activity view when navigating
    closeSingleActivityView();

    // Convert selectedDate string to Date objec
    const currentDate = new Date(selectedDate + 'T00:00:00');
    const newDate = new Date(currentDate);
    newDate.setDate(currentDate.getDate() + direction);

    // Check if the new date is outside the current period
    if (currentStartDate && currentEndDate) {
        if (newDate < currentStartDate || newDate > currentEndDate) {
            // Need to adjust the period
            // When going left (direction < 0): prefer first week to see more past dates
            // When going right (direction > 0): prefer second week to see more future dates
            const preferSecondWeek = direction > 0;
            const { startDate, endDate } = calculateTwoWeekPeriod(newDate, preferSecondWeek);
            loadTwoWeekData(startDate, endDate);
        }
    }

    // Show the single day view for the new date
    setTimeout(() => {
        loadDateData(formatDateForAPI(newDate)).then(dayData => {
            // Always show the single day view, even if there's no data
            showSingleDateView(formatDateForAPI(newDate), dayData);
        });
    }, 500);
}

// Go to today from single date view
function goToSingleDateToday() {
    // Close single activity view when going to today
    closeSingleActivityView();

    const today = new Date();
    const todayString = today.toISOString().split('T')[0];

    // Check if the new date is outside the current period
    if (currentStartDate && currentEndDate) {
        if (today < currentStartDate || today > currentEndDate) {
            // Need to adjust the period to include today
            const { startDate, endDate } = calculateTwoWeekPeriod(today);
            loadTwoWeekData(startDate, endDate);
        }
    }

    // Show the single day view for today
    setTimeout(() => {
        loadDateData(todayString).then(dayData => {
            // Always show the single day view, even if there's no data
            showSingleDateView(todayString, dayData);
        });
    }, 500);
}

// Update the date range display
function updateDateRange() {
    if (!currentStartDate || !currentEndDate) return;

    const startStr = currentStartDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });
    const endStr = currentEndDate.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });

    // Update the two week title with the date range
    document.getElementById('twoWeekTitle').textContent = `${startStr} - ${endStr}`;
}

// Get the Monday of the week containing the given date
function getWeekStart(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Adjust when day is Sunday
    return new Date(d.setDate(diff));
}

// Format date object as YYYY-MM-DD string for API calls
function formatDateForAPI(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format seconds as HH:MM:SS
function formatTime(seconds) {
    if (seconds === 0) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Navigate to a specific week in the two-week view
function navigateToWeek(targetDate) {
    // Close single date view and single activity view when navigating
    closeSingleDateView();
    closeSingleActivityView();

    // Calculate the two-week period with the target date in the second week
    const { startDate, endDate } = calculateTwoWeekPeriod(targetDate, true);

    loadTwoWeekData(startDate, endDate);
}

// Show/hide loading indicator
function showLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'block';
    }
}

function hideLoading() {
    const loadingElement = document.getElementById('loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
}

/**
 * Calculate 14-week period ending with current week
 * Used by all 14-week charts regardless of data type
 *
 * @returns {object} - {startDate: Date, endDate: Date, dateLabels: string[]}
 */
function calculate14WeekPeriod() {
    const today = new Date();
    const currentWeekStart = getWeekStart(today);
    const fourteenWeekStart = new Date(currentWeekStart);
    fourteenWeekStart.setDate(currentWeekStart.getDate() - (13 * 7)); // Go back 13 weeks

    // Generate array of 98 date labels (14 weeks × 7 days)
    const dateLabels = [];
    const currentDate = new Date(fourteenWeekStart);
    for (let i = 0; i < 98; i++) {
        const year = currentDate.getFullYear();
        const month = String(currentDate.getMonth() + 1).padStart(2, '0');
        const day = String(currentDate.getDate()).padStart(2, '0');
        dateLabels.push(`${year}-${month}-${day}`);
        currentDate.setDate(currentDate.getDate() + 1);
    }

    return {
        startDate: fourteenWeekStart,
        endDate: currentWeekStart,
        dateLabels
    };
}

/**
 * Group daily data into weekly aggregations
 * Used by all 14-week charts to convert 98 daily data points into 14 weekly aggregations
 *
 * @param {string[]} dateLabels - Array of 98 date labels (YYYY-MM-DD)
 * @param {Array} dataResults - Array of 98 daily data objects
 * @param {function} aggregationFunction - Function to aggregate week data (zone-specific)
 * @returns {object} - {weeklyData: Array, weekLabels: string[]}
 */
function groupDataByWeeks(dateLabels, dataResults, aggregationFunction) {
    const weeklyData = [];
    const weekLabels = [];

    for (let week = 0; week < 14; week++) {
        const weekStart = week * 7;
        const weekEnd = weekStart + 7;
        const weekDates = dateLabels.slice(weekStart, weekEnd);
        const weekData = dataResults.slice(weekStart, weekEnd);

        // Aggregate data for this week using provided function
        const weekAggregated = aggregationFunction(weekData);
        weeklyData.push(weekAggregated);

        // Create week label (e.g., "Apr 7")
        const firstDate = new Date(weekDates[0] + 'T00:00:00');
        const weekLabel = firstDate.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric'
        });
        weekLabels.push(weekLabel);
    }

    return { weeklyData, weekLabels };
}
