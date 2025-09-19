# Domain Model - Heart Rate & SpO2 Analysis Platform

This document describes the core domain concepts and data architecture for our physiological data analysis platform.

## Overview

We analyze physiological time series data to understand fitness and health patterns. The platform handles two main data types:
- **Heart Rate (HR)** time series from Garmin devices
- **SpO2** time series from O2Ring devices

All analysis is organized around **Days** and **Activities**, with data flowing from raw time series → derived aggregations → visualizations at different time scales.

## Core Domain Concepts

### Time Series Data (Raw Data)

**Heart Rate Time Series**
- Timestamps + heart rate values (BPM)
- Sources: Garmin daily data (every 2 mins) + Garmin activity data (every few seconds)
- Activity data preferred over daily data when both exist
- Used for: Line charts in single day/activity views

**SpO2 Time Series** 
- Timestamps + SpO2 values (%)
- Source: O2Ring device (every 4 seconds)
- Mapped to days/activities by timestamp overlap
- Used for: Line charts in single day/activity views

**Breathing Rate Time Series**
- Timestamps + breathing rate values
- Source: Garmin activities only
- Used for: Line charts in single activity views (display only, no derived data)

### Derived Data (Aggregations)

**TRIMP Zone Data** (from HR time series)
- 9 zones: 80-89, 90-99, 100-109, 110-119, 120-129, 130-139, 140-149, 150-159, 160+ BPM
- Per zone: minutes in zone + TRIMP score in zone
- Calculated at: day level + activity level
- Used for: Dashboard 14-week/2-week charts, activity charts

**SpO2 Level Data** (from SpO2 time series)
- Time spent at each SpO2 percentage level
- Time spent at or below key levels (95%, 90%, 88%)
- Calculated at: day level + activity level
- Used for: Single day/activity SpO2 distribution charts

**Oxygen Debt Summary Data** (from SpO2 time series)
- 3 key thresholds: Below 95%, Below 90%, Below 88%
- Per threshold: time_under + area_under (time × distance below threshold)
- Calculated at: day level + activity level
- Used for: Oxygen debt page 2-week charts

### Organizational Units

**Days**
- Calendar days (YYYY-MM-DD) - midnight to midnight in local time
- Contain: daily HR time series + mapped SpO2 time series + 0+ activities
- Derived data: daily TRIMP zones + daily SpO2 levels + daily oxygen debt
- **Clock change consideration**: Days may be 23/25 hours long, but time series charts assume 1440 minutes (24 hours) for display consistency

**Activities** 
- Garmin construct: name, start time, end time
- Contain: activity HR time series + activity breathing series + mapped SpO2 time series
- Derived data: activity TRIMP zones + activity SpO2 levels + activity oxygen debt

## Page Architecture

Each page is defined by **which derived data type** it displays in trend charts. All other elements remain consistent across pages.

### Data Types by View Level

**Time Series Data** (consistent across all pages):
- Day level: HR time series, SpO2 time series
- Activity level: HR time series, SpO2 time series, breathing time series

**Derived Data** (varies by page focus):
- Day level: TRIMP data, SpO2 level data, oxygen debt data, [future: new derived metrics]
- Activity level: TRIMP data, SpO2 level data, oxygen debt data, [future: new derived metrics]

**Other Data** (consistent across all pages):
- Day level: notes
- Activity level: notes

### Page Structure Matrix

| Element | Dashboard | Oxygen Debt | Future Clone |
|---------|-----------|-------------|--------------|
| **14-week chart** | day TRIMP data | *(not shown)* | day new derived metric |
| **2-week chart** | day TRIMP data | day oxygen debt data | day new derived metric |
| **Single day - SpO2 series chart** | day SpO2 series | day SpO2 series | day SpO2 series |
| **Single day - HR series chart** | day HR series | day HR series | day HR series |
| **Single day - TRIMP levels** | day TRIMP data | day TRIMP data | day TRIMP data |
| **Single day - SpO2 level chart** | day SpO2 level data | day SpO2 level data | day SpO2 level data |
| **Single day - oxygen debt summary** | day oxygen debt data | day oxygen debt data | day oxygen debt data |
| **Single day - notes** | day notes | day notes | day notes |
| **Single day - new visualization** | *(future)* | *(future)* | day new derived metric |
| **Single day - activities chart** | activity TRIMP data | activity oxygen debt data | activity new derived metric |
| **Single activity - SpO2 series** | activity SpO2 series | activity SpO2 series | activity SpO2 series |
| **Single activity - breathing series** | activity breathing series | activity breathing series | activity breathing series |
| **Single activity - HR series** | activity HR series | activity HR series | activity HR series |
| **Single activity - TRIMP levels** | activity TRIMP data | activity TRIMP data | activity TRIMP data |
| **Single activity - SpO2 level chart** | activity SpO2 level data | activity SpO2 level data | activity SpO2 level data |
| **Single activity - oxygen debt summary** | activity oxygen debt data | activity oxygen debt data | activity oxygen debt data |
| **Single activity - notes** | activity notes | activity notes | activity notes |
| **Single activity - new visualization** | *(future)* | *(future)* | activity new derived metric |

