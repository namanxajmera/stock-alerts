// Ensure Plotly is loaded
if (typeof Plotly === 'undefined') {
    console.error('Plotly.js failed to load. Please check your internet connection.');
}

// Constants
const PERIODS = {
    '1y': { days: 365, interval: '1d' },
    '3y': { days: 1095, interval: '1d' },
    '5y': { days: 1825, interval: '1d' },
    'max': { days: null, interval: '1d' }
};

// Chart configuration
const chartConfig = {
    displayModeBar: false,
    responsive: true,
    staticPlot: false,  // Enable interactivity
    showTips: false     // Disable default tooltips
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
const stockInfoPanel = document.getElementById('stock-info');
const stockNameEl = document.getElementById('stock-name');
const currentPriceEl = document.getElementById('current-price');
const priceChangeEl = document.getElementById('price-change');
const changeValueEl = document.getElementById('change-value');
const changePercentEl = document.getElementById('change-percent');
const customTooltip = document.getElementById('custom-tooltip');
const dashboard = document.querySelector('.dashboard');

// State
let selectedPeriod = '5y'; // Always use lowercase to match server requirements
let currentTicker = '';
let isLoading = false;
let lastData = null;

// Initialize the application
function init() {
    initializeCharts();
    setDefaultPeriod();
    tickerInput.focus();
    
    // Event listeners
    tickerInput.addEventListener('keyup', handleTickerInput);
    periodButtons.forEach(btn => {
        btn.addEventListener('click', handlePeriodChange);
    });
}

function setDefaultPeriod() {
    // Set 5y as default period (lowercase to match server requirements)
    selectedPeriod = '5y';
    const defaultBtn = document.querySelector('[data-period="5y"]');
    if (defaultBtn) {
        defaultBtn.classList.add('selected');
    }
}

// Initialize charts with empty data
function initializeCharts() {
    const commonLayout = {
        showlegend: false,
        margin: { t: 10, r: 40, l: 50, b: 40 },
        plot_bgcolor: 'rgba(0,0,0,0)',
        paper_bgcolor: 'rgba(0,0,0,0)',
        hovermode: 'x unified',
        hoverdistance: 50,
        hoverlabel: { 
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            bordercolor: 'rgba(0, 0, 0, 0.1)',
            font: { 
                family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                size: 12,
                color: '#1D1D1F'
            },
            padding: 8
        },
        xaxis: {
            ...commonAxisStyle,
            showspikes: true,
            spikemode: 'across',
            spikesnap: 'cursor',
            showline: true,
            showgrid: true,
            spikecolor: '#8E8E93',
            spikethickness: 1,
            showticklabels: true,
            tickangle: -45,
            tickfont: {
                family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                size: 10,
                color: '#8E8E93'
            },
            fixedrange: true,  // Prevent zooming on x-axis
            automargin: true,
            rangeslider: { visible: false }  // Disable range slider if present
        }
    };

    const mainChartLayout = {
        ...commonLayout,
        height: 300,
        yaxis: {
            ...commonAxisStyle,
            title: {
                text: 'PRICE (USD)',
                font: {
                    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                    size: 12,
                    weight: 'bold'
                },
                standoff: 10
            },
            automargin: true,
            range: [null, null],
            rangemode: 'normal',
            autorange: true,
            fixedrange: true  // Prevent zooming on y-axis
        }
    };

    const subChartLayout = {
        ...commonLayout,
        height: 200,
        yaxis: {
            ...commonAxisStyle,
            title: {
                text: '% DIFFERENCE',
                font: {
                    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                    size: 12,
                    weight: 'bold'
                },
                standoff: 10
            },
            automargin: true,
            fixedrange: true  // Prevent zooming on y-axis
        }
    };

    try {
        Plotly.newPlot('main-chart', [], mainChartLayout, chartConfig);
        Plotly.newPlot('sub-chart', [], subChartLayout, chartConfig);

        // Add event listeners for synchronized hover
        const mainChartEl = document.getElementById('main-chart');
        const subChartEl = document.getElementById('sub-chart');

        mainChartEl.on('plotly_hover', (data) => {
            if (!data.points || !data.points[0]) return;
            Plotly.Fx.hover(subChartEl, [
                { curveNumber: 0, pointNumber: data.points[0].pointNumber }
            ]);
            updateTooltip(data.points[0]);
        });

        subChartEl.on('plotly_hover', (data) => {
            if (!data.points || !data.points[0]) return;
            Plotly.Fx.hover(mainChartEl, [
                { curveNumber: 0, pointNumber: data.points[0].pointNumber }
            ]);
            updateTooltip(data.points[0]);
        });

        mainChartEl.on('plotly_unhover', () => {
            Plotly.Fx.unhover(subChartEl);
            hideTooltip();
        });

        subChartEl.on('plotly_unhover', () => {
            Plotly.Fx.unhover(mainChartEl);
            hideTooltip();
        });

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
        // Store data for tooltip use
        lastData = data;
        
        // Filter out null values
        const [priceDates, priceValues] = filterNullValues(data.dates, data.prices);
        const [maDates, maValues] = filterNullValues(data.dates, data.ma_200);
        const [diffDates, diffValues] = filterNullValues(data.dates, data.pct_diff);

        if (!priceDates.length || !priceValues.length) {
            throw new Error('No valid price data available');
        }

        // Show dashboard
        dashboard.style.display = 'block';

        // Update stock info panel with the latest data
        updateStockInfo(ticker, priceValues[priceValues.length - 1], priceValues[0]);

        // Main chart traces
        const mainTraces = [
            {
                x: priceDates,
                y: priceValues,
                type: 'scatter',
                mode: 'lines',
                line: { color: '#00C805', width: 2 },
                name: 'Price',
                hovertemplate: '$%{y:.2f}<extra></extra>'
            },
            {
                x: maDates,
                y: maValues,
                type: 'scatter',
                mode: 'lines',
                line: { color: '#8E8E93', width: 2, dash: 'dot' },
                name: '200-Day MA',
                hovertemplate: '$%{y:.2f}<extra></extra>'
            }
        ];

        // Determine color for percent difference line
        let diffColor = '#00C805'; // green by default
        if (diffValues.length > 0 && diffValues[diffValues.length - 1] < 0) {
            diffColor = '#FF5000'; // red if negative
        }

        // Sub chart traces
        const subTraces = [
            {
                x: diffDates,
                y: diffValues,
                type: 'scatter',
                mode: 'lines',
                fill: 'tozeroy',
                fillcolor: diffValues[diffValues.length - 1] >= 0 ? 'rgba(0, 200, 5, 0.1)' : 'rgba(255, 80, 0, 0.1)',
                line: { color: diffColor, width: 2 },
                name: '% Difference',
                hovertemplate: '%{y:.1f}%<extra></extra>'
            },
            {
                x: [data.dates[0], data.dates[data.dates.length - 1]],
                y: [0, 0],
                type: 'scatter',
                mode: 'lines',
                line: { color: '#8E8E93', width: 1, dash: 'dash' },
                name: 'Baseline',
                hoverinfo: 'skip'
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
                    line: { color: '#007AFF', width: 1, dash: 'dash' },
                    name: '5th Percentile',
                    hoverinfo: 'skip',
                    showlegend: false
                },
                {
                    x: [data.dates[0], data.dates[data.dates.length - 1]],
                    y: [data.percentiles.p95, data.percentiles.p95],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: '#5856D6', width: 1, dash: 'dash' },
                    name: '95th Percentile',
                    hoverinfo: 'skip',
                    showlegend: false
                }
            );
        }

        // Calculate y-axis range with padding
        const prices = priceValues.filter(p => p !== null);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const priceRange = maxPrice - minPrice;
        const padding = priceRange * 0.1; // 10% padding

        // Update charts with synchronized ranges
        const xRange = [priceDates[0], priceDates[priceDates.length - 1]];
        
        const mainChartUpdate = {
            ...document.getElementById('main-chart').layout,
            xaxis: {
                ...document.getElementById('main-chart').layout.xaxis,
                range: xRange
            },
            yaxis: {
                ...document.getElementById('main-chart').layout.yaxis,
                range: [minPrice - padding, maxPrice + padding]
            }
        };

        const subChartUpdate = {
            ...document.getElementById('sub-chart').layout,
            xaxis: {
                ...document.getElementById('sub-chart').layout.xaxis,
                range: xRange
            }
        };

        // Update charts
        Plotly.react('main-chart', mainTraces, mainChartUpdate, chartConfig);
        Plotly.react('sub-chart', subTraces, subChartUpdate, chartConfig);

    } catch (error) {
        console.error('Error updating charts:', error);
        showError('Failed to update charts: ' + error.message);
    }
}

