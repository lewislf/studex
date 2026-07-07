import { Text, Group, Box } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardCounters renders the numeric summary badges (summaries, mind maps, and flashcards count).
 */
export default function SubjectCardCounters({ counters }) {
    return (
        <Group gap="xs" wrap="nowrap">
            <Box className={styles.statBadge}>
                <Text className={styles.statBadgeLabel}>Resumos</Text>
                <Text className={styles.statBadgeValue}>{counters?.summaries || 0}</Text>
            </Box>
            <Box className={styles.statBadge}>
                <Text className={styles.statBadgeLabel}>Mapas</Text>
                <Text className={styles.statBadgeValue}>{counters?.mindMaps || 0}</Text>
            </Box>
            <Box className={styles.statBadge}>
                <Text className={styles.statBadgeLabel}>Flashcards</Text>
                <Text className={styles.statBadgeValue}>{counters?.flashcards || 0}</Text>
            </Box>
        </Group>
    );
}
