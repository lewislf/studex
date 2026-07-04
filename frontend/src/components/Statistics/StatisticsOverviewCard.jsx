import { Title, Text, RingProgress, Progress, Container, Stack, Group, Flex } from "@mantine/core";
import {
    IconFlame,
    IconCards,
    IconSitemap,
    IconFileText,
    IconBook
} from '@tabler/icons-react';
import styles from '../../styles/Statistics/Statistics.module.css';

export default function StatisticsOverviewCard({ user, stats }) {
    // Formatter for counts (e.g. 1247 -> 1.2k)
    const formatCount = (val) => {
        if (val >= 1000) {
            return (val / 1000).toFixed(1) + 'k';
        }
        return val;
    };

    // Calculate dynamic performance-based rank (E, D, C, B, A, S)
    const calculateUserRank = () => {
        const streak = user.gamification?.streak || 0;
        const maps = user.counters?.mapsCount || 0;
        const summaries = user.counters?.summariesCount || 0;
        const flashcards = user.counters?.totalFlashcardsCreated || 0;

        // Score formulation: flashcards created weight 2, streak weight 25, maps/summaries weight 10
        const score = (flashcards * 2) + (streak * 25) + (maps * 10) + (summaries * 10);

        let grade = "E";
        let progressValue = 0;
        let color = "gray.5";

        if (score < 500) {
            grade = "E";
            progressValue = (score / 500) * 100;
            color = "gray.5";
        } else if (score < 1200) {
            grade = "D";
            progressValue = ((score - 500) / 700) * 100;
            color = "orange.5";
        } else if (score < 2200) {
            grade = "C";
            progressValue = ((score - 1200) / 1000) * 100;
            color = "yellow.5";
        } else if (score < 3500) {
            grade = "B";
            progressValue = ((score - 2200) / 1300) * 100;
            color = "green.5";
        } else if (score < 5000) {
            grade = "A";
            progressValue = ((score - 3500) / 1500) * 100;
            color = "blue.5";
        } else {
            grade = "S";
            progressValue = Math.min(((score - 5000) / 3000) * 100 + 50, 100);
            color = "grape.6";
        }

        return {
            grade,
            progressValue: Math.round(progressValue),
            color
        };
    };

    const rank = calculateUserRank();

    return (
        <Container className={styles.leftCard}>
            <Stack justify="space-between" className={styles.overviewStack} gap="xl">
                <Stack gap="sm">
                    <Title order={2} className={styles.sectionTitle}>
                        Estatísticas
                    </Title>

                    <Flex direction={{ base: 'column', sm: 'row' }} justify="space-between" align="center" gap="md" mt="md" mb="md">
                        {/* List of Stats */}
                        <Stack className={styles.statList} gap="sm">
                            <Group gap="md" wrap="nowrap">
                                <IconFlame size={32} color="#ff9f1c" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Total de Dias de Ofensiva</Text>
                                    <Text className={styles.statValue}>{user.gamification?.streak || 0} dias</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <IconCards size={32} color="#2196f3" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Cartões na Fila Hoje:</Text>
                                    <Text className={styles.statValue}>{user.counters?.pendingFlashcardsToday || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <IconSitemap size={32} color="#00bcd4" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Mapas Mentais:</Text>
                                    <Text className={styles.statValue}>{user.counters?.mapsCount || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <IconFileText size={32} color="#9c27b0" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Resumos:</Text>
                                    <Text className={styles.statValue}>{user.counters?.summariesCount || 0}</Text>
                                </Stack>
                            </Group>
                            <Group gap="md" wrap="nowrap">
                                <IconBook size={32} color="#795548" />
                                <Stack gap={2}>
                                    <Text size="xs" className={styles.statLabel}>Total de Cartões Criados:</Text>
                                    <Text className={styles.statValue}>{formatCount(user.counters?.totalFlashcardsCreated || 0)}</Text>
                                </Stack>
                            </Group>
                        </Stack>

                        {/* Ring Chart of Performance Rank */}
                        <Group gap="md" justify="center">
                            <RingProgress
                                size={300}
                                thickness={25}
                                roundCaps
                                sections={[{ value: rank.progressValue, color: rank.color }]}
                                label={
                                    <Stack gap={0} align="center" justify="center">
                                        <Text size="5rem" fw={900} c={rank.color} lh={1} className={styles.studexLogoText}>
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

                {/* Subject Distribution */}
                <Stack className={styles.segmentedBarContainer} gap="xs">
                    <Title order={3} className={styles.sectionTitle} style={{ fontSize: "1.1rem" }}>
                        Assuntos de Cartões Mais Usados
                    </Title>

                    <Progress.Root size="lg" radius="xl">
                        {stats.statsDistribution?.map((item, idx) => (
                            <Progress.Section
                                key={idx}
                                value={item.percentage}
                                color={item.color}
                            />
                        ))}
                    </Progress.Root>

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
