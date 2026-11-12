import { Title, Text, RingProgress, Progress, Container, Stack, Group, Flex } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';
import SubjectIcon from '../Common/SubjectIcon';
import { useMediaQuery } from '@mantine/hooks';

/**
 * StatisticsOverviewCard displays primary numeric indicators (such as streak count,
 * flashcards created, maps created) and maps them to a gamified progress rating rank (E-S).
 */
// Rank tiers ordered from lowest to highest, each with the score threshold
// where it starts and the score span used to compute the ring's progress.
const RANK_TIERS = [
    { grade: "E", min: 0, span: 500, color: "gray.5" },
    { grade: "D", min: 500, span: 700, color: "orange.5" },
    { grade: "C", min: 1200, span: 1000, color: "yellow.5" },
    { grade: "B", min: 2200, span: 1300, color: "green.5" },
    { grade: "A", min: 3500, span: 1500, color: "blue.5" },
    { grade: "S", min: 5000, span: 3000, color: "grape.6" },
];

export default function StatisticsOverviewCard({ user, stats }) {
    // Helper function to format thousands (e.g. 1500 -> 1.5k)
    const formatCount = (val) => {
        if (val >= 1000) {
            return (val / 1000).toFixed(1) + 'k';
        }
        return val;
    };

    // Formulates a score index from statistics to assign a gamified rank tier (E, D, C, B, A, S)
    const calculateUserRank = () => {
        const streak = user.gamification?.streak || 0;
        const maps = user.counters?.mapsCount || 0;
        const summaries = user.counters?.summariesCount || 0;
        const flashcards = user.counters?.totalFlashcardsCreated || 0;

        // Weights: flashcards created weight 2, streak weight 25, maps/summaries weight 10
        const score = (flashcards * 2) + (streak * 25) + (maps * 10) + (summaries * 10);

        // Highest tier whose threshold the score has reached (RANK_TIERS is ascending).
        const tier = [...RANK_TIERS].reverse().find((t) => score >= t.min) ?? RANK_TIERS[0];
        const progressValue = tier.grade === "S"
            ? Math.min(((score - tier.min) / tier.span) * 100 + 50, 100)
            : ((score - tier.min) / tier.span) * 100;

        return {
            grade: tier.grade,
            progressValue: Math.round(progressValue),
            color: tier.color
        };
    };

    const rank = calculateUserRank();
    const isMobile = useMediaQuery('(max-width: 48em)', false, { getInitialValueInEffect: false });

    return (
        <Container className={styles.leftCard}>
            <Stack justify="space-between" className={styles.overviewStack} gap="xl">
                <Stack gap="sm">
                    {/* Header title */}
                    <Title order={2} className={styles.sectionTitle}>
                        Estatísticas
                    </Title>

                    {/* Responsive Flex block containing list stats and the rating ring progress chart */}
                    <Flex direction={{ base: 'column-reverse', sm: 'row' }} justify="space-between" align="center" gap="md" mt="md" mb="md">
                        {/* List of Stats */}
                        <Stack className={styles.statList} gap="sm">
                            <Group gap="md" wrap="nowrap">
                                <SubjectIcon name="flame" size={32} color="#ff9f1c" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Total de Dias de Ofensiva</Text>
                                    <Text className={styles.statValue}>{user.gamification?.streak || 0} dias</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <SubjectIcon name="cards" size={32} color="#2196f3" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Cartões na Fila Hoje:</Text>
                                    <Text className={styles.statValue}>{user.counters?.pendingFlashcardsToday || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <SubjectIcon name="sitemap" size={32} color="#00bcd4" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Mapas Mentais:</Text>
                                    <Text className={styles.statValue}>{user.counters?.mapsCount || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <SubjectIcon name="file-text" size={32} color="#9c27b0" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Resumos:</Text>
                                    <Text className={styles.statValue}>{user.counters?.summariesCount || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <SubjectIcon name="book" size={32} color="#795548" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Total de Cartões Criados:</Text>
                                    <Text className={styles.statValue}>{formatCount(user.counters?.totalFlashcardsCreated || 0)}</Text>
                                </Stack>
                            </Group>
                        </Stack>

                        {/* Large Ring Chart displaying overall gamified rank tier */}
                        <Group gap="md" justify="center">
                            <RingProgress
                                size={isMobile ? 190 : 300}
                                thickness={isMobile ? 16 : 25}
                                roundCaps
                                sections={[{ value: rank.progressValue, color: rank.color }]}
                                label={
                                    <Stack gap={0} align="center" justify="center">
                                        <Text size={isMobile ? '3.2rem' : '5rem'} fw={900} c={rank.color} lh={1} className={styles.rankGrade}>
                                            {rank.grade}
                                        </Text>
                                        <Text size="xs" fw={700} c="dimmed" tt="uppercase">
                                            Ranking
                                        </Text>
                                    </Stack>
                                }
                            />
                        </Group>
                    </Flex>
                </Stack>

                {/* Subject Distribution segmented bar */}
                <Stack className={styles.segmentedBarContainer} gap="xs">
                    <Title order={3} className={styles.sectionTitle} style={{ fontSize: "1.1rem" }}>
                        Assuntos de Cartões Mais Usados
                    </Title>

                    {/* Progress root stacking sections proportionally */}
                    <Progress.Root size="lg" radius="xl">
                        {stats.statsDistribution?.map((item, idx) => (
                            <Progress.Section
                                key={idx}
                                value={item.percentage}
                                color={item.color}
                            />
                        ))}
                    </Progress.Root>

                    {/* Color legends grid */}
                    <Group gap="md" mt="sm" wrap="wrap">
                        {stats.statsDistribution?.map((item, idx) => (
                            <Group key={idx} className={styles.legendItem} gap={6}>
                                <div
                                    className={styles.legendColor}
                                    style={{ backgroundColor: item.color }}
                                />
                                <Text span>{item.label}: {item.percentage}%</Text>
                            </Group>
                        ))}
                    </Group>
                </Stack>
            </Stack>
        </Container>
    );
}
