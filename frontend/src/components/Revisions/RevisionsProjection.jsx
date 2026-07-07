import { Text, Box } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';

import { WEEKDAYS_UPPER } from '../../config/Constants';

/**
 * RevisionsProjection renders a 7-day preview forecast, dynamically mapping relative
 * weekday tags and date integers, presenting proportional density horizontal lines.
 *
 * @param {Object} props
 * @param {Array} props.projection - List of upcoming weekly metrics.
 */
export default function RevisionsProjection({ projection = [] }) {
    // Generate relative weekday string labels (e.g. HOJE, SEG, TER)
    const getDayLabel = (offset) => {
        if (offset === 0) return 'HOJE';
        const targetDate = new Date();
        targetDate.setDate(targetDate.getDate() + offset);
        return WEEKDAYS_UPPER[targetDate.getDay()];
    };

    // Calculate relative day of the month numbers (e.g. 11, 12, 13)
    const getDayNumber = (offset) => {
        const targetDate = new Date();
        targetDate.setDate(targetDate.getDate() + offset);
        return targetDate.getDate();
    };

    // Maximum cards count density across forecast
    const maxProjectionCards = Math.max(...(projection.map(p => p.cardsCount) || [1]), 1);

    return (
        <Box className={styles.weeklyProjection}>
            <Text className={styles.weeklyHeader}>Próximos 7 Dias</Text>
            <Box className={styles.weeklyGrid}>
                {projection.map((day) => {
                    const label = getDayLabel(day.dayOffset);
                    const number = getDayNumber(day.dayOffset);
                    return (
                        <Box key={day.dayOffset} className={styles.dayBox}>
                            <Text className={styles.dayTitle}>{label}</Text>
                            <Text className={styles.dayValue}>{number}</Text>

                            <Box className={styles.dayBarTrack}>
                                <Box
                                    className={styles.dayBarFill}
                                    style={{ width: `${(day.cardsCount / maxProjectionCards) * 100}%` }}
                                />
                            </Box>

                            {day.isFree ? (
                                <Text size="xs" className={styles.dayFooterFree}>livre</Text>
                            ) : (
                                <Text size="xs" className={styles.dayFooter}>{day.cardsCount} cards</Text>
                            )}
                        </Box>
                    );
                })}
            </Box>
        </Box>
    );
}
