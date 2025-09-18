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

**When to AVOID DRY** (Keep Separate):
1. **Similar but different logic**: Same chart type but different data sources
2. **Evolving visualizations**: Charts that may diverge in future (line vs bar, different axes)
3. **Page-specific behavior**: Different click handlers, different navigation flows
4. **Premature abstractions**: When we don't yet understand the full pattern

**Current Code Analysis**:
- **Within page similarities**: 14-week vs 2-week charts differ mainly in aggregation (days→weeks vs days only) and axis scale - potential for careful abstraction
- **Across page similarities**: Same chart types but different data sources - keep separate to allow divergent evolution
- **Time series charts**: Day vs activity charts differ only in x-axis time scale - already well abstracted
- **Activities charts**: Same horizontal bar logic but different data sources (TRIMP vs oxygen debt) - keep separate for now

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

---

*This document serves as the authoritative description of our domain model. All code should align with these concepts and terminology.*
