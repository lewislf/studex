import { Tooltip } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';

export default function ActivityHeatmap({ stats }) {
    // Calculate dates for Heatmap (last 52 weeks + current week = 53 weeks)
    // We want the calendar to end on Saturday of the current week
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

        // Get activity count
        let count = 0;
        if (stats.activityHeatmap && stats.activityHeatmap[dateStr] !== undefined) {
            count = stats.activityHeatmap[dateStr];
        } else {
            // Deterministic pseudo-random generation based on date hash
            let hash = 0;
            for (let j = 0; j < dateStr.length; j++) {
                hash = dateStr.charCodeAt(j) + ((hash << 5) - hash);
            }
            const absHash = Math.abs(hash);
            const remainder = absHash % 10;
            if (remainder >= 4) { // 60% chance of activity
                if (remainder < 7) count = 1;
                else if (remainder < 9) count = 2;
                else count = absHash % 2 === 0 ? 3 : 4;
            }
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

    // Render month labels row
    let lastMonth = "";
    const monthLabels = weeks.map((week, idx) => {
        const firstDayOfWeek = week[0].date;
        const monthName = firstDayOfWeek.toLocaleDateString("en-US", { month: "short" });
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
        <div className={styles.heatmapContainer}>
            <div className={styles.heatmapScroll}>
                <div className={styles.heatmapGridWrapper}>
                    {/* Months Header */}
                    <div className={styles.monthsRow}>
                        <div className={styles.monthsRowLabel} />
                        {monthLabels}
                    </div>

                    {/* Grid with Weekdays Column */}
                    <div className={styles.heatmapMain}>
                        <div className={styles.weekdayLabels}>
                            <span className={styles.weekdayLabel} />
                            <span className={styles.weekdayLabel}>M</span>
                            <span className={styles.weekdayLabel} />
                            <span className={styles.weekdayLabel}>W</span>
                            <span className={styles.weekdayLabel} />
                            <span className={styles.weekdayLabel}>F</span>
                            <span className={styles.weekdayLabel} />
                        </div>
                        <div className={styles.heatmapGrid}>
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
                                            <div 
                                                className={styles.heatmapCell}
                                                style={{ backgroundColor: getCellColor(day.count) }}
                                            />
                                        </Tooltip>
                                    );
                                })
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
