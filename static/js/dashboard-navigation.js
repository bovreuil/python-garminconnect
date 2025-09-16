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

// Navigate single day left or right
function navigateSingleDay(direction) {
    if (!selectedDate) {
        return;
    }
    
    const currentDate = new Date(selectedDate);
    currentDate.setDate(currentDate.getDate() + direction);
    const newDateLabel = currentDate.toISOString().split('T')[0];
    
    // Check if the new date is within the current two-week view
    if (currentStartDate && currentEndDate) {
        if (currentDate >= currentStartDate && currentDate <= currentEndDate) {
            // Date is within current view, just update single date view
            loadDateData(newDateLabel).then(dayData => {
                showSingleDateView(newDateLabel, dayData);
            });
        } else {
            // Date is outside current view, need to navigate to new two-week period
            const { startDate, endDate } = calculateTwoWeekPeriod(currentDate);
            loadTwoWeekData(startDate, endDate);
            
            // Then show single date view for the new date
            loadDateData(newDateLabel).then(dayData => {
                showSingleDateView(newDateLabel, dayData);
            });
        }
    }
}

// Go to today from single date view
function goToSingleDateToday() {
    // Close single activity view when going to today
    closeSingleActivityView();
    
    const today = new Date();
    const todayString = today.toISOString().split('T')[0];
    
    // Check if today is within the current two-week view
    if (currentStartDate && currentEndDate) {
        if (today >= currentStartDate && today <= currentEndDate) {
            // Today is within current view, just update single date view
            loadDateData(todayString).then(dayData => {
                showSingleDateView(todayString, dayData);
            });
        } else {
            // Today is outside current view, need to navigate to today's two-week period
            const { startDate, endDate } = calculateTwoWeekPeriod(today);
            loadTwoWeekData(startDate, endDate);
            
            // Then show single date view for today
            loadDateData(todayString).then(dayData => {
                showSingleDateView(todayString, dayData);
            });
        }
    }
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
