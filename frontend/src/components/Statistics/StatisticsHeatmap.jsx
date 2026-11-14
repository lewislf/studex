import { useEffect, useRef } from "react";
import { Tooltip, Container, Box } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';
import { MONTHS_SHORT } from '../../config/Constants';

/**
 * StatisticsHeatmap renders a contribution-style calendar grid.
 * Displays daily active studying counts across a 53-week span, starting on Sunday.
 */
export default function StatisticsHeatmap({ stats }) {
    // Em telas estreitas o calendário rola na horizontal; começa mostrando as
    // semanas mais recentes (à direita) em vez das de um ano atrás.
    const scrollRef = useRef(null);
    useEffect(() => {
        const el = scrollRef.current;
        if (el) el.scrollLeft = el.scrollWidth;
    }, [stats]);

    // Current date of the user's browser
    const today = new Date();
    // Normalize today's date to midnight local time for safe comparisons
    const todayLocal = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    // Real activity map: local ISO day -> activity count, straight from the API
    const heatmap = stats.activityHeatmap || {};

    const todayDay = todayLocal.getDay(); // 0 (Sun) to 6 (Sat)
    const weeksToShow = 53;
    const daysInWeek = 7;
    const totalDays = weeksToShow * daysInWeek;

    // Start date is 52 weeks ago, aligned to Sunday of that week
    const startDate = new Date(todayLocal);
    startDate.setDate(startDate.getDate() - (totalDays - daysInWeek) - todayDay);

    // Generate days using dynamic variables
    const weeks = [];
    let currentWeek = [];

    for (let i = 0; i < totalDays; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);

        // Format as YYYY-MM-DD in local time
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;

        // Get the real activity count for this day, if any
        let count = 0;
        if (heatmap[dateStr] !== undefined) {
            count = heatmap[dateStr];
        }

        currentWeek.push({
            date,
            dateStr,
            count
        });

        if (currentWeek.length === daysInWeek) {
            weeks.push(currentWeek);
            currentWeek = [];
        }
    }

    // Determine color based on activity count
    const getCellColor = (count) => {
        if (count === 0) return "#f4f4f4";
        if (count === 1) return "#c6e48b";
        if (count === 2) return "#7bc96f";
        if (count === 3) return "#239a3b";
        return "#196127";
    };

    // Render month labels row in Portuguese
    let lastMonth = "";
    const monthLabels = weeks.map((week, idx) => {
        const firstDayOfWeek = week[0].date;
        const lastDayOfWeek = week[6].date;
        
        const firstMonthNum = firstDayOfWeek.getMonth();
        const lastMonthNum = lastDayOfWeek.getMonth();
        
        let monthName = MONTHS_SHORT[firstMonthNum];
        
        // If we are on the last week of the calendar and the week spans into the next month
        if (idx === weeks.length - 1 && lastMonthNum !== firstMonthNum) {
            monthName = MONTHS_SHORT[lastMonthNum];
        }

        if (monthName !== lastMonth) {
            lastMonth = monthName;
            return (
                <div key={idx} className={styles.monthLabel}>
                    {monthName}
                </div>
            );
        }
        return <div key={idx} />;
    });

    return (
        <Container className={styles.heatmapContainer}>
            <Box className={styles.heatmapScroll} ref={scrollRef}>
                <Box className={styles.heatmapGridWrapper}>
                    {/* Months Header row */}
                    <Box className={styles.monthsRow}>
                        <Box className={styles.monthsRowLabel} />
                        {monthLabels}
                    </Box>

                    {/* Grid with Weekdays Column (S, Q, S aligned with rows 1, 3, 5) */}
                    <Box className={styles.heatmapMain}>
                        <div className={styles.weekdayLabels}>
                            <div className={styles.weekdayLabel} />
                            <div className={styles.weekdayLabel}>S</div>
                            <div className={styles.weekdayLabel} />
                            <div className={styles.weekdayLabel}>Q</div>
                            <div className={styles.weekdayLabel} />
                            <div className={styles.weekdayLabel}>S</div>
                            <div className={styles.weekdayLabel} />
                        </div>
                        {/* Daily contribution cells grid */}
                        <Box className={styles.heatmapGrid}>
                            {weeks.map((week) =>
                                week.map((day) => {
                                    const formattedDate = day.date.toLocaleDateString("pt-BR", {
                                        day: "numeric",
                                        month: "long",
                                        year: "numeric"
                                    });
                                    const activityLabel = day.count === 1 ? "1 atividade" : `${day.count} atividades`;
                                    return (
                                        <Tooltip
                                            key={day.dateStr}
                                            label={`${activityLabel} em ${formattedDate}`}
                                            position="top"
                                            withArrow
                                        >
                                            <Box
                                                className={styles.heatmapCell}
                                                style={{ backgroundColor: getCellColor(day.count) }}
                                            />
                                        </Tooltip>
                                    );
                                })
                            )}
                        </Box>
                    </Box>
                </Box>
            </Box>
        </Container>
    );
}
