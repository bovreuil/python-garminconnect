/**
 * Page Initialization
 * 
 * Common initialization code shared between dashboard and oxygen debt pages.
 * Includes CSS injection, Chart.js setup, and variable declarations.
 */

// Initialize common page elements and configuration
function initializePage() {
    // Register the DataLabels plugin
    // Chart.register(ChartDataLabels); // Temporarily disabled for debugging
    
    // Add CSS for notes fields
    injectNotesCSS();
    
    // Configure Chart.js defaults
    configureChartDefaults();
    
    // Initialize global chart variables
    initializeChartVariables();
}

// Inject CSS for notes fields - IDENTICAL in both pages
function injectNotesCSS() {
    const style = document.createElement('style');
    style.textContent = `
        .notes-field {
            padding: 0.5rem;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.375rem;
            cursor: pointer;
            min-height: 2.5rem;
            transition: all 0.2s ease-in-out;
        }
        
        .notes-field:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
        
        .notes-field p {
            margin: 0;
            min-height: 1.5rem;
        }
    `;
    document.head.appendChild(style);
}

// Configure Chart.js defaults - IDENTICAL in both pages
function configureChartDefaults() {
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
    Chart.defaults.font.size = 12;
    Chart.defaults.color = '#2c3e50';
}

// Initialize global chart variables - IDENTICAL in both pages
function initializeChartVariables() {
    // Global chart variables
    window.twoWeekChart = null;
    window.fourteenWeekChart = null;
    window.hrChart = null;
    window.spo2Chart = null;
    window.activitiesChart = null;
    window.activityHrChart = null;
    window.activitySpo2Chart = null;
    window.activityBreathingChart = null;
    window.spo2AtOrBelowChart = null;
    window.spo2AtChart = null;
    window.activitySpo2AtOrBelowChart = null;
    window.activitySpo2AtChart = null;
    window.spo2IndividualLevelsChart = null;
    window.activitySpo2IndividualLevelsChart = null;
    
    // Global state variables
    window.currentStartDate = null;
    window.currentEndDate = null;
    window.currentDataResults = []; // Store the current data results for click handling
    window.selectedDate = null; // Track the currently selected date for single date view
    window.selectedActivity = null; // Track the currently selected activity
}

// Setup common event listeners - enhanced version of existing resize handler
function setupCommonEventListeners() {
    // Set up shared event listeners
    setupEventHandlers();
    
    // Add enhanced window resize listener to keep charts aligned
    window.addEventListener('resize', function() {
        setTimeout(() => {
            // Resize all charts if they exist
            if (twoWeekChart) twoWeekChart.resize();
            if (fourteenWeekChart) fourteenWeekChart.resize();
            if (hrChart) hrChart.resize();
            if (spo2Chart) spo2Chart.resize();
            if (activitiesChart) activitiesChart.resize();
            if (activityHrChart) activityHrChart.resize();
            if (activitySpo2Chart) activitySpo2Chart.resize();
            if (activityBreathingChart) activityBreathingChart.resize();
            if (spo2AtOrBelowChart) spo2AtOrBelowChart.resize();
            if (spo2AtChart) spo2AtChart.resize();
            if (activitySpo2AtOrBelowChart) activitySpo2AtOrBelowChart.resize();
            if (activitySpo2AtChart) activitySpo2AtChart.resize();
            if (spo2IndividualLevelsChart) spo2IndividualLevelsChart.resize();
            if (activitySpo2IndividualLevelsChart) activitySpo2IndividualLevelsChart.resize();
            
            // Keep SpO2 and HR charts aligned (dashboard specific but harmless on oxygen debt page)
            if (spo2Chart && hrChart) {
                const hrContainer = document.querySelector('.chart-container canvas#hrChart').parentElement;
                const spo2Container = document.querySelector('.chart-container canvas#spo2Chart').parentElement;
                if (hrContainer && spo2Container) {
                    spo2Container.style.width = hrContainer.offsetWidth + 'px';
                    spo2Chart.resize();
                }
            }
            if (activitySpo2Chart && activityHrChart) {
                const hrContainer = document.querySelector('.chart-container canvas#activityHrChart').parentElement;
                const spo2Container = document.querySelector('.chart-container canvas#activitySpo2Chart').parentElement;
                if (hrContainer && spo2Container) {
                    spo2Container.style.width = hrContainer.offsetWidth + 'px';
                    activitySpo2Chart.resize();
                }
            }
            if (activityBreathingChart && activityHrChart) {
                const hrContainer = document.querySelector('.chart-container canvas#activityHrChart').parentElement;
                const breathingContainer = document.querySelector('.chart-container canvas#activityBreathingChart').parentElement;
                if (hrContainer && breathingContainer) {
                    breathingContainer.style.width = hrContainer.offsetWidth + 'px';
                    activityBreathingChart.resize();
                }
            }
        }, 100);
    });
}
