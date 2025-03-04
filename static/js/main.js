// Ensure Plotly is loaded
if (typeof Plotly === 'undefined') {
    console.error('Plotly.js failed to load. Please check your internet connection.');
}

// Constants
const PERIODS = {
    '1D': { days: 1, interval: '5m' },
    '1W': { days: 7, interval: '15m' },
    '1M': { days: 30, interval: '1h' },
    '3M': { days: 90, interval: '1d' },
    '6M': { days: 180, interval: '1d' },
    '1Y': { days: 365, interval: '1d' },
    '5Y': { days: 1825, interval: '1d' }
};

// Chart configuration
const chartConfig = {
    displayModeBar: false,
    responsive: true,
    staticPlot: true  // Disable all interactivity as per requirements
};

// Common layout properties
const commonAxisStyle = {
    showgrid: false,
    zeroline: false,
    tickfont: {
        family: 'Arial',
        size: 13,
        color: 'black'
    }
};

// DOM Elements
const tickerInput = document.getElementById('ticker-input');
const periodButtons = document.querySelectorAll('.period-btn');
const mainChart = document.getElementById('main-chart');
const subChart = document.getElementById('sub-chart');
const loadingIndicator = document.querySelector('.loading-indicator');
const errorMessage = document.querySelector('.error-message');

// State
let selectedPeriod = '1D';
let currentTicker = '';
let isLoading = false;

// Initialize the application
function init() {
    initializeCharts();
    setDefaultPeriod();
    tickerInput.focus();
}

function setDefaultPeriod() {
    // Set 1Y as default period
    selectedPeriod = '1Y';
    const defaultBtn = document.querySelector(`[data-period="1y"]`);
    if (defaultBtn) {
        defaultBtn.classList.add('selected');
    }
}

// Initialize charts with empty data
function initializeCharts() {
    const mainChartLayout = {
        height: 400,
        margin: { t: 40, r: 10, l: 50, b: 0 },
        showlegend: false,
        xaxis: {
            ...commonAxisStyle,
            showticklabels: false
        },
        yaxis: {
            ...commonAxisStyle,
            title: {
                text: 'PRICE (USD)',
                font: {
                    family: 'Arial',
                    size: 13,
                    weight: 'bold'
                }
            }
        },
        title: {
            text: '',
            font: {
                family: 'Arial',
                size: 13,
                weight: 'bold'
            },
            y: 0.95
        }
    };

    const subChartLayout = {
        height: 250,
        margin: { t: 0, r: 10, l: 50, b: 30 },
        showlegend: false,
        xaxis: commonAxisStyle,
        yaxis: {
            ...commonAxisStyle,
            title: {
                text: '% DIFFERENCE',
                font: {
                    family: 'Arial',
                    size: 13,
                    weight: 'bold'
                }
            }
        }
    };

    try {
        Plotly.newPlot('main-chart', [], mainChartLayout, chartConfig);
        Plotly.newPlot('sub-chart', [], subChartLayout, chartConfig);
    } catch (error) {
        console.error('Error initializing charts:', error);
        showError('Failed to initialize charts');
    }
}

// Filter out null values from data
function filterNullValues(dates, values) {
    const filtered = dates.reduce((acc, date, i) => {
        if (values[i] !== null) {
            acc.dates.push(date);
            acc.values.push(values[i]);
        }
        return acc;
    }, { dates: [], values: [] });
    return [filtered.dates, filtered.values];
}

