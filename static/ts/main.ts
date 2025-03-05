// Since we're using the CDN version of Plotly, we don't need to import it
// The Plotly object is available globally from the CDN script

// Type definitions
interface Period {
    days: number | null;
    interval: string;
}

interface Periods {
    [key: string]: Period;
}

interface ChartData {
    dates: string[];
    prices: (number | null)[];
    ma_200: (number | null)[];
    pct_diff: (number | null)[];
    percentiles?: {
        [key: string]: number;
    };
}

interface FilteredData {
    dates: string[];
    values: number[];
}

// Type definitions for Plotly
interface PlotlyLayout {
    showlegend?: boolean;
    margin?: {
        t?: number;
        r?: number;
        l?: number;
        b?: number;
    };
    plot_bgcolor?: string;
    paper_bgcolor?: string;
    hovermode?: string;
    hoverdistance?: number;
    hoverlabel?: {
        bgcolor?: string;
        bordercolor?: string;
        font?: {
            family?: string;
            size?: number;
            color?: string;
        };
        padding?: number;
    };
    xaxis?: Partial<PlotlyAxis>;
    yaxis?: Partial<PlotlyAxis>;
    height?: number;
}

interface PlotlyAxis {
    showgrid?: boolean;
    zeroline?: boolean;
    tickfont?: {
        family?: string;
        size?: number;
        color?: string;
    };
    title?: {
        text?: string;
        font?: {
            family?: string;
            size?: number;
            weight?: number;
        };
        standoff?: number;
    };
    showspikes?: boolean;
    spikemode?: string;
    spikesnap?: string;
    showline?: boolean;
    spikecolor?: string;
    spikethickness?: number;
    showticklabels?: boolean;
    tickangle?: number;
    fixedrange?: boolean;
    automargin?: boolean;
    rangeslider?: { visible: boolean };
    range?: (number | null | string)[] | string[];
    rangemode?: string;
    autorange?: boolean;
}

interface PlotlyData {
    x?: any[];
    y?: any[];
    type?: string;
    mode?: string;
    line?: {
        color?: string;
        width?: number;
        dash?: string;
    };
    name?: string;
    hovertemplate?: string;
    fill?: string;
    fillcolor?: string;
    hoverinfo?: string;
    showlegend?: boolean;
}

// Update type definitions to include Fx
interface PlotlyFx {
    hover: (element: HTMLElement, points: Array<{ curveNumber: number; pointNumber: number }>) => void;
    unhover: (element: HTMLElement) => void;
}

// Define base Plotly interface
interface BasePlotly {
    newPlot: (element: string | HTMLElement, data: any[], layout?: Partial<PlotlyLayout>, config?: Partial<any>) => Promise<any>;
    react: (element: string | HTMLElement, data: any[], layout?: Partial<PlotlyLayout>, config?: Partial<any>) => Promise<any>;
    relayout: (element: string | HTMLElement, layout: Partial<PlotlyLayout>) => Promise<any>;
}

// Extend with Fx
interface PlotlyWithFx extends BasePlotly {
    Fx: PlotlyFx;
}

// Declare Plotly as a global variable since it's loaded from CDN
declare global {
    interface Window {
        Plotly: PlotlyWithFx;
    }
}

// Constants
const PERIODS: Periods = {
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
    showTips: false,    // Disable default tooltips
    autosize: true      // Enable autosize
};

// Common layout properties
const commonAxisStyle: Partial<PlotlyAxis> = {
    showgrid: false,
    zeroline: false,
    tickfont: {
        family: 'Arial',
        size: 13,
        color: 'black'
    }
};

// Type definitions for Plotly events and elements
interface PlotlyHTMLElement extends HTMLElement {
    on(event: string, callback: (data: any) => void): void;
    layout?: Partial<PlotlyLayout>;
}

type PlotlyHoverInfo = 'x' | 'y' | 'all' | 'none' | 'z' | 'text' | 'name' | 'skip' | 'x+text' | 'x+name' | 'x+y' | 'x+y+text' | 'x+y+name' | 'x+y+z' | 'x+y+z+text' | 'x+y+z+name' | 'y+name' | 'y+x' | 'y+text';
type PlotlyFill = 'none' | 'tozeroy' | 'tozerox' | 'tonexty' | 'tonextx' | 'toself' | 'tonext';

interface PlotlyTrace extends Partial<PlotlyData> {
    showlegend?: boolean;
    hoverinfo?: PlotlyHoverInfo;
    fill?: PlotlyFill;
    fillcolor?: string;
    hovertemplate?: string;
}

// DOM Elements
const tickerInput = document.getElementById('ticker-input') as HTMLInputElement;
const periodButtons = document.querySelectorAll('.period-btn') as NodeListOf<HTMLButtonElement>;
const mainChart = document.getElementById('main-chart') as HTMLDivElement;
const subChart = document.getElementById('sub-chart') as HTMLDivElement;
const loadingIndicator = document.querySelector('.loading-indicator') as HTMLElement;
const errorMessage = document.querySelector('.error-message') as HTMLElement;
const stockInfoPanel = document.getElementById('stock-info') as HTMLElement;
const stockNameEl = document.getElementById('stock-name') as HTMLElement;
const currentPriceEl = document.getElementById('current-price') as HTMLElement;
const priceChangeEl = document.getElementById('price-change') as HTMLElement;
const changeValueEl = document.getElementById('change-value') as HTMLElement;
const changePercentEl = document.getElementById('change-percent') as HTMLElement;
const customTooltip = document.getElementById('custom-tooltip') as HTMLElement;
const dashboard = document.querySelector('.dashboard') as HTMLElement;