### Key Insights

1. **Very few data types**: Only time series + derived data at day/activity levels
2. **Modular composition**: Views combine these basic data types in different ways
3. **Page differentiation**: Only the trend charts (14-week, 2-week, activities) vary by page
4. **Consistent single views**: Day and activity detail views show all available data types

### View Composition Principles

**Multi-day Views** (14-week, 2-week charts):
- Display: Day-level derived data for the page's focus metric
- Aggregation: Sum day data to weeks for 14-week charts (on-the-fly)
- Data source: Cached derived data only (no time series rebuilding)

**Single Day View**:
- Display: Day time series + day derived data + activity derived data (for activities chart)
- Shows: All available data types (TRIMP, SpO2 levels, oxygen debt, future metrics)
- Data source: Rebuild day time series (load sources, apply priority order) + cached derived data

**Single Activity View**:
- Display: Activity time series + activity derived data
- Shows: All available data types (TRIMP, SpO2 levels, oxygen debt, future metrics)  
- Data source: Rebuild activity time series (load sources, apply priority order) + cached derived data

**Theoretical Single Week View**:
- Display: Day-level derived data aggregated to single week
- Would show: 7 days summed to 1 week for any derived metric

## Data Requirements by View

### Chart Data Requirements

**14-Week Chart**: 98 days × derived data values (varies by page)
- Dashboard: 98 days × 18 TRIMP values = 1,764 values
- Future pages: 98 days × N values for new derived metrics
- Only needs: cached derived data (aggregate to weeks on-the-fly)
- Should NOT rebuild time series

**2-Week Chart**: 14 days × derived data values (varies by page)
- Dashboard: 14 days × 18 TRIMP values = 252 values
- Oxygen debt: 14 days × 6 oxygen debt values = 84 values
- Future pages: 14 days × N values for new derived metrics
- Only needs: cached derived data
- Should NOT rebuild time series

**Single Day View**: 1 day
- Needs: HR time series + SpO2 time series + all derived data types
- OK to rebuild time series (single day only): load relevant sources from database, apply priority order
- Shows all available derived data (TRIMP + SpO2 levels + oxygen debt + future metrics)

**Single Activity View**: 1 activity
- Needs: HR time series + SpO2 time series + breathing series + all derived data types
- OK to rebuild time series (single activity only): load relevant sources from database, apply priority order
- Shows all available derived data (TRIMP + SpO2 levels + oxygen debt + future metrics)

### Performance Requirements

- **Chart loading**: < 2 seconds (14-week), < 1 second (2-week)
- **Single day**: < 3 seconds (acceptable for detailed view)
- **Single activity**: < 2 seconds (acceptable for detailed view)

## Data Sources & Management

### Garmin Data Source
- **Daily HR**: Whole day, 2-minute intervals
- **Activity Timeseries**: Per activity, few-second intervals, HR, breathing rate (and more)  
- **Activity Metadata**: Name, start/end times (and more)
- **Loading**: Via Garmin API, by calendar day
- **Triggers recalculation**: HR-derived data for affected day + activities

### O2Ring Data Source
- **SpO2 Time Series**: 4-second intervals while wearing ring
- **Loading**: CSV file upload
- **Mapping**: To days/activities by timestamp overlap
- **Triggers recalculation**: SpO2-derived data for overlapped days + activities

### Data Correction Mechanisms

**Manual Activities**
- Create flat HR activity to override bad daily HR data
- Triggers: activity + day HR-derived data recalculation

**Activity HR CSV Override**
- Download/edit/upload activity HR time series
- Triggers: activity + day HR-derived data recalculation

**TRIMP Overrides**
- Manual entry of TRIMP zone values per day
- Used when: no HR data available or incomplete data
- Overrides: calculated TRIMP values
- Triggers: chart refresh only (no recalculation)

**SpO2 CSV Management**
- Upload: triggers SpO2-derived data recalculation for overlapped days/activities
- Delete: triggers SpO2-derived data recalculation for overlapped days/activities

## Data Storage Strategy

### Caching Strategy
- **Store**: All derived data at day + activity level only (no weekly aggregation needed)
- **Calculate**: Only when missing or time series data changes
- **Serve charts**: From cached derived data only (no time series rebuilding)
- **Serve detailed views**: Rebuild time series + use cached derived data
- **Weekly aggregation**: Sum day-level data on-the-fly for 14-week charts