// Update charts with new data
function updateCharts(data, ticker) {
    try {
        // Filter out null values
        const [priceDates, priceValues] = filterNullValues(data.dates, data.prices);
        const [maDates, maValues] = filterNullValues(data.dates, data.ma_200);
        const [diffDates, diffValues] = filterNullValues(data.dates, data.pct_diff);

        if (!priceDates.length || !priceValues.length) {
            throw new Error('No valid price data available');
        }

        // Main chart traces
        const mainTraces = [
            {
                x: priceDates,
                y: priceValues,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'blue', width: 1 }
            },
            {
                x: maDates,
                y: maValues,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'black', width: 2 }
            }
        ];

        // Sub chart traces
        const subTraces = [
            {
                x: diffDates,
                y: diffValues,
                type: 'scatter',
                mode: 'lines',
                line: { color: 'lightblue', width: 1 }
            },
            {
                x: [data.dates[0], data.dates[data.dates.length - 1]],
                y: [0, 0],
                type: 'scatter',
                mode: 'lines',
                line: { color: 'gray', width: 1, dash: 'dash' }
            }
        ];

        // Only add percentile lines if we have valid percentiles
        if (data.percentiles && data.percentiles.p5 !== null && data.percentiles.p95 !== null) {
            subTraces.push(
                {
                    x: [data.dates[0], data.dates[data.dates.length - 1]],
                    y: [data.percentiles.p5, data.percentiles.p5],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: 'purple', width: 2 }
                },
                {
                    x: [data.dates[0], data.dates[data.dates.length - 1]],
                    y: [data.percentiles.p95, data.percentiles.p95],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: 'orange', width: 2 }
                }
            );
        }

        // Add percentile labels if we have valid percentiles
        const annotations = [];
        if (data.percentiles && data.percentiles.p5 !== null && data.percentiles.p95 !== null) {
            const lastDate = data.dates[data.dates.length - 1];
            annotations.push(
                {
                    x: lastDate,
                    y: data.percentiles.p5,
                    text: ' 5TH',
                    showarrow: false,
                    font: {
                        family: 'Arial',
                        size: 13,
                        weight: 'bold'
                    },
                    xanchor: 'left',
                    yanchor: 'top'
                },
                {
                    x: lastDate,
                    y: data.percentiles.p95,
                    text: ' 95TH',
                    showarrow: false,
                    font: {
                        family: 'Arial',
                        size: 13,
                        weight: 'bold'
                    },
                    xanchor: 'left',
                    yanchor: 'bottom'
                }
            );
        }

        // Update main chart
        Plotly.react('main-chart', mainTraces, {
            ...document.getElementById('main-chart').layout,
            title: {
                text: `${ticker} CLOSING PRICE AND 200-DAY MOVING AVERAGE`,
                font: {
                    family: 'Arial',
                    size: 13,
                    weight: 'bold'
                }
            }
        }, chartConfig);

        // Update sub chart
        Plotly.react('sub-chart', subTraces, {
            ...document.getElementById('sub-chart').layout,
            annotations
        }, chartConfig);

        return true;
    } catch (error) {
        console.error('Error updating charts:', error);
        showError('Failed to update charts');
        return false;
    }
}

// Event Listeners
tickerInput.addEventListener('keypress', handleTickerInput);
periodButtons.forEach(btn => btn.addEventListener('click', handlePeriodChange));

// Event Handlers
function handleTickerInput(event) {
    if (event.key === 'Enter') {
        const newTicker = tickerInput.value.trim().toUpperCase();
        if (newTicker && newTicker !== currentTicker) {
            currentTicker = newTicker;
            fetchData();
        }
    }
}

function handlePeriodChange(event) {
    const newPeriod = event.target.dataset.period;
    if (newPeriod && newPeriod !== selectedPeriod) {
        updateSelectedPeriod(newPeriod);
        if (currentTicker) {
            fetchData();
        }
    }
}

function updateSelectedPeriod(newPeriod) {
    selectedPeriod = newPeriod;
    periodButtons.forEach(btn => {
        btn.classList.toggle('selected', btn.dataset.period === newPeriod);
    });
}

// UI State Management
function setLoading(loading) {
    isLoading = loading;
    tickerInput.disabled = loading;
    periodButtons.forEach(btn => btn.disabled = loading);
    loadingIndicator.classList.toggle('show', loading);
    
    if (loading) {
        errorMessage.textContent = '';
    }
}

function showError(message) {
    errorMessage.textContent = message;
}

// Data Fetching and Chart Updates
async function fetchData() {
    if (isLoading) return;
    
    setLoading(true);
    
    try {
        const response = await fetch(`/data/${currentTicker}/${selectedPeriod.toLowerCase()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        updateCharts(data, currentTicker);
        showError('');
    } catch (error) {
        console.error('Error fetching data:', error);
        showError(error.message || 'An error occurred while fetching data');
        clearCharts();
    } finally {
        setLoading(false);
    }
}

function clearCharts() {
    Plotly.purge(mainChart);
    Plotly.purge(subChart);
}

// Initialize the app
init(); 