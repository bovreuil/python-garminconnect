// period_url_logic.test.js
// Node.js tests for period and URL logic
const assert = require('assert');

// Import the tested navigation functions
const {
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
} = require('../static/js/navigation.js');

// --- Test data ---
const fixedToday = '2025-07-22';

// A. Two-week period calculation tests
const A = [
    // [date, preferSecondWeek, expectedStart, expectedEnd]
    ['2025-07-15', false, '2025-07-14', '2025-07-27'],
    ['2025-07-15', true, '2025-07-07', '2025-07-20'],
    ['2025-07-20', false, '2025-07-14', '2025-07-27'],
    ['2025-07-20', true, '2025-07-07', '2025-07-20'],
    ['2025-07-21', false, '2025-07-21', '2025-08-03'],
    ['2025-07-21', true, '2025-07-14', '2025-07-27'],
    ['2025-07-14', false, '2025-07-14', '2025-07-27'],
    ['2025-07-27', false, '2025-07-21', '2025-08-03'],
    ['2025-07-27', true, '2025-07-14', '2025-07-27'],
];

// B. Date-in-period tests
const B = [
    // [date, periodStart, periodEnd, expected]
    ['2025-07-14', '2025-07-14', '2025-07-27', true],
    ['2025-07-15', '2025-07-14', '2025-07-27', true],
    ['2025-07-27', '2025-07-14', '2025-07-27', true],
    ['2025-07-13', '2025-07-14', '2025-07-27', false],
    ['2025-07-28', '2025-07-14', '2025-07-27', false],
];

// C. URL parsing tests
const C = [
    // [input, expectedPeriodStart, expectedPeriodEnd, expectedDay, expectedActivityId]
    ['/2025-07-14-2025-07-27', '2025-07-14', '2025-07-27', null, null],
    ['/2025-07-14-2025-07-27/2025-07-15', '2025-07-14', '2025-07-27', '2025-07-15', null],
    ['/2025-07-14-2025-07-27/2025-07-15/123456789', '2025-07-14', '2025-07-27', '2025-07-15', '123456789'],
    ['/2025-07-07-2025-07-20/2025-07-15', '2025-07-07', '2025-07-20', '2025-07-15', null],
    ['/', null, null, null, null], // Default case
];

// D. URL Correction/Validation (today = 2025-07-22)
const D = [
    // Input, Expected
    ['/2025-07-13-2025-07-27/2025-07-15', '/2025-07-14-2025-07-27/2025-07-22'],
    ['/2025-07-14-2025-07-27/2025-07-13', '/2025-07-07-2025-07-20/2025-07-13'],
    ['/2025-07-14-2025-07-27/2025-07-28', '/2025-07-21-2025-08-03/2025-07-28'],
    ['/2025-07-14-2025-07-27/2025-07-15/999999999', '/2025-07-14-2025-07-27/2025-07-15'],
    ['/2025-07-14-2025-07-27/2025-07-15/', '/2025-07-14-2025-07-27/2025-07-15'],
    ['/2025-07-14-2025-07-27/2025-01-01', '/2024-12-30-2025-01-12/2025-01-01'],
];

// E. Navigation tests
const E = [
    // [action, startUrl, expected]
    ['twoWeekLeft', '/2025-07-14-2025-07-27/2025-07-15', '/2025-07-07-2025-07-20'],
    ['twoWeekRight', '/2025-07-14-2025-07-27/2025-07-15', '/2025-07-21-2025-08-03'],
    ['singleDayLeftIn', '/2025-07-14-2025-07-27/2025-07-15', '/2025-07-14-2025-07-27/2025-07-14'],
    ['singleDayLeftOut', '/2025-07-14-2025-07-27/2025-07-14', '/2025-07-07-2025-07-20/2025-07-13'],
    ['singleDayRightIn', '/2025-07-14-2025-07-27/2025-07-26', '/2025-07-14-2025-07-27/2025-07-27'],
    ['singleDayRightOut', '/2025-07-14-2025-07-27/2025-07-27', '/2025-07-21-2025-08-03/2025-07-28'],
    ['today', '/', '/2025-07-14-2025-07-27/2025-07-22'],
    ['singleDayLeft2to1', '/2025-07-14-2025-07-27/2025-07-21', '/2025-07-14-2025-07-27/2025-07-20'],
    ['singleDayRight1to2', '/2025-07-14-2025-07-27/2025-07-20', '/2025-07-14-2025-07-27/2025-07-21'],
];

// --- Test runner ---
let passed = 0;
let failed = 0;

// A. Two-week period calculation tests
A.forEach(([date, preferSecondWeek, expectedStart, expectedEnd], i) => {
    test(`A${i+1}: getTwoWeekPeriod(${date}, ${preferSecondWeek})`, () => {
        const { start, end } = getTwoWeekPeriod(date, preferSecondWeek);
        assert.strictEqual(dateStr(start), expectedStart);
        assert.strictEqual(dateStr(end), expectedEnd);
    });
});

// B. Date-in-period tests
B.forEach(([date, periodStart, periodEnd, expected], i) => {
    test(`B${i+1}: isDateInPeriod(${date}, ${periodStart}, ${periodEnd})`, () => {
        const result = isDateInPeriod(date, periodStart, periodEnd);
        assert.strictEqual(result, expected);
    });
});

// C. URL parsing tests
C.forEach(([input, expectedPeriodStart, expectedPeriodEnd, expectedDay, expectedActivityId], i) => {
    test(`C${i+1}: parseURL(${input})`, () => {
        const result = parseURL(input);
        if (expectedPeriodStart === null) {
            assert.strictEqual(result, null);
        } else {
            assert.strictEqual(dateStr(result.periodStart), expectedPeriodStart);
            assert.strictEqual(dateStr(result.periodEnd), expectedPeriodEnd);
            assert.strictEqual(result.day || null, expectedDay);
            assert.strictEqual(result.activityId || null, expectedActivityId);
        }
    });
});

// D. URL correction tests
D.forEach(([input, expected], i) => {
    test(`D${i+1}: URL correction for ${input}`, () => {
        const url = correctURL(input, fixedToday);
        assert.strictEqual(url, expected);
    });
});

// E. Navigation tests
E.forEach(([action, startUrl, expected], i) => {
    test(`E${i+1}: Navigation ${action} from ${startUrl}`, () => {
        let url = '';
        if (action === 'twoWeekLeft') {
            url = navigateTwoWeekLeft(startUrl);
        } else if (action === 'twoWeekRight') {
            url = navigateTwoWeekRight(startUrl);
        } else if (action.startsWith('singleDay')) {
            if (action.includes('Left')) {
                url = navigateSingleDayLeft(startUrl);
            } else if (action.includes('Right')) {
                url = navigateSingleDayRight(startUrl);
            }
        } else if (action === 'today') {
            url = navigateToday();
        }
        assert.strictEqual(url, expected);
    });
});

function test(name, fn) {
    try {
        fn();
        console.log(`✓ ${name}`);
        passed++;
    } catch (error) {
        console.log(`✗ ${name}`);
        console.log(`  ${error.message}`);
        failed++;
    }
}

console.log(`\n${passed} passed, ${failed} failed.`); 