### Invalidation Rules
When time series data changes, recalculate derived data for:
- **Day-level changes**: Only the affected day(s)
- **Activity-level changes**: The affected activity + its parent day
- **SpO2 CSV changes**: All overlapped days + all overlapped activities
- **No cascade to weeks**: Weekly data calculated on demand from day data

### Database Schema Principles
- **Time series**: Store as JSON arrays of [timestamp, value] pairs
- **Derived data**: Store as JSON objects with zone/level breakdowns
- **Caching**: Hash-based invalidation when source data changes
- **Organization**: Separate tables for daily_data vs activity_data
- **No weekly storage**: Calculate weekly aggregations from daily data as needed

## API Design Principles

### Efficient Chart APIs
- **Batch endpoints**: Single request for multiple days
- **Lightweight responses**: Derived data only, no time series
- **Conditional loading**: Skip expensive operations for cached data
- **Separate concerns**: Chart data vs detailed view data

### Data Consistency
- **Invalidation**: Cascade when source data changes
- **Atomicity**: Complete recalculation or rollback
- **Freshness**: Detect stale cache via hash comparison

## Refactoring Goals

### Code-Domain Alignment
1. **Clear separation**: Time series vs derived data handling
2. **Consistent patterns**: Same structure across all derived data types
3. **Efficient caching**: Serve charts from cache, rebuild only when needed
4. **Modular design**: Easy to add new derived data types

### Performance Targets
1. **Chart loading**: Return to original 2s/fast performance
2. **Batch efficiency**: Single DB queries, no redundant calculations
3. **Cache utilization**: Skip rebuilding when cached data sufficient
4. **Resource management**: Reuse connections, minimize memory

### Maintainability
1. **Domain language**: Code matches this document's terminology
2. **Single responsibility**: Each function has clear domain purpose
3. **Easy extension**: New derived data types follow same patterns
4. **Clear boundaries**: Separation between data sources, processing, presentation

### DRY Principle Application

**When to Apply DRY** (Extract/Share):
1. **Identical functions**: Exactly the same logic, same inputs/outputs
2. **Time series display**: Same chart type for same data type (HR, SpO2, breathing)
3. **Utility functions**: Color mappings, date formatting, shared calculations
4. **Data loading patterns**: Identical API calls and response handling
5. **Navigation patterns**: Chart interaction and navigation logic independent of data type

**When to AVOID DRY** (Keep Separate):
1. **Similar but different logic**: Same chart type but different data sources
2. **Evolving visualizations**: Charts that may diverge in future (line vs bar, different axes)
3. **Page-specific behavior**: Different click handlers, different navigation flows
4. **Premature abstractions**: When we don't yet understand the full pattern

**Current Code Analysis** (Post-Refactoring):

**Module Organization** (Domain-Perfect):
- **heart-rate-charts.js** (1,052 lines): Daily + Activity HR time series
- **spo2-charts.js** (806 lines): Daily + Activity SpO2 time series + distributions  
- **breathing-charts.js** (289 lines): Activity breathing time series
- **modal-management.js** (671 lines): All user interaction modals
- **shared-data-functions.js** (202 lines): Common data loading patterns
- **dashboard-navigation.js** (203 lines): Navigation and timing logic
- **All other modules** (<200 lines): Focused utilities

**Chart Similarity Patterns**:

*Time Series Charts (Same Chart, Different X-Axis):*
- **HR Day vs Activity**: Same chart logic, 24-hour vs activity-duration x-axis
- **SpO2 Day vs Activity**: Same chart logic, 24-hour vs activity-duration x-axis  
- **Pattern**: Only x-axis timeline generation differs (24-hour vs activity range)

*Trend Charts (Same Chart, Different X-Axis):*
- **TRIMP 14-week vs 2-week**: Same chart logic, weekly vs daily x-axis aggregation
- **Oxygen Debt 14-week vs 2-week**: Same chart logic, weekly vs daily x-axis aggregation
- **Activities Charts**: Same as 14/2-week but transposed (horizontal bars per activity)

*Cross-Data-Type Similarities (Different Data, Same Structure):*
- **14-week charts**: Identical timing logic (14 weeks up to today), different data sources
- **2-week charts**: Identical navigation logic (boundaries, buttons), different data sources
- **Single views**: Identical component loading, different derived data displays

### Chart Navigation Patterns (Potential Abstraction)

**Common Navigation Logic** (Independent of Data Type):
All chart navigation follows identical patterns regardless of whether displaying TRIMP or oxygen debt data:

1. **14-Week Chart Timing**: Always displays 14 weeks up to and including the week containing today
2. **Week Click Navigation**: Clicking on a week in 14-week chart navigates 2-week chart to show that week
3. **Minimal Navigation**: Navigation makes the smallest move possible to include the clicked week
4. **Two-Week Chart Structure**: Always displays exactly 2 weeks, Monday to Sunday
5. **Today Button Behavior**: Always displays today in the second week of the 2-week chart
6. **Arrow Navigation**: Left/right buttons move 2-week chart by exactly one week
7. **Day Click Navigation**: Clicking on a day in 2-week chart opens single day view