// Function to update stock info panel
function updateStockInfo(ticker, currentPrice, firstPrice) {
    stockNameEl.textContent = ticker;
    currentPriceEl.textContent = `$${currentPrice.toFixed(2)}`;
    
    // Calculate price change
    const priceChange = currentPrice - firstPrice;
    const percentChange = (priceChange / firstPrice) * 100;
    
    // Update change elements
    changeValueEl.textContent = `$${priceChange.toFixed(2)}`;
    changePercentEl.textContent = `(${percentChange.toFixed(2)}%)`;
    
    // Set color based on change
    if (priceChange >= 0) {
        priceChangeEl.classList.remove('negative');
        priceChangeEl.classList.add('positive');
    } else {
        priceChangeEl.classList.remove('positive');
        priceChangeEl.classList.add('negative');
    }
    
    // Show the panel
    stockInfoPanel.style.display = 'flex';
}

// Update tooltip content and position
function updateTooltip(point) {
    if (!point || !lastData || !point.event) return;
    
    const date = new Date(point.x).toLocaleDateString();
    let tooltipContent = '';
    
    // Different content based on which chart is being hovered
    if (point.data.name === 'Price' || point.data.name === '200-Day MA') {
        // Main chart (price)
        tooltipContent = `<div>${date} · $${point.y.toFixed(2)}</div>`;
    } else if (point.data.name === '% Difference') {
        // Sub chart (percentile)
        tooltipContent = `<div>${date} · ${point.y.toFixed(1)}%</div>`;
    } else {
        return; // Don't show tooltip for other traces
    }
    
    customTooltip.innerHTML = tooltipContent;
    customTooltip.style.display = 'block';
    
    // Position tooltip using the mouse event coordinates
    const evt = point.event;
    customTooltip.style.left = `${evt.pageX + 10}px`;
    customTooltip.style.top = `${evt.pageY - 20}px`;
}

