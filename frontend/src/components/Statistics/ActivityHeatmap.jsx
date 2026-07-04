import { Tooltip, Container, Box, Stack, Text } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';

export default function ActivityHeatmap({ stats }) {
    // Calculate dates for Heatmap (last 52 weeks + current week = 53 weeks)
    // Calendar starts on Sunday to align with default layout
    const today = new Date();
    const todayDay = today.getDay(); // 0 (Sun) to 6 (Sat)

    // Start date is 52 weeks ago, aligned to Sunday
    const startDate = new Date(today);
    startDate.setDate(today.getDate() - 364 - todayDay);

    // Generate days (53 weeks * 7 days = 371 days)
    const weeks = [];
    let currentWeek = [];

    for (let i = 0; i < 371; i++) {
        const date = new Date(startDate);
        date.setDate(startDate.getDate() + i);

        // Format as YYYY-MM-DD in local time
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;

        // Get activity count strictly from mock data
        let count = 0;
        if (stats.activityHeatmap && stats.activityHeatmap[dateStr] !== undefined) {
            count = stats.activityHeatmap[dateStr];
        }

        currentWeek.push({
            date,
            dateStr,
            count
        });

        if (currentWeek.length === 7) {
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
        const monthNum = firstDayOfWeek.getMonth();
        const ptMonths = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
        const monthName = ptMonths[monthNum];
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
            <Box className={styles.heatmapScroll}>
                <Box className={styles.heatmapGridWrapper}>
                    {/* Months Header */}
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
                        <Box className={styles.heatmapGrid}>
                            {weeks.map((week) =>
                                week.map((day) => {
                                    const formattedDate = day.date.toLocaleDateString("pt-BR", {
                                        day: "numeric",
                                        month: "long",
                                        year: "numeric"
                                    });
                                    return (
                                        <Tooltip
                                            key={day.dateStr}
                                            label={`${day.count} atividades em ${formattedDate}`}
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