**Within-Page Chart Similarities** (Potential Abstraction):
- **Dashboard**: 14-week TRIMP chart vs 2-week TRIMP chart (same data source, different aggregation)
- **Oxygen Debt**: 14-week oxygen debt chart vs 2-week oxygen debt chart (same data source, different aggregation)
- **Pattern**: Both pairs differ only in x-axis granularity (days vs weeks) and bar count (14 vs 98 data points)

**High-Value Abstraction Opportunities** (Complex Logic Duplication):

*Critical for Future Extensibility:*
1. **14-Week Timing Logic**: Complex calculation of 14 weeks up to today's week (in `loadFourteenWeekData()`)
2. **2-Week Navigation Logic**: Complex boundary calculation, left/right navigation, today button behavior
3. **X-Axis Timeline Generation**: 24-hour timeline vs activity-duration timeline patterns

*Medium-Value Abstractions:*
4. **Within-Page Chart Pairs**: 14-week vs 2-week chart logic (same data, different aggregation)
5. **Chart Click Handlers**: Navigation and view-switching behavior patterns
6. **Data Aggregation**: Week-level summation from daily data

**Future Impact**:
Adding new derived metrics will require:
- New 14-week charts → duplicate complex timing logic
- New 2-week charts → duplicate complex navigation logic  
- New time series → duplicate x-axis timeline generation
- New single views → duplicate component loading patterns

**Priority**: Extract timing and navigation logic before adding new chart types to avoid exponential duplication growth.

## Current Architecture State (Post-Refactoring)

### Code Organization Achievement

**Perfect Domain Alignment**: Code structure now mirrors domain model exactly
- **Data Type Separation**: HR, SpO2, breathing charts in separate modules
- **Concern Separation**: Navigation, modals, utilities cleanly isolated
- **Zero Duplication**: All identical code extracted to shared modules
- **Workable Sizes**: All files <1,100 lines (AI-development friendly)

**Template Transformation**:
- **Before**: 5,277 lines each (83% duplication)
- **After**: 915 lines each (0% duplication)
- **Result**: Clean, page-specific logic only

**Module Quality**:
- **13 focused modules** replacing monolithic templates
- **Single responsibility** principle perfectly applied
- **Clear dependencies** with logical import ordering
- **Consistent patterns** across all similar functionality

### Identified Complex Duplication (High-Value Targets)

**1. Timeline Generation Logic** (Currently Duplicated):
- **24-Hour Timeline**: `heart-rate-charts.js` + `spo2-charts.js` (daily views)
- **Activity Timeline**: `heart-rate-charts.js` + `spo2-charts.js` + `breathing-charts.js` (activity views)
- **Pattern**: Same timeline generation, different chart types
- **Impact**: New time series charts will duplicate this complex logic

**2. Chart Period Calculation** (Currently Duplicated):
- **14-Week Period**: `templates/dashboard.html` + `templates/oxygen_debt.html`
- **2-Week Navigation**: Both templates use `dashboard-navigation.js` functions
- **Pattern**: Same timing logic, different data aggregation
- **Impact**: New trend charts will duplicate timing calculations

**3. Chart Structure Patterns** (Currently Duplicated):
- **Stacked Bar Logic**: 14-week, 2-week, activities charts all use similar structure
- **Click Handlers**: Navigation behavior identical across chart types
- **Tooltip Formatting**: Similar patterns for totals and breakdowns

### Refactoring Readiness Assessment

**Ready for Advanced Abstractions**: ✅
- Clean foundation established
- All duplication eliminated at function level
- Clear patterns identified for next-level abstractions
- Test-driven process proven effective

**Next-Level Targets** (In Priority Order):
1. **Timeline Generation Utilities**: Extract x-axis logic (high complexity, high reuse)
2. **Chart Period Calculations**: Extract 14-week/2-week timing logic
3. **Chart Structure Templates**: Parameterized chart configuration patterns

## Development Guidelines: Coding Tasks

These guidelines ensure all new development respects our refactored architecture and maintains clean separation of concerns.

### Task 1: Calculate New Derived Data Type from Time Series

**When**: Adding new metrics like HRV zones, recovery scores, training load, etc.

**Steps**:
1. **Backend Calculation Function** (Python in `app.py`):
   ```python
   def calculate_new_metric_from_timeseries(time_series_data):
       """
       Calculate new derived metric from time series.
       Args: time_series_data: List of [timestamp, value] pairs
       Returns: Dict with derived metric data
       """
       # Pure calculation logic here
       return {'metric_zones': {...}, 'total_metric': 0.0}
   ```

