import { Text, Group, Stack, Progress, Box } from "@mantine/core";
import styles from '../../styles/Subjects/Subjects.module.css';
import SubjectIcon from '../Common/SubjectIcon';

/**
 * SubjectCard represents a single course subject item, including status indicators,
 * topic descriptions, mastery percentage progress, and queue statistics.
 */
export default function SubjectCard({ subject }) {
    return (
        <Box className={styles.subjectCard}>
            <Box
                className={styles.cardStripe}
                style={{ backgroundColor: subject.color }}
            />

            {/* Main card contents container */}
            <Box className={styles.cardContent}>
                {/* Header block with vertical stack layout matching mockup print */}
                <Stack gap="xs" className={styles.cardHeader}>
                    <SubjectIcon name={subject.icon} size={36} color={subject.color} />
                    <Text className={styles.cardTitle}>{subject.title}</Text>
                    <Text className={styles.cardSubtext}>
                        {subject.totalTopics} tópicos - última atividade ontem
                    </Text>
                </Stack>

                {/* Sub-counters summary badges row */}
                <Group gap="xs" wrap="nowrap">
                    <Box className={styles.badgeLabel}>
                        <Text size="xs" fw={700} c="blue.5">{subject.counters?.summaries || 0}</Text>
                        <Text size="xxs" fw={600} c="dimmed">resumos</Text>
                    </Box>
                    <Box className={styles.badgeLabel}>
                        <Text size="xs" fw={700} c="grape.5">{subject.counters?.mindMaps || 0}</Text>
                        <Text size="xxs" fw={600} c="dimmed">mapas</Text>
                    </Box>
                    <Box className={styles.badgeLabel}>
                        <Text size="xs" fw={700} c="orange.5">{subject.counters?.flashcards || 0}</Text>
                        <Text size="xxs" fw={600} c="dimmed">cards</Text>
                    </Box>
                </Group>

                {/* Mastery progress tracker */}
                <Stack gap={4} className={styles.masteryStack}>
                    <Group justify="space-between" align="center">
                        <Text size="xs" fw={600} c="dimmed">Domínio</Text>
                        <Text size="xs" fw={700} c="dark.7">{subject.masteryPercentage}%</Text>
                    </Group>
                    <Progress
                        value={subject.masteryPercentage}
                        color={subject.color}
                        size="sm"
                        radius="xl"
                        className={styles.progressBar}
                    />
                </Stack>

                {/* Card footer: Pending counts status and action links */}
                <Group justify="space-between" align="center">
                    <Group gap={6} align="center">
                        <Box
                            className={styles.bulletDot}
                            style={{ backgroundColor: subject.color }}
                        />
                        <Text size="xs" fw={500} c="dimmed">
                            <Text span fw={700}>{subject.pendingInQueue}</Text> na fila
                        </Text>
                    </Group>
                    <Text className={styles.openLink}>
                        abrir &gt;
                    </Text>
                </Group>
            </Box>
        </Box>
    );
}