// State
let selectedPeriod: string = '5y'; // Always use lowercase to match server requirements
let currentTicker: string = '';
let isLoading: boolean = false;
let lastData: ChartData | null = null;

// Export the init function and any other necessary functions
export function init() {
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
                    weight: 500
                },
                standoff: 10
            },
            automargin: true,
            range: [null, null],
            rangemode: 'normal',
            autorange: true,
            fixedrange: true
        },
        xaxis: {
            ...commonAxisStyle,
            showspikes: true,
            spikemode: 'across' as const,
            spikesnap: 'cursor' as 'cursor',
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
            fixedrange: true,
            automargin: true,
            rangeslider: { visible: false }
        }
    } as unknown as Partial<PlotlyLayout>;

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
                    weight: 500
                },
                standoff: 10
            },
            automargin: true,
            fixedrange: true
        },
        xaxis: {
            ...commonAxisStyle,
            showspikes: true,
            spikemode: 'across' as const,
            spikesnap: 'cursor' as 'cursor',
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
            fixedrange: true,
            automargin: true,
            rangeslider: { visible: false }
        }
    } as unknown as Partial<PlotlyLayout>;

    try {
        window.Plotly.newPlot('main-chart', [], mainChartLayout, chartConfig);
        window.Plotly.newPlot('sub-chart', [], subChartLayout, chartConfig);

        // Add event listeners for synchronized hover
        const mainChartEl = document.getElementById('main-chart') as PlotlyHTMLElement;
        const subChartEl = document.getElementById('sub-chart') as PlotlyHTMLElement;

        mainChartEl.on('plotly_hover', (data) => {
            if (!data.points?.[0]) return;
            (window.Plotly as PlotlyWithFx).Fx.hover(subChartEl, [
                { curveNumber: 0, pointNumber: data.points[0].pointNumber }
            ]);
            updateTooltip(data.points[0]);
        });

        subChartEl.on('plotly_hover', (data) => {
            if (!data.points?.[0]) return;
            (window.Plotly as PlotlyWithFx).Fx.hover(mainChartEl, [
                { curveNumber: 0, pointNumber: data.points[0].pointNumber }
            ]);
            updateTooltip(data.points[0]);
        });

        mainChartEl.on('plotly_unhover', () => {
            (window.Plotly as PlotlyWithFx).Fx.unhover(subChartEl);
            hideTooltip();
        });

        subChartEl.on('plotly_unhover', () => {
            (window.Plotly as PlotlyWithFx).Fx.unhover(mainChartEl);
            hideTooltip();
        });

    } catch (error) {
        console.error('Error initializing charts:', error);
        showError('Failed to initialize charts');
    }
}

// Filter out null values from data
function filterNullValues(dates: string[], values: (number | null)[]): [string[], number[]] {
    const filtered = dates.reduce<FilteredData>((acc, date, i) => {
        if (values[i] !== null) {
            acc.dates.push(date);
            acc.values.push(values[i] as number);
        }
        return acc;
    }, { dates: [], values: [] });
    return [filtered.dates, filtered.values];
}

// Update charts with new data
function updateCharts(data: ChartData, ticker: string): void {
    try {
        // Store data for tooltip use
        lastData = data;
        
        // Filter out null values
        const [priceDates, priceValues] = filterNullValues(data.dates, data.prices);
        const [maDates, maValues] = filterNullValues(data.dates, data.ma_200);
        const [diffDates, diffValues] = filterNullValues(data.dates, data.pct_diff);

        if (!priceDates.length || !priceValues.length) {
            throw new Error('No data available');
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
        ] as Partial<PlotlyData>[];

        // Determine color for percent difference line
        let diffColor = '#00C805'; // green by default
        if (diffValues.length > 0 && diffValues[diffValues.length - 1] < 0) {
            diffColor = '#FF5000'; // red if negative
        }

        // Sub chart traces
        const subTraces: Array<Partial<PlotlyData>> = [
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
        let resizeTimeout: number;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = window.setTimeout(updateSize, 100);
        });

    } catch (error) {
        console.error('Error updating charts:', error);
        showError('Failed to update charts');
    }
}

// Function to update stock info panel
function updateStockInfo(ticker: string, currentPrice: number, firstPrice: number) {
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
function updateTooltip(point: any) {
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
function handleTickerInput(event: KeyboardEvent) {
    if (event.key === 'Enter' && !isLoading) {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (ticker && ticker !== currentTicker) {
            currentTicker = ticker;
            fetchData();
        }
    }
}

// Handle period change
function handlePeriodChange(event: Event) {
    if (isLoading) return;
    
    const button = event.target as HTMLButtonElement;
    const newPeriod = button.dataset.period?.toLowerCase() || '';
    if (newPeriod && newPeriod !== selectedPeriod) {
        updateSelectedPeriod(newPeriod);
        if (currentTicker) {
            fetchData();
        }
    }
}

// Update UI for selected period
function updateSelectedPeriod(newPeriod: string) {
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
function setLoading(loading: boolean) {
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
function showError(message: string) {
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
    } catch (error: unknown) {
        console.error('Error fetching data:', error);
        const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
        showError(`Error: ${errorMessage}`);
        clearCharts();
    } finally {
        setLoading(false);
    }
}

// Clear charts
function clearCharts() {
    const mainChartEl = document.getElementById('main-chart') as PlotlyHTMLElement;
    const subChartEl = document.getElementById('sub-chart') as PlotlyHTMLElement;
    
    window.Plotly.react('main-chart', [], mainChartEl?.layout || {}, chartConfig);
    window.Plotly.react('sub-chart', [], subChartEl?.layout || {}, chartConfig);
    stockInfoPanel.style.display = 'none';
    dashboard.style.display = 'none';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init); 