2. **Add Caching Support** (follow TRIMP/oxygen debt patterns):
   ```python
   def calculate_new_metric_with_caching(target_date, time_series_data, data_type='daily'):
       # Follow exact pattern from calculate_trimp_with_caching()
   ```

3. **Wire to Time Series Extractors** (JavaScript frontend calls Python backend):
   ```javascript
   // Frontend: Extract clean time series
   const hrTimeSeries = getDayHRTimeSeries(dayData);
   // Send to backend API with time series data
   // Backend receives: [[timestamp, hr_value], ...] format
   ```
   ```python
   # Backend: Receive time series from frontend
   def calculate_new_metric_from_timeseries(hr_series):
       # hr_series format: [[timestamp, hr_value], ...] 
       # Already cleaned by JavaScript extractors
   ```

4. **Add to API Endpoints**:
   - Add to `/api/data/<date>` for daily metrics
   - Add to `/api/activities/<date>` for activity metrics
   - Follow existing patterns exactly

**Key Principles**:
- ✅ **Reuse time series extractors**: Never parse raw data formats again
- ✅ **Pure calculation functions**: Work with any time series, independent of source
- ✅ **Follow caching patterns**: Hash-based invalidation, same as TRIMP/oxygen debt
- ❌ **Don't mix concerns**: Keep calculation separate from data extraction and visualization

### Task 2: Display New Visualization in Single Day/Activity Views

**When**: Adding new components to single day or single activity detail views.

**Steps**:
1. **Create Visualization Function** (JavaScript in appropriate module):
   ```javascript
   // In new-metric-charts.js or existing module
   function createNewMetricVisualization(metricData, containerId, viewType) {
       // Pure visualization logic
       // Uses metricData (already calculated)
       // viewType: 'daily' or 'activity'
   }
   ```

2. **Add to View Loading** (in `view-management.js` or chart modules):
   ```javascript
   // In showSingleDateView() or showSingleActivityView()
   if (data.new_metric) {
       createNewMetricVisualization(data.new_metric, 'newMetricContainer', 'daily');
   }
   ```

3. **Add HTML Container** (in templates):
   ```html
   <!-- In single day/activity view sections -->
   <div id="newMetricContainer" class="chart-container">
       <h3>New Metric Analysis</h3>
       <!-- Visualization elements -->
   </div>
   ```

4. **Add to Cleanup** (in `data-loading.js`):
   ```javascript
   // In clearCharts() functions
   if (newMetricChart) {
       newMetricChart.destroy();
       newMetricChart = null;
   }
   ```

**Key Principles**:
- ✅ **Use calculated data**: Receive derived data, don't recalculate
- ✅ **Follow existing patterns**: Same structure as SpO2 levels, oxygen debt
- ✅ **Unified view type**: Same function for daily/activity, use viewType parameter
- ❌ **Don't duplicate**: Reuse existing container patterns and cleanup logic

### Task 3: Display New Visualization in 14-Week, 2-Week, Activities Views

**When**: Creating new trend pages (like oxygen debt page) for new derived metrics.

**Steps**:
1. **Create New Page Template** (copy `oxygen_debt.html`):
   ```html
   <!-- new-metric.html -->
   {% extends "base.html" %}
   <!-- Import same JavaScript modules -->
   <!-- Copy structure, change only data references -->
   ```

2. **Update Chart Functions** (in template):
   ```javascript
   // Change only the data property names
   function updateFourteenWeekChart() {
       // Use new_metric instead of oxygen_debt
       const newMetricData = dayData.new_metric;
       // Rest identical to oxygen debt pattern
   }
   
   function updateTwoWeekChart() {
       // Same pattern, different data property
   }
   
   function createActivitiesChart() {
       // Same pattern, different data property  
   }
   ```

3. **Add Route** (in `app.py`):
   ```python
   @app.route('/new-metric')
   def new_metric_page():
       return render_template('new_metric.html')
   ```

4. **Add Navigation** (in `base.html`):
   ```html
   <a href="/new-metric" class="nav-link">New Metric</a>
   ```

5. **Import Required Modules** (copy from existing templates):
   ```html
   <!-- Essential modules for any new page -->
   <script src="{{ url_for('static', filename='js/dashboard-navigation.js') }}"></script>
   <script src="{{ url_for('static', filename='js/chart-utilities.js') }}"></script>
   <script src="{{ url_for('static', filename='js/chart-timeline-utils.js') }}"></script>
   <script src="{{ url_for('static', filename='js/time-series-extractors.js') }}"></script>
   <!-- Add others as needed: data-loading.js, heart-rate-charts.js, etc. -->
   ```

