import { Text, Stack, Group, Progress } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardMastery renders the mastery level and percentage progress bar.
 */
export default function SubjectCardMastery({ masteryPercentage, color }) {
    return (
        <Stack gap={4}>
            <Group justify="space-between">
                <Text size="xs" fw={600} c="dimmed">Domínio</Text>
                <Text size="xs" fw={700} c="dimmed">{masteryPercentage}%</Text>
            </Group>
            <Progress
                value={masteryPercentage}
                color={color}
                size="sm"
                radius="xl"
                className={styles.progressBar}
            />
        </Stack>
    );
}
