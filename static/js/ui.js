export const DOM = {
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
    stockNameTitle: document.getElementById('stock-name-title'),
    currentPrice: document.getElementById('current-price'),
    priceChange: document.getElementById('price-change'),
    fearDays: document.getElementById('fear-days'),
    fearAvgPrice: document.getElementById('fear-avg-price'),
    fearVsCurrent: document.getElementById('fear-vs-current'),
    momentumValue: document.getElementById('momentum-value'),
    customTooltip: document.getElementById('custom-tooltip'),
};

export const activateDashboardView = (isDashboardActive) => {
    if (isDashboardActive) return;
    DOM.headerSearchControls.appendChild(DOM.searchControls);
    DOM.appContainer.classList.add('dashboard-active');
    DOM.dashboard.style.display = 'block';
};

export const updateStockInfo = (ticker, currentPrice, previousClose) => {
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
};

export const updateMomentumInfo = (lastValue) => {
    if (lastValue === null || lastValue === undefined) {
        DOM.momentumValue.textContent = '--';
        return;
    }
    const sign = lastValue >= 0 ? '+' : '';
    DOM.momentumValue.textContent = `${sign}${lastValue.toFixed(2)}%`;
    DOM.momentumValue.className = `price-change ${lastValue >= 0 ? 'positive' : 'negative'}`;
};

export const updateTradingStats = (stats) => {
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
};

export const setLoading = (loading) => {
    DOM.loadingIndicator.classList.toggle('show', loading);
    DOM.tickerInput.disabled = loading;
    DOM.periodButtons.forEach(btn => btn.disabled = loading);
};

export const showError = (message) => {
    DOM.errorMessage.textContent = message;
    setTimeout(() => DOM.errorMessage.textContent = '', 5000);
};

export const updateSelectedPeriod = (newPeriod) => {
    document.querySelectorAll('.period-btn').forEach(btn => {
        const isSelected = btn.dataset.period === newPeriod;
        btn.classList.toggle('selected', isSelected);
        btn.setAttribute('aria-pressed', isSelected.toString());
    });
};
