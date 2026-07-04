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

    return (
        <Container className={styles.leftCard}>
            <Stack justify="space-between" className={styles.overviewStack} gap="xl">
                <Stack gap="sm">
                    <Title order={2} className={styles.burgundyTitle}>
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

                        {/* Ring Charts */}
                        <Group gap="md" justify="center">
                            {/* Big Donut */}
                            <RingProgress
                                size={140}
                                thickness={14}
                                roundCaps
                                sections={[{ value: 65, color: "blue.4" }]}
                                label={
                                    <Text size="2rem" fw={800} c="blue.4" ta="center" className={styles.studexLogoText}>
                                        S
                                    </Text>
                                }
                            />

                            {/* Small Donut Stack */}
                            <Stack gap="sm">
                                <Stack gap={2} align="center">
                                    <Text className={styles.smallCircleLabel}>Línguas Estrangeiras</Text>
                                    <RingProgress
                                        size={65}
                                        thickness={6}
                                        roundCaps
                                        sections={[{ value: 70, color: "pink.4" }]}
                                        label={
                                            <Text size="xs" fw={700} c="pink.5" ta="center">
                                                70%
                                            </Text>
                                        }
                                    />
                                </Stack>
                                <Stack gap={2} align="center">
                                    <Text className={styles.smallCircleLabel}>Medicina</Text>
                                    <RingProgress
                                        size={65}
                                        thickness={6}
                                        roundCaps
                                        sections={[{ value: 30, color: "pink.4" }]}
                                        label={
                                            <Text size="xs" fw={700} c="pink.5" ta="center">
                                                30%
                                            </Text>
                                        }
                                    />
                                </Stack>
                            </Stack>
                        </Group>
                    </Flex>
                </Stack>

                {/* Subject Distribution */}
                <Stack className={styles.segmentedBarContainer} gap="xs">
                    <Title order={3} className={styles.burgundyTitle} style={{ fontSize: "1.1rem" }}>
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
