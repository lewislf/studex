// Global map representing short names for week days in Portuguese
const WEEK_DAYS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];

/**
 * Transforms standard mock date offsets into real dynamic calendar days and names.
 * Ensures the projection timeline updates relative to runtime device dates.
 * @param {Object[]} projectionData - Array containing items with sequential day offsets.
 * @returns {Object[]} Cloned array augmented with local calendar properties.
 */
export function getDynamicProjection(projectionData) {
    if (!projectionData) return [];

    const today = new Date();

    // Map over sequential items to attach structural time markers dynamically
    return projectionData.map((item) => {
        // Special case: Day 0 is always formatted as 'HOJE'
        if (item.day_offset === 0) {
            return {
                ...item,
                day_name: "HOJE",
                day_number: today.getDate()
            };
        }

        // Initialize target date copy and apply offset increments
        const targetDate = new Date();
        targetDate.setDate(today.getDate() + item.day_offset);

        return {
            ...item,
            day_name: WEEK_DAYS[targetDate.getDay()], // Fetches corresponding weekday string
            day_number: targetDate.getDate()          // Fetches dynamic calendar day number
        };
    });
}