**Key Principles**:
- ✅ **Copy proven patterns**: Start with oxygen debt page, change data references only
- ✅ **Reuse navigation logic**: Use existing `dashboard-navigation.js` functions
- ✅ **Reuse chart utilities**: Use `createZonedDatasets()` and other shared functions
- ❌ **Don't reinvent**: Chart timing, navigation, structure should be identical

### Common Anti-Patterns to Avoid

**❌ Don't Parse Raw Data Formats**:
```javascript
// WRONG - parsing raw data in charts
activity.heart_rate_values.forEach(point => {
    if (Array.isArray(point)) {
        timestamp = point[0]; hr = point[1];
    } else {
        timestamp = point.timestamp; hr = point.value;
    }
});

// RIGHT - use clean extractors
const hrTimeSeries = getActivityHRTimeSeries(activity);
hrTimeSeries.forEach(point => {
    const timestamp = point[0]; 
    const hr = point[1];
});
```

**❌ Don't Mix Calculation with Visualization**:
```javascript
// WRONG - calculating in chart function
function createNewChart(rawData) {
    // Complex calculation logic
    const derivedData = calculateComplexMetric(rawData);
    // Chart creation
}

// RIGHT - receive calculated data
function createNewChart(derivedData) {
    // Pure visualization only
}
```

**❌ Don't Duplicate Complex Logic**:
```javascript
// WRONG - copying timing logic
const fourteenWeeksAgo = new Date();
fourteenWeeksAgo.setDate(fourteenWeeksAgo.getDate() - (14 * 7));
// ... complex date arithmetic

// RIGHT - use shared utilities  
const { startDate, endDate } = calculate14WeekPeriod();
```

### Testing Strategy for New Features

**Always Test These Scenarios**:
1. **Data Loading**: Empty data, partial data, full data
2. **View Switching**: 14-week → 2-week → single day → single activity
3. **Navigation**: Left/right arrows, today button, chart clicks
4. **Responsive**: Resize browser, mobile view
5. **Error Cases**: Network failures, invalid data

**Test in This Order**:
1. Backend calculation function (unit test with sample data)
2. Single day/activity views (detailed view first)
3. 2-week chart (simpler than 14-week)
4. 14-week chart (most complex)
5. Navigation between views (integration test)

## Architecture Evolution Summary

### Recent Major Achievements (2024)

**Clean Time Series Extractors** (Latest):
- **New Module**: `time-series-extractors.js` 
- **Complete Coverage**: Functions for all time series types (day HR, activity HR, day SpO2, activity SpO2, activity breathing)
- **Standardized Format**: All return `[[timestamp, value], ...]`
- **Separated Concerns**: Data extraction completely isolated from visualization
- **Foundation Ready**: Perfect base for connecting to calculation functions

**SpO2 Component Abstraction**:
- **Unified Loading**: `loadSpO2Distribution(identifier, viewType)` 
- **Eliminated Duplication**: Identical loading patterns consolidated
- **Fixed Toggle Bug**: SpO2 "At"/"At or Below" charts now both created
- **Single Source**: `updateOxygenDebtDisplay()` in one location only

**Time Series Background Abstraction**:
- **Specialized Functions**: `createHRTimeSeriesBackground()`, `createSpO2TimeSeriesBackground()`
- **Eliminated Duplication**: Complex gradient logic consolidated
- **Maintained Distinction**: HR vs SpO2 gradients kept separate (avoided premature abstraction)
- **All Time Series Charts**: Daily/activity HR and SpO2 charts updated

**Colored Bar Dataset Abstraction**:
- **Generic Function**: `createZonedDatasets(zones, colors, dataExtractor, options)`
- **Flexible Design**: Works for TRIMP, oxygen debt, future metrics
- **Spread Operator**: `...options` for easy property overrides

**Week Grouping Logic Abstraction**:
- **Centralized Function**: `groupDataByWeeks(dateLabels, dataResults, aggregationFunc)`
- **Complex Week Boundaries**: Monday-to-Sunday week calculation with proper date formatting
- **Parameterized Aggregation**: Works with any data aggregation function
- **Universal Application**: All 14-week charts use same grouping logic

**Timeline and Period Calculation Utilities**:
- **14-Week Period**: `calculate14WeekPeriod()` - complex date arithmetic for 14 weeks up to today
- **Timeline Generation**: `generate24HourTimeline()`, `generateActivityTimeline()` (foundation for future use)
- **Gridline Logic**: `createAfterBuildTicks()` for consistent activity chart gridlines
- **Data Mapping**: `mapDataToTimeline()` for time series to timeline array mapping

**Template Transformation**:
- **Before**: Massive templates with 83% duplication between pages
- **After**: Clean, page-specific logic with zero duplication
- **Focused Modules**: Each module maintains single responsibility
- **Perfect Domain Alignment**: Code structure mirrors domain model

