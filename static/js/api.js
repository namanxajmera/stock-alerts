export const fetchData = async (ticker, period) => {
    try {
        const response = await fetch(`/data/${ticker}/${period}`);
        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.error || `HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching data:', error);
        // Re-throw the error so the calling function can handle it
        throw error;
    }
};
