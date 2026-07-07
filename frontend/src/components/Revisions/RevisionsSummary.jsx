import { Text, Progress, Box, Stack } from "@mantine/core";
import { IconClock } from '@tabler/icons-react';
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsSummary renders the split progress metrics.
 * Displays totals, learning curves, new and review allocations proportionally.
 *
 * @param {Object} props
 * @param {Object} props.summary - Spacing repetition splits summary metrics.
 */
export default function RevisionsSummary({ summary }) {
    if (!summary) return null;

    const total = summary.totalPending || 0;
    const split = summary.split || { new: 0, learning: 0, review: 0 };

    return (
        <Box className={styles.summaryContainer}>
            <Box className={styles.summaryHeader}>
                <Stack gap={2}>
                    <Text className={styles.pendingLabel}>Na Fila Agora</Text>
                    <Text className={styles.pendingNumber}>{total}</Text>
                </Stack>
                <Box className={styles.estimatedTime}>
                    <IconClock size={16} />
                    <Text span>tempo estimado: ~{summary.estimatedTimeMinutes} min</Text>
                </Box>
            </Box>

            {/* Progress segment proportions */}
            <Progress.Root size="lg" radius="xl" className={styles.progressBar}>
                <Progress.Section
                    value={total ? (split.new / total) * 100 : 0}
                    color="#2196f3"
                />
                <Progress.Section
                    value={total ? (split.learning / total) * 100 : 0}
                    color="#ff9f1c"
                />
                <Progress.Section
                    value={total ? (split.review / total) * 100 : 0}
                    color="#2ec4b6"
                />
            </Progress.Root>

            {/* Sub-metrics color legend rows */}
            <Box className={styles.splitLegend}>
                <Box className={styles.legendItem}>
                    <Box className={styles.splitDot} style={{ backgroundColor: '#2196f3' }} />
                    <Text className={styles.splitText}>
                        novo <Text span className={styles.splitTextNumber}>{split.new}</Text>
                    </Text>
                </Box>
                <Box className={styles.legendItem}>
                    <Box className={styles.splitDot} style={{ backgroundColor: '#ff9f1c' }} />
                    <Text className={styles.splitText}>
                        aprendendo <Text span className={styles.splitTextNumber}>{split.learning}</Text>
                    </Text>
                </Box>
                <Box className={styles.legendItem}>
                    <Box className={styles.splitDot} style={{ backgroundColor: '#2ec4b6' }} />
                    <Text className={styles.splitText}>
                        revisar <Text span className={styles.splitTextNumber}>{split.review}</Text>
                    </Text>
                </Box>
            </Box>
        </Box>
    );
}