**Module Quality Principles**:
- **Domain Separation**: HR, SpO2, breathing charts in separate modules
- **Single Responsibility**: Each module has clear, focused purpose
- **Zero Duplication**: All identical code extracted to shared utilities
- **Manageable Size**: All modules kept to reasonable working size
- **Clean Dependencies**: Logical import ordering with clear boundaries

### Current Architecture State

**Data Flow** (Clean Pipeline):
```
Raw Data → Time Series Extractors → Calculation Functions → Charts
    ↓              ↓                      ↓                ↓
Database    [[timestamp,value]]     {derived_data}    Visualizations
Formats     Standardized Arrays     Cached Results    Chart.js
```

**Layer Responsibilities**:
- **Time Series Extractors** (JavaScript): Parse raw formats → standardized arrays
- **Calculation Functions** (Python): Process standardized arrays → derived metrics  
- **Chart Functions** (JavaScript): Render derived metrics → interactive visualizations
- **Shared Utilities** (JavaScript): Common patterns across all chart types

**Module Organization** (Domain-Perfect):
- **Data Extraction**: `time-series-extractors.js` (new foundation)
- **Calculations**: Backend Python functions (already clean)
- **Visualization**: Domain-specific chart modules (HR, SpO2, breathing)
- **Utilities**: Shared functions for common patterns
- **Navigation**: Timing and interaction logic centralized

**Abstraction Strategy** (Proven Effective):
- ✅ **Extract Identical Code**: Aggressive deduplication of genuinely same logic
- ✅ **Avoid Premature Abstractions**: Keep similar-but-different code separate
- ✅ **Modular Design**: Small, focused modules with clear boundaries
- ✅ **Test-Driven Process**: Code changes → test → commit cycle

### Ready for Future Development

**Foundation Complete**: 
- Clean time series extraction ✅
- Separated calculation functions ✅  
- Modular visualization components ✅
- Shared utilities for common patterns ✅

**Next Development Ready**:
- New derived metrics: Use existing extractors + add calculation functions
- New visualizations: Follow proven patterns in single views
- New trend pages: Copy oxygen debt page pattern
- Advanced abstractions: Timeline generation, chart period calculations

**Architecture Principles Established**:
1. **Domain Alignment**: Code structure matches domain model exactly
2. **Separation of Concerns**: Data extraction ≠ calculation ≠ visualization  
3. **Reusable Components**: Time series extractors, calculation functions, chart utilities
4. **Consistent Patterns**: Same structure for all similar functionality
5. **Test-Driven Evolution**: Small changes, frequent testing, regular commits

## Known Issues & TODOs

### Manual SpO2 Entry Button (TODO: Remove)
- **Issue**: Single activity view has manual SpO2 entry button that conflicts with O2Ring CSV data
- **Problem**: Button allows editing O2Ring data, which should be read-only
- **Solution**: Remove button and associated functionality (manual data preserved in database)
- **Priority**: Low (no longer needed since O2Ring implementation)

### Clock Changes (TODO: Monitor)
- **Issue**: Days during clock changes are 23 or 25 hours long
- **Current approach**: Time series charts assume 1440 minutes for display consistency
- **Consideration**: May need special handling for labeling and data presentation
- **Priority**: Monitor (no clock changes experienced yet with current system)

## Refactoring Methodology

This section captures the proven methodology for successful refactoring that prevents "agent goes rogue" scenarios and preserves knowledge across conversations.

### Core Process: Test-Driven Refactoring

**Golden Rule**: Never commit untested code. Always follow this cycle:

```
Code Changes → Manual Testing → Commit → Next Change
```

**Why This Works**:
- **Prevents regression**: Each commit is a known-good state
- **Enables rollback**: Can always return to last working version
- **Preserves knowledge**: Commit messages document what was changed and why
- **Builds confidence**: Each step is validated before proceeding

### Abstraction Decision Framework

**When to Extract (DRY Principle)**:
- ✅ **Identical Functions**: 100% same logic, same inputs, same outputs
- ✅ **3+ Usage Rule**: Pattern appears in 3 or more places
- ✅ **Clear Boundaries**: Function has single, well-defined responsibility
- ✅ **Stable Interface**: Function signature unlikely to change

**When NOT to Extract (Avoid Premature Abstraction)**:
- ❌ **Similar-but-Different**: Would require complex parameterization
- ❌ **Evolving Code**: Functionality likely to diverge in future
- ❌ **Unclear Pattern**: Haven't seen the pattern enough times to understand it fully
- ❌ **Forced Generalization**: Making code more complex to avoid small duplication

**Example Decision Process**:
```
Question: Should we extract this repeated code?
1. Is it 100% identical? → If no, keep separate
2. Used in 3+ places? → If no, wait for more usage
3. Clear single responsibility? → If no, don't extract yet
4. Interface stable? → If no, let it evolve first
```

