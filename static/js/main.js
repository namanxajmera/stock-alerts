import { fetchData } from './api.js';
import { initializeCharts, updateCharts, clearCharts } from './chart.js';
import { DOM, activateDashboardView, updateStockInfo, updateMomentumInfo, updateTradingStats, setLoading, showError, updateSelectedPeriod } from './ui.js';

const StockAnalyzer = (() => {
    const state = {
        selectedPeriod: '5y',
        currentTicker: '',
        isLoading: false,
        mainChartInstance: null,
        subChartInstance: null,
        isDashboardActive: false,
        lastPrice: null,
        previousClose: null,
        lastDiffValue: null,
        debounceTimer: null,
        lastDiffColor: null,
    };

    const init = () => {
        const { mainChartInstance, subChartInstance } = initializeCharts(DOM.mainChart, DOM.subChart, handleChartMouseMove, handleChartMouseLeave);
        state.mainChartInstance = mainChartInstance;
        state.subChartInstance = subChartInstance;
        
        setDefaultPeriod();
        DOM.tickerInput.focus();
        setupEventListeners();
    };

    const setDefaultPeriod = () => {
        state.selectedPeriod = '5y';
        const defaultBtn = document.querySelector('[data-period="5y"]');
        if (defaultBtn) defaultBtn.classList.add('selected');
    };

    const setupEventListeners = () => {
        DOM.tickerInput.addEventListener('keyup', handleTickerInput);
        DOM.periodButtons.forEach(btn => {
            btn.addEventListener('click', handlePeriodChange);
        });
    };

    const handleTickerInput = (event) => {
        if (event.key === 'Enter' && !state.isLoading) {
            const ticker = DOM.tickerInput.value.trim().toUpperCase();
            if (ticker) {
                state.currentTicker = ticker;
                fetchAllData();
            }
        } else if (event.type === 'keyup' && event.key !== 'Enter') {
            const ticker = DOM.tickerInput.value.trim().toUpperCase();
            if (ticker && ticker.length >= 2) {
                state.currentTicker = ticker;
                debouncedFetchAllData();
            }
        }
    };

    const handlePeriodChange = (event) => {
        if (state.isLoading) return;
        const button = event.target;
        const newPeriod = button.dataset.period?.toLowerCase() || '';
        if (newPeriod && newPeriod !== state.selectedPeriod) {
            state.selectedPeriod = newPeriod;
            updateSelectedPeriod(newPeriod);
            if (state.currentTicker) debouncedFetchAllData();
        }
    };

    const fetchAllData = async () => {
        if (state.isLoading) return;
        setLoading(true);
        showError('');
        try {
            const result = await fetchData(state.currentTicker, state.selectedPeriod);
            if (!state.isDashboardActive) {
                activateDashboardView(state.isDashboardActive);
                state.isDashboardActive = true;
            }
            
            if (result.stock_data && result.trading_stats) {
                state.lastDiffColor = updateCharts(result.stock_data, state.currentTicker, state.lastDiffColor);
                updateTradingStats(result.trading_stats);

                state.lastPrice = result.stock_data.prices[result.stock_data.prices.length - 1];
                state.firstPrice = result.stock_data.prices[0];
                state.previousClose = result.stock_data.previous_close;
                state.lastDiffValue = result.stock_data.pct_diff[result.stock_data.pct_diff.length - 1];

                updateStockInfo(state.currentTicker, state.lastPrice, state.firstPrice);
                updateMomentumInfo(state.lastDiffValue);
            } else {
                clearCharts();
                DOM.statsBanner.style.display = 'none';
            }
        } catch (error) {
            showError(`Error: ${error.message}`);
            clearCharts();
        } finally {
            setLoading(false);
        }
    };

    const debouncedFetchAllData = debounce(fetchAllData, 200);

    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(state.debounceTimer);
            state.debounceTimer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    const handleChartMouseMove = (event, chartContext, config) => {
        const { dataPointIndex } = config;
        if (dataPointIndex === -1) return;

        const mainSeries = state.mainChartInstance.w.globals.initialSeries;
        if (!mainSeries.length) return;

        const timestamp = mainSeries[0].data[dataPointIndex][0];
        const currentPrice = mainSeries[0].data[dataPointIndex][1];
        const previousPrice = dataPointIndex > 0 ? mainSeries[0].data[dataPointIndex - 1][1] : currentPrice;

        const subSeries = state.subChartInstance.w.globals.initialSeries;
        if (!subSeries.length) return;

        const momentumValue = subSeries[0].data[dataPointIndex][1];

        const date = new Date(timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        DOM.stockNameTitle.textContent = date;

        updateStockInfo(state.currentTicker, currentPrice, previousPrice);
        updateMomentumInfo(momentumValue);
    };

    const handleChartMouseLeave = () => {
        updateStockInfo(state.currentTicker, state.lastPrice, state.firstPrice);
        updateMomentumInfo(state.lastDiffValue);
    };

    document.addEventListener('DOMContentLoaded', init);

    return { init };
})();