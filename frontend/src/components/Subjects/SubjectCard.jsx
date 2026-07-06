import { Text, Group, Stack, Progress, Box } from "@mantine/core";
import {
    IconGlobe,
    IconRocket,
    IconSchool,
    IconUsers,
    IconDatabase,
    IconBook,
    IconCalculator,
    IconFlask,
    IconCode,
    IconLanguage,
    IconBrain,
    IconPalette,
    IconHistory,
    IconMicroscope,
    IconHeart,
    IconScale
} from '@tabler/icons-react';
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCard represents a single course subject item, including status indicators,
 * topic descriptions, mastery percentage progress, and queue statistics.
 */
export default function SubjectCard({ subject }) {
    // Dynamic icon resolution based on configuration mock key strings
    const getSubjectIcon = (iconName) => {
        switch (iconName) {
            case 'globe': return IconGlobe;
            case 'rocket': return IconRocket;
            case 'user-teacher': return IconSchool;
            case 'users': return IconUsers;
            case 'database': return IconDatabase;
            case 'calculator': return IconCalculator;
            case 'flask': return IconFlask;
            case 'code': return IconCode;
            case 'language': return IconLanguage;
            case 'brain': return IconBrain;
            case 'palette': return IconPalette;
            case 'history': return IconHistory;
            case 'microscope': return IconMicroscope;
            case 'heart': return IconHeart;
            case 'scale': return IconScale;
            default: return IconBook;
        }
    };

    const IconComponent = getSubjectIcon(subject.icon);

    return (
        <Box className={styles.subjectCard}>
            <div
                className={styles.cardStripe}
                style={{ backgroundColor: subject.color }}
            />

            {/* Main card contents container */}
            <div className={styles.cardContent}>
                {/* Header block with vertical stack layout matching mockup print */}
                <Stack gap="xs" className={styles.cardHeader}>
                    <IconComponent size={36} color={subject.color} />
                    <Text className={styles.cardTitle}>{subject.title}</Text>
                    <Text className={styles.cardSubtext}>
                        {subject.totalTopics} tópicos - última atividade ontem
                    </Text>
                </Stack>

                {/* Sub-counters summary badges row */}
                <Group gap="xs" wrap="nowrap">
                    <div className={styles.statBadge}>
                        <Text className={styles.statBadgeLabel}>Resumos</Text>
                        <Text className={styles.statBadgeValue}>{subject.counters?.summaries || 0}</Text>
                    </div>
                    <div className={styles.statBadge}>
                        <Text className={styles.statBadgeLabel}>Mapas</Text>
                        <Text className={styles.statBadgeValue}>{subject.counters?.mindMaps || 0}</Text>
                    </div>
                    <div className={styles.statBadge}>
                        <Text className={styles.statBadgeLabel}>Flashcards</Text>
                        <Text className={styles.statBadgeValue}>{subject.counters?.flashcards || 0}</Text>
                    </div>
                </Group>

                {/* Mastery progress levels gauge */}
                <Stack gap={4}>
                    <Group justify="space-between">
                        <Text size="xs" fw={600} c="dimmed">Domínio</Text>
                        <Text size="xs" fw={700} c="dimmed">{subject.masteryPercentage}%</Text>
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
                        <div
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
            </div>
        </Box>
    );
}
