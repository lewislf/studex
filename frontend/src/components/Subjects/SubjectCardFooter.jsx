import { Text, Group, Box } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardFooter renders the status indicator and action link.
 */
export default function SubjectCardFooter({ pendingInQueue, color }) {
    return (
        <Group justify="space-between" align="center">
            <Group gap={6} align="center">
                <Box
                    className={styles.bulletDot}
                    style={{ backgroundColor: color }}
                />
                <Text size="xs" fw={500} c="dimmed">
                    <Text span fw={700}>{pendingInQueue}</Text> na fila
                </Text>
            </Group>
            <Text className={styles.openLink}>
                abrir &gt;
            </Text>
        </Group>
    );
}
