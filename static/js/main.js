// ApexCharts is available globally from the CDN script

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
            family: 'var(--font-family-main)',
            size: 12,
            color: 'var(--text-secondary)'
        },
        fixedrange: true,
    };

    const commonLayout = {
        showlegend: false,
        margin: { t: 10, r: 10, l: 50, b: 40 },
        plot_bgcolor: 'transparent',
        paper_bgcolor: 'transparent',
        hovermode: 'x unified',
        dragmode: false,
        autosize: true,
        hoverlabel: {
            bgcolor: 'rgba(255, 255, 255, 0.9)',
            bordercolor: 'var(--border-primary)',
            font: {
                family: 'var(--font-family-main)',
                size: 12,
                color: 'var(--text-primary)'
            },
        },
        xaxis: {
            ...commonAxisStyle,
            showspikes: true,
            spikemode: 'across',
            spikesnap: 'cursor',
            showline: true,
            showgrid: true,
            spikecolor: 'var(--border-secondary)',
            spikethickness: 1,
            automargin: true,
            tickangle: -45,
        }
    };

    // DOM Elements (cached for performance)
    const DOM = {
        appContainer: document.querySelector('.app-container'),
        initialView: document.querySelector('.initial-view'),
        headerSearchControls: document.getElementById('header-search-controls'),
        searchControls: document.querySelector('.search-controls'),
        tickerInput: document.getElementById('ticker-input'),
        periodButtons: document.querySelectorAll('.period-btn'),
        mainChart: document.getElementById('main-chart'),
        subChart: document.getElementById('sub-chart'),
        loadingIndicator: document.getElementById('loading-indicator'),
        errorMessage: document.getElementById('error-message'),
        dashboard: document.querySelector('.dashboard'),
        statsBanner: document.getElementById('stats-banner'),
        
        // Stock Info in Chart Header
        stockNameTitle: document.getElementById('stock-name-title'),
        currentPrice: document.getElementById('current-price'),
        priceChange: document.getElementById('price-change'),

        // Simplified Stats
        fearDays: document.getElementById('fear-days'),
        fearAvgPrice: document.getElementById('fear-avg-price'),
        fearVsCurrent: document.getElementById('fear-vs-current'),

        // Momentum Value
        momentumValue: document.getElementById('momentum-value'),



        customTooltip: document.getElementById('custom-tooltip'),
    };

    // Application state
    const state = {
        selectedPeriod: '5y',
        currentTicker: '',
        isLoading: false,
        mainChartInstance: null,
        subChartInstance: null,
        isDashboardActive: false, // Track if we have transitioned to dashboard view
        // Cache for hover-off state restoration
        lastPrice: null,
        previousClose: null,
        lastDiffValue: null,
        // Debounce tracking
        debounceTimer: null,
        // Chart optimization tracking
        lastDiffColor: null,
    };

    // Utility function for debouncing
    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(state.debounceTimer);
            state.debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // Debounced version of fetchData with 200ms delay
    const debouncedFetchData = debounce(fetchData, 200);

    // Initialize the application
    function init() {
        initializeCharts();
        setDefaultPeriod();
        DOM.tickerInput.focus();
        setupEventListeners();
        setupMobileOptimizations();
    }

    // Mobile-specific optimizations
    function setupMobileOptimizations() {
        // Handle window resize for chart responsiveness
        window.addEventListener('resize', debounce(() => {
            if (state.mainChartInstance) {
                state.mainChartInstance.updateOptions({
                    chart: {
                        height: window.innerWidth <= 768 ? 300 : 400
                    }
                });
            }
            if (state.subChartInstance) {
                state.subChartInstance.updateOptions({
                    chart: {
                        height: window.innerWidth <= 768 ? 200 : 250
                    }
                });
            }
        }, 250));

        // Disable chart animations on mobile for better performance
        if (window.innerWidth <= 768) {
            const mobileOptions = {
                chart: {
                    animations: {
                        enabled: false
                    }
                }
            };
            
            if (state.mainChartInstance) {
                state.mainChartInstance.updateOptions(mobileOptions);
            }
            if (state.subChartInstance) {
                state.subChartInstance.updateOptions(mobileOptions);
            }
        }
    }

    // Debounce utility function
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Set up all event listeners
    function setupEventListeners() {
        DOM.tickerInput.addEventListener('keyup', handleTickerInput);
        DOM.periodButtons.forEach(btn => {
            btn.addEventListener('click', handlePeriodChange);
        });
    }

    // Activates the main dashboard view after the first search
    function activateDashboardView() {
        if (state.isDashboardActive) return;
        DOM.headerSearchControls.appendChild(DOM.searchControls);
        DOM.appContainer.classList.add('dashboard-active');
        DOM.dashboard.style.display = 'block';
        state.isDashboardActive = true;
    }

    function setDefaultPeriod() {
        state.selectedPeriod = '5y';
        const defaultBtn = document.querySelector('[data-period="5y"]');
        if (defaultBtn) defaultBtn.classList.add('selected');
    }

    // Initialize charts with ApexCharts
    function initializeCharts() {
        const commonOptions = {
            chart: {
                type: 'line',
                height: 350,
                group: 'stock-charts', // Syncs tooltips and crosshairs
                toolbar: { show: false },
                zoom: { enabled: false },
                events: {
                    mouseMove: handleChartMouseMove,
                    mouseLeave: handleChartMouseLeave,
                }
            },
            dataLabels: { enabled: false },
            stroke: { width: 2, curve: 'straight' },
            grid: {
                borderColor: 'var(--border-primary)',
                xaxis: { lines: { show: true } },
                yaxis: { lines: { show: false } }
            },
            xaxis: {
                type: 'datetime',
                tickAmount: 6,
                labels: {
                    style: {
                        colors: 'var(--text-secondary)',
                        fontFamily: 'var(--font-family-main)',
                    },
                },
                axisBorder: { show: false },
                axisTicks: { show: false },
                tooltip: { enabled: false }, // Hide x-axis tooltip line
            },
            yaxis: {
                opposite: false,
                labels: {
                    style: {
                        colors: 'var(--text-secondary)',
                        fontFamily: 'var(--font-family-main)',
                    },
                    formatter: (val) => val.toFixed(0) // Default formatter
                },
            },
            tooltip: {
                x: { format: 'dd MMM yyyy' },
                shared: true,
                theme: 'light',
                style: {
                    fontFamily: 'var(--font-family-main)',
                },
                marker: { show: true },
            },
            legend: {
                show: true,
                position: 'top',
                horizontalAlign: 'right',
                floating: true,
                offsetY: -5,
                fontFamily: 'var(--font-family-main)',
                markers: {
                    width: 16,
                    height: 2,
                    radius: 0,
                },
                itemMargin: {
                    horizontal: 10,
                },
            }
        };

        // Responsive chart heights
        const isMobile = window.innerWidth <= 768;
        const mainHeight = isMobile ? 300 : 400;
        const subHeight = isMobile ? 200 : 250;

        const mainChartOptions = {
            ...commonOptions,
            chart: { 
                ...commonOptions.chart, 
                type: 'line', 
                height: mainHeight,
                animations: {
                    enabled: !isMobile
                }
            },
            series: [],
            colors: ['var(--green-primary)', 'var(--text-secondary)'],
            yaxis: {
                ...commonOptions.yaxis,
                labels: {
                    ...commonOptions.yaxis.labels,
                    formatter: (val) => `$${val.toFixed(2)}`,
                },
                tooltip: {
                    enabled: true,
                    formatter: (val) => `$${val.toFixed(2)}`
                }
            },
            legend: {
                ...commonOptions.legend,
                offsetY: isMobile ? -10 : -5,
                fontSize: isMobile ? '12px' : '14px'
            },
            noData: { text: 'Enter a stock ticker to begin.' }
        };

        const subChartOptions = {
            ...commonOptions,
            chart: { 
                ...commonOptions.chart, 
                type: 'line', 
                height: subHeight,
                animations: {
                    enabled: !isMobile
                }
            },
            series: [],
            colors: ['var(--green-primary)', 'var(--blue-primary)', 'var(--purple-primary)'],
            yaxis: {
                ...commonOptions.yaxis,
                labels: {
                    ...commonOptions.yaxis.labels,
                    formatter: (val) => `${val.toFixed(1)}%`,
                },
            },
            legend: {
                ...commonOptions.legend,
                offsetY: isMobile ? -10 : -5,
                fontSize: isMobile ? '12px' : '14px'
            },
            annotations: {
                yaxis: [{
                    y: 0,
                    borderColor: 'var(--text-secondary)',
                    borderWidth: 1,
                    strokeDashArray: 2,
                }]
            },
            noData: { text: 'Loading momentum data...' }
        };

        try {
            state.mainChartInstance = new ApexCharts(DOM.mainChart, mainChartOptions);
            state.subChartInstance = new ApexCharts(DOM.subChart, subChartOptions);
            state.mainChartInstance.render();
            state.subChartInstance.render();
        } catch (error) {
            console.error('Error initializing charts:', error);
            showError('Failed to initialize charts');
        }
    }

    // Transforms API data into ApexCharts series format
    function transformToSeries(dates, values) {
        return dates.map((date, i) => {
            const timestamp = new Date(date).getTime();
            return [timestamp, values[i]];
        });
    }

    // Update charts with new data
    function updateCharts(data, ticker) {
        try {
            console.log('Updating charts with data:', data);
            const priceSeries = transformToSeries(data.dates, data.prices);
            const maSeries = transformToSeries(data.dates, data.ma_200);
            const diffSeries = transformToSeries(data.dates, data.pct_diff);
            console.log('Series created:', { priceSeries: priceSeries.length, maSeries: maSeries.length, diffSeries: diffSeries.length });
            
            // --- NEW: Create series for percentile lines ---
            const p16Series = createConstantSeries(data.dates, data.percentiles.p16, '16th Percentile');
            const p84Series = createConstantSeries(data.dates, data.percentiles.p84, '84th Percentile');

            if (!priceSeries.length) throw new Error('No data available for charts.');
            
            // --- NEW: Cache latest values for hover-off restoration ---
            state.lastPrice = data.prices[data.prices.length - 1];
            state.firstPrice = data.prices[0]; // First price in timeframe for period-based change
            state.previousClose = data.previous_close;
            state.lastDiffValue = data.pct_diff[data.pct_diff.length - 1];

            updateStockInfo(ticker, state.lastPrice, state.firstPrice);
            updateMomentumInfo(state.lastDiffValue);

            state.mainChartInstance.updateSeries([
                { name: 'Price', data: priceSeries },
                { name: '200-Day MA', data: maSeries }
            ]);

            const lastDiffValue = data.pct_diff[data.pct_diff.length - 1];
            const diffColor = lastDiffValue >= 0 ? 'var(--green-primary)' : 'var(--red-primary)';
            
            state.subChartInstance.updateSeries([
                { name: '% Deviation', data: diffSeries },
                p16Series,
                p84Series
            ].filter(s => s.data.length > 0));
            
            // Only update chart options if the color changed (performance optimization)
            if (state.lastDiffColor !== diffColor) {
                const newSubChartOptions = {
                    colors: [diffColor, 'var(--blue-primary)', 'var(--purple-primary)'],
                    stroke: {
                        width: [2, 1.5, 1.5],
                        dashArray: [0, 4, 4]
                    },
                    legend: {
                        show: true,
                        position: 'top',
                        horizontalAlign: 'right',
                        floating: true,
                        offsetY: -5,
                        fontFamily: 'var(--font-family-main)',
                        markers: {
                            width: 16,
                            height: 2,
                            radius: 0,
                        },
                        itemMargin: {
                            horizontal: 10,
                        },
                    },
                };
                state.subChartInstance.updateOptions(newSubChartOptions);
                state.lastDiffColor = diffColor;
            }

        } catch (error) {
            console.error('Error updating charts:', error);
            showError('Failed to update charts with new data.');
        }
    }

    // --- NEW: Creates a data series with a constant value ---
    function createConstantSeries(dates, value, name) {
        if (value === null || value === undefined) return { name, data: [] };
        const seriesData = dates.map(date => [new Date(date).getTime(), value]);
        return { name, data: seriesData };
    }

    // Updates stock info in the main chart's header
    function updateStockInfo(ticker, currentPrice, previousClose) {
        DOM.stockNameTitle.textContent = ticker;
        if (currentPrice) {
            DOM.currentPrice.textContent = `$${currentPrice.toFixed(2)}`;
        }

        let priceChange = 0;
        let percentChange = 0;
        if (currentPrice && previousClose) {
            priceChange = currentPrice - previousClose;
            percentChange = (priceChange / previousClose) * 100;
        }

        const sign = priceChange >= 0 ? '+' : '';
        DOM.priceChange.innerHTML = `
            <span>${sign}${priceChange.toFixed(2)}</span>
            <span>(${sign}${percentChange.toFixed(2)}%)</span>
        `;
        DOM.priceChange.className = `price-change ${priceChange >= 0 ? 'positive' : 'negative'}`;
    }

    function updateMomentumInfo(lastValue) {
        if (lastValue === null || lastValue === undefined) {
            DOM.momentumValue.textContent = '--';
            return;
        }
        const sign = lastValue >= 0 ? '+' : '';
        DOM.momentumValue.textContent = `${sign}${lastValue.toFixed(2)}%`;
        DOM.momentumValue.className = `price-change ${lastValue >= 0 ? 'positive' : 'negative'}`;
    }

    function handleTickerInput(event) {
        if (event.key === 'Enter' && !state.isLoading) {
            const ticker = DOM.tickerInput.value.trim().toUpperCase();
            if (ticker) {
                state.currentTicker = ticker;
                fetchData();
            }
        }
    }

    function handlePeriodChange(event) {
        if (state.isLoading) return;
        const button = event.target;
        const newPeriod = button.dataset.period?.toLowerCase() || '';
        if (newPeriod && newPeriod !== state.selectedPeriod) {
            updateSelectedPeriod(newPeriod);
            if (state.currentTicker) debouncedFetchData();
        }
    }

    function updateSelectedPeriod(newPeriod) {
        state.selectedPeriod = newPeriod;
        DOM.periodButtons.forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.period === newPeriod);
        });
    }

    function setLoading(loading) {
        state.isLoading = loading;
        DOM.loadingIndicator.classList.toggle('show', loading);
        DOM.tickerInput.disabled = loading;
        DOM.periodButtons.forEach(btn => btn.disabled = loading);
    }

    function showError(message) {
        DOM.errorMessage.textContent = message;
        setTimeout(() => DOM.errorMessage.textContent = '', 5000);
    }

    // Fetch data from the server
    async function fetchData() {
        if (state.isLoading) return;
        setLoading(true);
        DOM.errorMessage.textContent = '';
        try {
            const response = await fetch(`/data/${state.currentTicker}/${state.selectedPeriod}`);
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'Failed to fetch data');

            activateDashboardView();
            // Handle combined response structure
            if (result.stock_data && result.trading_stats) {
                // New combined response format
                updateCharts(result.stock_data, state.currentTicker);
                updateTradingStats(result.trading_stats);
            } else {
                // Fallback to old format if not combined
                updateCharts(result, state.currentTicker);
                fetchTradingStats();
            }


        } catch (error) {
            console.error('Error fetching data:', error);
            showError(`Error: ${error.message}`);
            clearCharts();
        } finally {
            setLoading(false);
        }
    }

    function clearCharts() {
        if(state.mainChartInstance && state.subChartInstance) {
            state.mainChartInstance.updateSeries([]);
            state.subChartInstance.updateSeries([]);
        }
        DOM.dashboard.style.display = 'none';
        DOM.statsBanner.style.display = 'none';
    }

    // Fetch and display simplified trading stats
    async function fetchTradingStats() {
        if (!state.currentTicker) return;
        
        try {
            const response = await fetch(`/trading-stats/${state.currentTicker}/${state.selectedPeriod}`);
            const result = await response.json();
            
            if (response.ok) {
                updateTradingStats(result);
            } else {
                console.warn('Could not fetch trading stats:', result.error);
                DOM.statsBanner.style.display = 'none';
            }
        } catch (error) {
            console.error('Error fetching trading stats:', error);
            DOM.statsBanner.style.display = 'none';
        }
    }

    // Update the new simplified stats banner
    function updateTradingStats(stats) {
        try {
            const fearDays = stats.zone_analysis?.fear_zone?.days ?? 'N/A';
            const fearPercentage = stats.zone_analysis?.fear_zone?.percentage ?? 'N/A';
            DOM.fearDays.textContent = `${fearDays} (${fearPercentage})`;
            
            const fearAvgPrice = stats.zone_analysis?.fear_zone?.avg_price;
            const currentPrice = stats.current_analysis?.price;
            
            if (fearAvgPrice && currentPrice) {
                const diff = ((currentPrice - fearAvgPrice) / fearAvgPrice * 100);
                const diffText = `${diff >= 0 ? '+' : ''}${diff.toFixed(1)}%`;
                DOM.fearAvgPrice.innerHTML = `$${fearAvgPrice.toFixed(2)} <span class="stat-value-small">(${diffText} vs current)</span>`;
            } else {
                DOM.fearAvgPrice.textContent = 'N/A';
            }
            
            DOM.statsBanner.style.display = 'flex';
        } catch (error) {
            console.error('Error updating trading stats display:', error);
            DOM.statsBanner.style.display = 'none';
        }
    }

    // --- NEW: Event handler for chart hover ---
    function handleChartMouseMove(event, chartContext, config) {
        const { dataPointIndex } = config;
        if (dataPointIndex === -1) return; // Not hovering over a data point

        // Get data from the internal chart state
        const mainSeries = state.mainChartInstance.w.globals.initialSeries;

        if (!mainSeries.length) return;

        const timestamp = mainSeries[0].data[dataPointIndex][0];
        const currentPrice = mainSeries[0].data[dataPointIndex][1];
        
        // Find previous day's price for change calculation
        const previousPrice = dataPointIndex > 0 ? mainSeries[0].data[dataPointIndex - 1][1] : currentPrice;

        // Get data from the sub-chart (momentum chart)
        const subSeries = state.subChartInstance.w.globals.initialSeries;
        if (!subSeries.length) return;

        const momentumValue = subSeries[0].data[dataPointIndex][1];

        // Update headers with hovered data
        const date = new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        DOM.stockNameTitle.textContent = date;

        updateStockInfo(state.currentTicker, currentPrice, previousPrice);
        updateMomentumInfo(momentumValue);
    }

    // --- NEW: Event handler to restore headers on mouse leave ---
    function handleChartMouseLeave() {
        // Restore the header to show the latest data
        updateStockInfo(state.currentTicker, state.lastPrice, state.firstPrice);
        updateMomentumInfo(state.lastDiffValue);
    }



    // Initialize on page load
    document.addEventListener('DOMContentLoaded', init);

    // Public API (for potential debugging or extensions)
    return {
        init,
        fetchData,
        fetchTradingStats,
    };
})();
