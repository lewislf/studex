import { Text, Group, Box } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardCounters renders the numeric summary badges (summaries, mind maps, and flashcards count).
 */
export default function SubjectCardCounters({ counters }) {
    return (
        <Group gap="xs" wrap="nowrap">
            <Box className={styles.badgeLabel}>
                <Text size="sm" fw={700} c="blue">{counters?.summaries || 0}</Text>
                <Text size="sm" fw={600} c="dimmed">resumos</Text>
            </Box>
            <Box className={styles.badgeLabel}>
                <Text size="sm" fw={700} c="grape.5">{counters?.mindMaps || 0}</Text>
                <Text size="sm" fw={600} c="dimmed">mapas</Text>
            </Box>
            <Box className={styles.badgeLabel}>
                <Text size="sm" fw={700} c="orange.5">{counters?.flashcards || 0}</Text>
                <Text size="sm" fw={600} c="dimmed">cards</Text>
            </Box>
        </Group>
    );
}