### Strategic Refactoring Order

**Phase 1: Utilities & Pure Functions**
- Extract calculation functions (no side effects)
- Extract data transformation utilities
- Extract constants and configuration

**Phase 2: Common Setup & Infrastructure**
- Extract initialization code
- Extract shared event handlers
- Extract common imports and dependencies

**Phase 3: Data Loading & API Patterns**
- Extract identical API calls
- Extract data processing pipelines
- Extract error handling patterns

**Phase 4: UI Components & Visualization**
- Extract identical UI components
- Extract chart configuration patterns
- Extract interaction handlers

**Why This Order**:
- **Low Risk First**: Pure functions are safest to refactor
- **Foundation Up**: Build shared utilities before using them
- **High Value Last**: UI changes are most visible but most complex

### Root Cause Analysis Process

**When Bugs Appear During Refactoring**:

1. **Stop Making Changes**: Don't try to fix forward
2. **Use Git Diff**: `git diff HEAD~1` to see exactly what changed
3. **Identify Root Cause**: Understand why the change broke functionality
4. **Fix Systematically**: Address the root cause, not symptoms
5. **Test Thoroughly**: Verify fix works in all affected areas
6. **Document Learning**: Update methodology if new pattern discovered

**Common Root Causes**:
- **Variable Renaming**: Old references not updated
- **Function Signature Changes**: Parameters not updated everywhere
- **Missing Imports**: New modules not imported in all templates
- **Scope Issues**: Variables moved but references not updated

### Knowledge Preservation Strategy

**During Refactoring**:
- **Commit Messages**: Detailed descriptions of what and why
- **Domain Model Updates**: Update architecture documentation regularly
- **Pattern Documentation**: Note new patterns as they emerge
- **Anti-Pattern Documentation**: Record what doesn't work and why

**Between Conversations**:
- **Domain Model**: Primary knowledge repository
- **Git History**: Detailed record of changes and reasoning
- **Code Comments**: In-line documentation of complex decisions
- **README Updates**: High-level changes and new patterns

### Collaboration Patterns (AI + Human)

**Human Responsibilities**:
- **Strategic Direction**: Define goals and constraints
- **Quality Gates**: Test and validate each change
- **Domain Knowledge**: Provide context and business logic
- **Pattern Recognition**: Identify when abstractions are premature

**AI Responsibilities**:
- **Pattern Analysis**: Find duplicate code and similar structures
- **Implementation**: Execute refactoring changes systematically
- **Root Cause Analysis**: Analyze git diffs and trace problems
- **Documentation**: Update code comments and architecture docs

**Communication Protocol**:
- **Clear Objectives**: Human defines specific, measurable goals
- **Incremental Progress**: AI implements small, testable changes
- **Validation Loops**: Human tests before AI proceeds to next step
- **Knowledge Capture**: AI documents learnings in domain model

### Module Management Guidelines

**Size Management**:
- **Single Responsibility**: Each module should have one clear domain purpose
- **Manageable Complexity**: Keep modules small enough for effective AI collaboration
- **Clear Dependencies**: Explicit imports, avoid circular dependencies
- **Domain Alignment**: Module boundaries should match domain concepts

**Quality Indicators**:
- ✅ **Clear Purpose**: Can describe module's role in one sentence
- ✅ **Stable Interface**: Function signatures don't change frequently
- ✅ **Minimal Dependencies**: Imports only what's needed
- ✅ **No Duplication**: Identical code extracted to shared utilities

**Warning Signs**:
- ❌ **Mixed Concerns**: Module handles multiple unrelated responsibilities
- ❌ **Excessive Size**: Module too large for effective understanding/modification
- ❌ **Tight Coupling**: Changes in one module frequently require changes in others
- ❌ **Unclear Boundaries**: Difficult to decide where new functionality belongs

### Success Metrics

**Code Quality**:
- **Zero Duplication**: No identical functions across modules
- **Clear Separation**: Data extraction ≠ calculation ≠ visualization
- **Consistent Patterns**: Same structure for similar functionality
- **Domain Alignment**: Code structure matches domain model

**Process Quality**:
- **No Broken Commits**: Every commit represents working code
- **Clear History**: Git log tells story of refactoring decisions
- **Preserved Functionality**: All existing features continue working
- **Enhanced Maintainability**: New features easier to add

**Knowledge Preservation**:
- **Updated Documentation**: Domain model reflects current architecture
- **Captured Patterns**: Successful abstractions documented for reuse
- **Recorded Anti-Patterns**: Failed approaches documented to avoid repetition
- **Clear Guidelines**: Future developers can follow established patterns

---

*This document serves as the authoritative description of our domain model and refactoring methodology. All code should align with these concepts and terminology.*