// Hide tooltip
function hideTooltip() {
    customTooltip.style.display = 'none';
}

// Handle ticker input
function handleTickerInput(event) {
    if (event.key === 'Enter' && !isLoading) {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (ticker && ticker !== currentTicker) {
            currentTicker = ticker;
            fetchData();
        }
    }
}

// Handle period change
function handlePeriodChange(event) {
    if (isLoading) return;
    
    const newPeriod = event.target.dataset.period.toLowerCase(); // Ensure lowercase
    if (newPeriod && newPeriod !== selectedPeriod) {
        updateSelectedPeriod(newPeriod);
        if (currentTicker) {
            fetchData();
        }
    }
}

// Update UI for selected period
function updateSelectedPeriod(newPeriod) {
    selectedPeriod = newPeriod;
    periodButtons.forEach(btn => {
        if (btn.dataset.period === newPeriod) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });
}

// Set loading state
function setLoading(loading) {
    isLoading = loading;
    if (loading) {
        loadingIndicator.classList.add('show');
        tickerInput.disabled = true;
        periodButtons.forEach(btn => btn.disabled = true);
    } else {
        loadingIndicator.classList.remove('show');
        tickerInput.disabled = false;
        periodButtons.forEach(btn => btn.disabled = false);
    }
}

// Show error message
function showError(message) {
    errorMessage.textContent = message;
    setTimeout(() => {
        errorMessage.textContent = '';
    }, 5000);
}

// Fetch data from the server
async function fetchData() {
    if (isLoading) return;
    
    setLoading(true);
    errorMessage.textContent = '';
    
    try {
        const response = await fetch(`/data/${currentTicker}/${selectedPeriod}`);
        const result = await response.json();
        
        if (response.ok) {
            updateCharts(result, currentTicker);
        } else {
            throw new Error(result.error || 'Failed to fetch data');
        }
    } catch (error) {
        console.error('Error fetching data:', error);
        showError(`Error: ${error.message}`);
        clearCharts();
    } finally {
        setLoading(false);
    }
}

// Clear charts
function clearCharts() {
    Plotly.react('main-chart', [], document.getElementById('main-chart').layout, chartConfig);
    Plotly.react('sub-chart', [], document.getElementById('sub-chart').layout, chartConfig);
    stockInfoPanel.style.display = 'none';
    dashboard.style.display = 'none';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init); 