import { Text, Group, Box } from "@mantine/core";
import { useNavigate } from "react-router";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardFooter renders the status indicator and the "abrir >" action
 * link, which is the sole entry point into the subject detail page.
 *
 * @param {Object} props
 * @param {string|number} props.subjectId - Subject id to navigate to on open.
 * @param {number} props.pendingInQueue - The count of reviews waiting in the queue.
 * @param {string} props.color - Theme color string of the bullet dot.
 */
export default function SubjectCardFooter({ subjectId, pendingInQueue, color }) {
    const navigate = useNavigate();

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
            <Text
                className={styles.openLink}
                onClick={() => navigate(`/materias/${subjectId}`)}
            >
                abrir &gt;
            </Text>
        </Group>
    );
}
