/**
 * Page Configuration System
 * 
 * Defines data sources, zones, colors, and aggregation logic for each page.
 * This enables the same chart functions to work with different data types.
 */

// Page configuration objects
const PAGE_CONFIGS = {
    dashboard: {
        name: 'Dashboard',
        dataType: 'trimp',
        zones: zoneOrder,
        colors: zoneColors,
        metrics: {
            primary: { key: 'trimp', label: 'TRIMP', buttonId: 'trimpBtn' },
            secondary: { key: 'minutes', label: 'Minutes', buttonId: 'minutesBtn' }
        },
        dataExtractor: {
            // Extract data from API response for this page's charts
            getZoneData: (dayData, zone, metric) => {
                if (!dayData || !dayData.presentation_buckets || !dayData.presentation_buckets[zone]) {
                    return 0;
                }
                
                if (metric === 'trimp') {
                    // Use override values if available, otherwise use calculated values
                    if (dayData.trimp_overrides && dayData.trimp_overrides[zone] !== undefined) {
                        return dayData.trimp_overrides[zone];
                    } else {
                        return dayData.presentation_buckets[zone].trimp || 0;
                    }
                } else {
                    // For minutes view, show 0 if overrides exist
                    if (dayData.trimp_overrides && Object.keys(dayData.trimp_overrides).length > 0) {
                        return 0;
                    } else {
                        return dayData.presentation_buckets[zone].minutes || 0;
                    }
                }
            },
            
            // Calculate total for tooltip display
            getTotal: (dayData, metric) => {
                if (!dayData) return 0;
                
                if (metric === 'trimp') {
                    // Use override total if available, otherwise use calculated total
                    let trimpTotal = dayData.total_trimp || 0;
                    if (dayData.trimp_overrides && Object.keys(dayData.trimp_overrides).length > 0) {
                        trimpTotal = Object.values(dayData.trimp_overrides).reduce((sum, value) => sum + value, 0);
                    }
                    return trimpTotal;
                } else {
                    // Calculate total minutes for this day (0 if overrides exist)
                    let totalMinutes = 0;
                    if (dayData.trimp_overrides && Object.keys(dayData.trimp_overrides).length > 0) {
                        totalMinutes = 0;
                    } else if (dayData.presentation_buckets) {
                        Object.values(dayData.presentation_buckets).forEach(bucket => {
                            totalMinutes += bucket.minutes || 0;
                        });
                    }
                    return totalMinutes;
                }
            }
        },
        
        // Week aggregation function
        aggregateWeekData: function(weekData, metric) {
            const aggregated = {};
            
            // Initialize all zones with 0
            this.zones.forEach(zone => {
                aggregated[zone] = 0;
            });
            
            // Aggregate data for each day in the week
            weekData.forEach(dayData => {
                if (dayData) {
                    this.zones.forEach(zone => {
                        aggregated[zone] += this.dataExtractor.getZoneData(dayData, zone, metric);
                    });
                }
            });
            
            return aggregated;
        }
    },

    'oxygen-debt': {
        name: 'Oxygen Debt Analysis',
        dataType: 'oxygen_debt',
        zones: oxygenDebtZoneOrder,
        colors: oxygenDebtColors,
        metrics: {
            primary: { key: 'area', label: 'Area', buttonId: 'areaBtn' },
            secondary: { key: 'minutes', label: 'Minutes', buttonId: 'minutesBtn' }
        },
        dataExtractor: {
            getZoneData: (dayData, zone, metric) => {
                if (!dayData || !dayData.oxygen_debt) {
                    return 0;
                }
                
                const oxygenDebt = dayData.oxygen_debt;
                
                if (metric === 'area') {
                    if (zone === 'Below 95') return oxygenDebt.area_under_95 || 0;
                    if (zone === 'Below 90') return oxygenDebt.area_under_90 || 0;
                    if (zone === 'Below 88') return oxygenDebt.area_under_88 || 0;
                } else {
                    // Convert seconds to minutes for minutes view
                    if (zone === 'Below 95') return Math.round((oxygenDebt.time_under_95 || 0) / 60);
                    if (zone === 'Below 90') return Math.round((oxygenDebt.time_under_90 || 0) / 60);
                    if (zone === 'Below 88') return Math.round((oxygenDebt.time_under_88 || 0) / 60);
                }
                return 0;
            },
            
            getTotal: (dayData, metric) => {
                if (!dayData || !dayData.oxygen_debt) return 0;
                
                const oxygenDebt = dayData.oxygen_debt;
                
                if (metric === 'area') {
                    // Calculate total oxygen debt area for this day
                    const totalArea = (oxygenDebt.area_under_95 || 0) + 
                                     (oxygenDebt.area_under_90 || 0) + 
                                     (oxygenDebt.area_under_88 || 0);
                    return totalArea;
                } else {
                    // Calculate total oxygen debt minutes for this day
                    const totalMinutes = Math.round(((oxygenDebt.time_under_95 || 0) + 
                                                   (oxygenDebt.time_under_90 || 0) + 
                                                   (oxygenDebt.time_under_88 || 0)) / 60);
                    return totalMinutes;
                }
            }
        },
        
        aggregateWeekData: function(weekData, metric) {
            const aggregated = {};
            
            // Initialize all oxygen debt zones with 0
            this.zones.forEach(zone => {
                aggregated[zone] = 0;
            });
            
            // Aggregate data for each day in the week
            weekData.forEach(dayData => {
                if (dayData) {
                    this.zones.forEach(zone => {
                        aggregated[zone] += this.dataExtractor.getZoneData(dayData, zone, metric);
                    });
                }
            });
            
            return aggregated;
        }
    },

    'spo2-distribution': {
        name: 'SpO2 Distribution Analysis',
        dataType: 'spo2_distribution',
        zones: ['80', '81', '82', '83', '84', '85', '86', '87', '88', '89', '90', '91', '92', '93', '94', '95', '96', '97', '98', '99'],
        colors: spo2LevelColors,
        metrics: {
            primary: { key: 'at', label: 'SpO2 Distribution (%)', buttonId: null } // No toggle needed
        },
        dataExtractor: {
            getZoneData: (dayData, level, metric) => {
                if (!dayData || !dayData.spo2_distribution || !dayData.spo2_distribution.at_level) {
                    return 0;
                }
                
                // Find the SpO2 level data (only 'at' metric for SpO2 distribution)
                const levelData = dayData.spo2_distribution.at_level.find(item => item.spo2 === parseInt(level));
                return levelData ? levelData.percent : 0;
            },
            
            getTotal: (dayData, metric) => {
                if (!dayData || !dayData.spo2_distribution || !dayData.spo2_distribution.at_level) return 0;
                
                // Calculate total percentage (should be 100% for SpO2 distribution)
                const totalPercent = dayData.spo2_distribution.at_level.reduce((sum, item) => sum + item.percent, 0);
                return totalPercent;
            },
            
            // Activity-specific data extraction (activities have different structure)
            getActivityZoneData: (activity, level, metric) => {
                if (!activity || !activity.spo2_distribution || !activity.spo2_distribution.at_level) {
                    return 0;
                }
                
                // Find the SpO2 level data for activity
                const levelData = activity.spo2_distribution.at_level.find(item => item.spo2 === parseInt(level));
                return levelData ? levelData.percent : 0;
            },
            
            getActivityTotal: (activity, metric) => {
                if (!activity || !activity.spo2_distribution || !activity.spo2_distribution.at_level) return 0;
                
                // Calculate total percentage for activity
                const totalPercent = activity.spo2_distribution.at_level.reduce((sum, item) => sum + item.percent, 0);
                return totalPercent;
            }
        },
        
        aggregateWeekData: function(weekData, metric) {
            const aggregated = {};
            
            // Initialize all SpO2 levels with 0
            this.zones.forEach(level => {
                aggregated[level] = 0;
            });
            
            // For SpO2 distribution, we average the percentages across the week
            let validDays = 0;
            weekData.forEach(dayData => {
                if (dayData && dayData.spo2_distribution && dayData.spo2_distribution.at_level) {
                    validDays++;
                    this.zones.forEach(level => {
                        aggregated[level] += this.dataExtractor.getZoneData(dayData, level, metric);
                    });
                }
            });
            
            // Average the percentages
            if (validDays > 0) {
                this.zones.forEach(level => {
                    aggregated[level] = aggregated[level] / validDays;
                });
            }
            
            return aggregated;
        }
    }
};

// Get current page configuration based on URL path
function getCurrentPageConfig() {
    const path = window.location.pathname;
    
    if (path === '/oxygen-debt') {
        return PAGE_CONFIGS['oxygen-debt'];
    } else if (path === '/spo2-distribution') {
        return PAGE_CONFIGS['spo2-distribution'];
    } else {
        return PAGE_CONFIGS.dashboard; // Default to dashboard
    }
}

// Global current page config (set on page load)
let currentPageConfig = null;
