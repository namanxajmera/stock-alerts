// Since we're using the CDN version of Plotly, we don't need to import it
// The Plotly object is available globally from the CDN script

// Main application module to encapsulate state and behavior
const StockAnalyzer = (() => {
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
        staticPlot: false, // Enable interactivity
        showTips: false, // Disable default tooltips
        autosize: true // Enable autosize
    };

    // Common layout properties
    const commonAxisStyle = {
        showgrid: false,
        zeroline: false,
        tickfont: {
            family: 'Arial',
            size: 13,
            color: 'black'
        },
        fixedrange: true,
    };

    // DOM Elements (cached for performance)
    const DOM = {
        tickerInput: document.getElementById('ticker-input'),
        periodButtons: document.querySelectorAll('.period-btn'),
        mainChart: document.getElementById('main-chart'),
        subChart: document.getElementById('sub-chart'),
        loadingIndicator: document.querySelector('.loading-indicator'),
        errorMessage: document.querySelector('.error-message'),
        stockInfoPanel: document.getElementById('stock-info'),
        stockNameEl: document.getElementById('stock-name'),
        currentPriceEl: document.getElementById('current-price'),
        priceChangeEl: document.getElementById('price-change'),
        changeValueEl: document.getElementById('change-value'),
        changePercentEl: document.getElementById('change-percent'),
        customTooltip: document.getElementById('custom-tooltip'),
        dashboard: document.querySelector('.dashboard')
    };

    // Application state
    const state = {
        selectedPeriod: '5y',
        currentTicker: '',
        isLoading: false,
        chartDataCache: null,
        resizeTimeout: null
    };

    // Initialize the application
    function init() {
        initializeCharts();
        setDefaultPeriod();
        DOM.tickerInput.focus();
        setupEventListeners();
    }

    // Set up all event listeners
    function setupEventListeners() {
        DOM.tickerInput.addEventListener('keyup', handleTickerInput);
        DOM.periodButtons.forEach(btn => {
            btn.addEventListener('click', handlePeriodChange);
        });
        window.addEventListener('resize', handleResize);
    }

    function setDefaultPeriod() {
        // Set 5y as default period (lowercase to match server requirements)
        state.selectedPeriod = '5y';
        const defaultBtn = document.querySelector('[data-period="5y"]');
        if (defaultBtn) {
            defaultBtn.classList.add('selected');
        }
    }

    // Initialize charts with empty data
    function initializeCharts() {
        const commonLayout = {
            showlegend: false,
            margin: { t: 10, r: 10, l: 50, b: 40 }, // Reduced right margin
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            hovermode: 'x unified',
            hoverdistance: 50,
            autosize: true, // Enable autosize
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
            xaxis: Object.assign(Object.assign({}, commonAxisStyle), { showspikes: true, spikemode: 'across', spikesnap: 'cursor', showline: true, showgrid: true, spikecolor: '#8E8E93', spikethickness: 1, showticklabels: true, tickangle: -45, tickfont: {
                    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                    size: 10,
                    color: '#8E8E93'
                }, fixedrange: true, automargin: true, rangeslider: { visible: false } // Disable range slider if present
             })
        };
        const mainChartLayout = Object.assign(Object.assign({}, commonLayout), { height: 300, yaxis: Object.assign(Object.assign({}, commonAxisStyle), { title: {
                    text: 'PRICE (USD)',
                    font: {
                        family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                        size: 12,
                        weight: 500
                    },
                    standoff: 10
                }, automargin: true, range: [null, null], rangemode: 'normal', autorange: true, fixedrange: true }), xaxis: Object.assign(Object.assign({}, commonAxisStyle), { showspikes: true, spikemode: 'across', spikesnap: 'cursor', showline: true, showgrid: true, spikecolor: '#8E8E93', spikethickness: 1, showticklabels: true, tickangle: -45, tickfont: {
                    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                    size: 10,
                    color: '#8E8E93'
                }, fixedrange: true, automargin: true, rangeslider: { visible: false } }) });
        const subChartLayout = Object.assign(Object.assign({}, commonLayout), { height: 200, yaxis: Object.assign(Object.assign({}, commonAxisStyle), { title: {
                    text: '% DIFFERENCE',
                    font: {
                        family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                        size: 12,
                        weight: 500
                    },
                    standoff: 10
                }, automargin: true, fixedrange: true }), xaxis: Object.assign(Object.assign({}, commonAxisStyle), { showspikes: true, spikemode: 'across', spikesnap: 'cursor', showline: true, showgrid: true, spikecolor: '#8E8E93', spikethickness: 1, showticklabels: true, tickangle: -45, tickfont: {
                    family: '-apple-system, BlinkMacSystemFont, Segoe UI, Roboto',
                    size: 10,
                    color: '#8E8E93'
                }, fixedrange: true, automargin: true, rangeslider: { visible: false } }) });
        try {
            window.Plotly.newPlot('main-chart', [], mainChartLayout, chartConfig);
            window.Plotly.newPlot('sub-chart', [], subChartLayout, chartConfig);
            // Add event listeners for synchronized hover
            const mainChartEl = document.getElementById('main-chart');
            const subChartEl = document.getElementById('sub-chart');
            mainChartEl.on('plotly_hover', (data) => {
                var _a;
                if (!((_a = data.points) === null || _a === void 0 ? void 0 : _a[0]))
                    return;
                window.Plotly.Fx.hover(subChartEl, [
                    { curveNumber: 0, pointNumber: data.points[0].pointNumber }
                ]);
                updateTooltip(data.points[0]);
            });
            subChartEl.on('plotly_hover', (data) => {
                var _a;
                if (!((_a = data.points) === null || _a === void 0 ? void 0 : _a[0]))
                    return;
                window.Plotly.Fx.hover(mainChartEl, [
                    { curveNumber: 0, pointNumber: data.points[0].pointNumber }
                ]);
                updateTooltip(data.points[0]);
            });
            mainChartEl.on('plotly_unhover', () => {
                window.Plotly.Fx.unhover(subChartEl);
                hideTooltip();
            });
            subChartEl.on('plotly_unhover', () => {
                window.Plotly.Fx.unhover(mainChartEl);
                hideTooltip();
            });
        }
        catch (error) {
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
            state.chartDataCache = data;
            // Filter out null values
            const [priceDates, priceValues] = filterNullValues(data.dates, data.prices);
            const [maDates, maValues] = filterNullValues(data.dates, data.ma_200);
            const [diffDates, diffValues] = filterNullValues(data.dates, data.pct_diff);
            if (!priceDates.length || !priceValues.length) {
                throw new Error('No data available');
            }
            // Show dashboard
            DOM.dashboard.style.display = 'block';
            // Update stock info panel with the latest data
            updateStockInfo(ticker, priceValues[priceValues.length - 1], data.previous_close);
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
            if (data.percentiles && data.percentiles.p16 !== null && data.percentiles.p84 !== null) {
                subTraces.push({
                    x: [data.dates[0], data.dates[data.dates.length - 1]],
                    y: [data.percentiles.p16, data.percentiles.p16],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: '#007AFF', width: 1, dash: 'dash' },
                    name: '16th Percentile',
                    hoverinfo: 'skip',
                    showlegend: false
                }, {
                    x: [data.dates[0], data.dates[data.dates.length - 1]],
                    y: [data.percentiles.p84, data.percentiles.p84],
                    type: 'scatter',
                    mode: 'lines',
                    line: { color: '#5856D6', width: 1, dash: 'dash' },
                    name: '84th Percentile',
                    hoverinfo: 'skip',
                    showlegend: false
                });
            }
            // Calculate y-axis range with padding
            const prices = priceValues.filter(p => p !== null);
            const minPrice = Math.min(...prices);
            const maxPrice = Math.max(...prices);
            const priceRange = maxPrice - minPrice;
            const padding = priceRange * 0.1; // 10% padding
            // Update main chart layout
            const mainChartLayout = {
                autosize: true,
                margin: { t: 10, r: 10, l: 50, b: 40 },
                yaxis: {
                    range: [minPrice - padding, maxPrice + padding],
                    automargin: true,
                    fixedrange: true
                },
                xaxis: {
                    automargin: true,
                    fixedrange: true
                }
            };
            // Sub chart traces with proper layout
            const subChartLayout = {
                autosize: true,
                margin: { t: 10, r: 10, l: 50, b: 40 },
                yaxis: {
                    automargin: true,
                    fixedrange: true
                },
                xaxis: {
                    automargin: true,
                    fixedrange: true
                }
            };
            // Update charts with proper config
            window.Plotly.react('main-chart', mainTraces, mainChartLayout, chartConfig);
            window.Plotly.react('sub-chart', subTraces, subChartLayout, chartConfig);
            // Add window resize handler
            const updateSize = () => {
                window.Plotly.Plots.resize('main-chart');
                window.Plotly.Plots.resize('sub-chart');
            };
            // Debounce resize handler
            state.resizeTimeout = window.setTimeout(updateSize, 100);
        }
        catch (error) {
            console.error('Error updating charts:', error);
            showError('Failed to update charts');
        }
    }

    // Function to update stock info panel
    function updateStockInfo(ticker, currentPrice, previousClose) {
        DOM.stockNameEl.textContent = ticker;
        DOM.currentPriceEl.textContent = `$${currentPrice.toFixed(2)}`;
        // Calculate price change
        let priceChange = 0;
        let percentChange = 0;
        if (previousClose !== null) {
            priceChange = currentPrice - previousClose;
            percentChange = (priceChange / previousClose) * 100;
        }
        // Update change elements
        DOM.changeValueEl.textContent = `${priceChange >= 0 ? '+' : ''}$${priceChange.toFixed(2)}`;
        DOM.changePercentEl.textContent = `(${percentChange.toFixed(2)}%)`;
        // Set color based on change
        if (priceChange >= 0) {
            DOM.priceChangeEl.classList.remove('negative');
            DOM.priceChangeEl.classList.add('positive');
        }
        else {
            DOM.priceChangeEl.classList.remove('positive');
            DOM.priceChangeEl.classList.add('negative');
        }
        // Show the panel
        DOM.stockInfoPanel.style.display = 'flex';
    }

    // Update tooltip content and position
    function updateTooltip(point) {
        if (!point || !point.x)
            return;
        const date = new Date(point.x).toLocaleDateString();
        let value = '';
        if (point.data.name === 'Price' || point.data.name === '200-Day MA') {
            value = `$${point.y.toFixed(2)}`;
        }
        else if (point.data.name === '% Difference') {
            value = `${point.y.toFixed(1)}%`;
        }
        else {
            return; // Don't show tooltip for other traces
        }
        DOM.customTooltip.innerHTML = `<div>${date} · ${value}</div>`;
        DOM.customTooltip.style.display = 'block';
        // Position tooltip using the mouse event coordinates
        const evt = point.event;
        DOM.customTooltip.style.left = `${evt.pageX + 10}px`;
        DOM.customTooltip.style.top = `${evt.pageY - 20}px`;
    }

    // Hide tooltip
    function hideTooltip() {
        DOM.customTooltip.style.display = 'none';
    }

    // Handle ticker input
    function handleTickerInput(event) {
        if (event.key === 'Enter' && !state.isLoading) {
            const ticker = DOM.tickerInput.value.trim().toUpperCase();
            if (ticker && ticker !== state.currentTicker) {
                state.currentTicker = ticker;
                fetchData();
            }
        }
    }

    // Handle period change
    function handlePeriodChange(event) {
        var _a;
        if (state.isLoading)
            return;
        const button = event.target;
        const newPeriod = ((_a = button.dataset.period) === null || _a === void 0 ? void 0 : _a.toLowerCase()) || '';
        if (newPeriod && newPeriod !== state.selectedPeriod) {
            updateSelectedPeriod(newPeriod);
            if (state.currentTicker) {
                fetchData();
            }
        }
    }

    // Update UI for selected period
    function updateSelectedPeriod(newPeriod) {
        state.selectedPeriod = newPeriod;
        DOM.periodButtons.forEach(btn => {
            if (btn.dataset.period === newPeriod) {
                btn.classList.add('selected');
                btn.setAttribute('aria-pressed', 'true');
            }
            else {
                btn.classList.remove('selected');
                btn.setAttribute('aria-pressed', 'false');
            }
        });
    }

    // Set loading state
    function setLoading(loading) {
        state.isLoading = loading;
        if (loading) {
            DOM.loadingIndicator.classList.add('show');
            DOM.tickerInput.disabled = true;
            DOM.periodButtons.forEach(btn => btn.disabled = true);
        }
        else {
            DOM.loadingIndicator.classList.remove('show');
            DOM.tickerInput.disabled = false;
            DOM.periodButtons.forEach(btn => btn.disabled = false);
        }
    }

    // Show error message
    function showError(message) {
        DOM.errorMessage.textContent = message;
        setTimeout(() => {
            DOM.errorMessage.textContent = '';
        }, 5000);
    }

    // Fetch data from the server
    async function fetchData() {
        if (state.isLoading)
            return;
        setLoading(true);
        DOM.errorMessage.textContent = '';
        try {
            const response = await fetch(`/data/${state.currentTicker}/${state.selectedPeriod}`);
            const result = await response.json();
            if (response.ok) {
                updateCharts(result, state.currentTicker);
            }
            else {
                throw new Error(result.error || 'Failed to fetch data');
            }
        }
        catch (error) {
            console.error('Error fetching data:', error);
            const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
            showError(`Error: ${errorMessage}`);
            clearCharts();
        }
        finally {
            setLoading(false);
        }
    }

    // Clear charts
    function clearCharts() {
        const mainChartEl = document.getElementById('main-chart');
        const subChartEl = document.getElementById('sub-chart');
        window.Plotly.react('main-chart', [], (mainChartEl === null || mainChartEl === void 0 ? void 0 : mainChartEl.layout) || {}, chartConfig);
        window.Plotly.react('sub-chart', [], (subChartEl === null || subChartEl === void 0 ? void 0 : subChartEl.layout) || {}, chartConfig);
        DOM.stockInfoPanel.style.display = 'none';
        DOM.dashboard.style.display = 'none';
    }

    function handleResize() {
        clearTimeout(state.resizeTimeout);
        state.resizeTimeout = window.setTimeout(() => {
            window.Plotly.Plots.resize('main-chart');
            window.Plotly.Plots.resize('sub-chart');
        }, 100);
    }

    // Initialize on page load
    document.addEventListener('DOMContentLoaded', init);

    return {
        init: init,
        setDefaultPeriod: setDefaultPeriod,
        initializeCharts: initializeCharts,
        filterNullValues: filterNullValues,
        updateCharts: updateCharts,
        updateStockInfo: updateStockInfo,
        updateTooltip: updateTooltip,
        hideTooltip: hideTooltip,
        handleTickerInput: handleTickerInput,
        handlePeriodChange: handlePeriodChange,
        updateSelectedPeriod: updateSelectedPeriod,
        setLoading: setLoading,
        showError: showError,
        fetchData: fetchData,
        clearCharts: clearCharts,
        handleResize: handleResize
    };
})();
