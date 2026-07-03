const WEEK_DAYS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];

// Converts the projection offset into days and actual names based on today's date.
export function getDynamicProjection(projectionData) {
    if (!projectionData) return [];

    const today = new Date();

    // array iteration
    return projectionData.map((item) => {
        if (item.day_offset === 0) {
            return {
                ...item,
                day_name: "HOJE",
                day_number: today.getDate()
            };
        }

        const targetDate = new Date();
        targetDate.setDate(today.getDate() + item.day_offset);

        return {
            ...item,
            day_name: WEEK_DAYS[targetDate.getDay()],
            day_number: targetDate.getDate()
        };
    });
}
