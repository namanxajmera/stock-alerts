let mainChartInstance = null;
let subChartInstance = null;

const initializeCharts = (mainChartElement, subChartElement, handleChartMouseMove, handleChartMouseLeave) => {
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

    mainChartInstance = new ApexCharts(mainChartElement, mainChartOptions);
    subChartInstance = new ApexCharts(subChartElement, subChartOptions);
    mainChartInstance.render();
    subChartInstance.render();

    return { mainChartInstance, subChartInstance };
};

const transformToSeries = (dates, values) => {
    return dates.map((date, i) => {
        const timestamp = new Date(date).getTime();
        return [timestamp, values[i]];
    });
};

const createConstantSeries = (dates, value, name) => {
    if (value === null || value === undefined) return { name, data: [] };
    const seriesData = dates.map(date => [new Date(date).getTime(), value]);
    return { name, data: seriesData };
};

const updateCharts = (data, ticker, lastDiffColor) => {
    const priceSeries = transformToSeries(data.dates, data.prices);
    const maSeries = transformToSeries(data.dates, data.ma_200);
    const diffSeries = transformToSeries(data.dates, data.pct_diff);
    const p16Series = createConstantSeries(data.dates, data.percentiles.p16, '16th Percentile');
    const p84Series = createConstantSeries(data.dates, data.percentiles.p84, '84th Percentile');

    if (!priceSeries.length) throw new Error('No data available for charts.');

    mainChartInstance.updateSeries([
        { name: 'Price', data: priceSeries },
        { name: '200-Day MA', data: maSeries }
    ]);

    const lastDiffValue = data.pct_diff[data.pct_diff.length - 1];
    const diffColor = lastDiffValue >= 0 ? 'var(--green-primary)' : 'var(--red-primary)';

    subChartInstance.updateSeries([
        { name: '% Deviation', data: diffSeries },
        p16Series,
        p84Series
    ].filter(s => s.data.length > 0));

    if (lastDiffColor !== diffColor) {
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
        subChartInstance.updateOptions(newSubChartOptions);
    }
    return diffColor;
};

const clearCharts = () => {
    if(mainChartInstance && subChartInstance) {
        mainChartInstance.updateSeries([]);
        subChartInstance.updateSeries([]);
    }
};

export { initializeCharts, updateCharts, clearCharts };
