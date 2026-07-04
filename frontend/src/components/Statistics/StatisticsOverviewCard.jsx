import { Title, Text, RingProgress, Progress } from "@mantine/core";
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
        <div className={styles.leftCard}>
            <div>
                <Title order={2} className={styles.burgundyTitle}>
                    Estatísticas
                </Title>

                <div className={styles.progressContainer}>
                    {/* List of Stats */}
                    <div className={styles.statList}>
                        <div className={styles.statItem}>
                            <IconFlame size={32} color="#ff9f1c" />
                            <div className={styles.statTextContainer}>
                                <span className={styles.statLabel}>Total de Dias de Ofensiva</span>
                                <span className={styles.statValue}>{user.gamification?.streak || 0} dias</span>
                            </div>
                        </div>
                        <div className={styles.statItem}>
                            <IconCards size={32} color="#2196f3" />
                            <div className={styles.statTextContainer}>
                                <span className={styles.statLabel}>Cartões na Fila Hoje:</span>
                                <span className={styles.statValue}>{user.counters?.pendingFlashcardsToday || 0}</span>
                            </div>
                        </div>
                        <div className={styles.statItem}>
                            <IconSitemap size={32} color="#00bcd4" />
                            <div className={styles.statTextContainer}>
                                <span className={styles.statLabel}>Mapas Mentais:</span>
                                <span className={styles.statValue}>{user.counters?.mapsCount || 0}</span>
                            </div>
                        </div>
                        <div className={styles.statItem}>
                            <IconFileText size={32} color="#9c27b0" />
                            <div className={styles.statTextContainer}>
                                <span className={styles.statLabel}>Resumos:</span>
                                <span className={styles.statValue}>{user.counters?.summariesCount || 0}</span>
                            </div>
                        </div>
                        <div className={styles.statItem}>
                            <IconBook size={32} color="#795548" />
                            <div className={styles.statTextContainer}>
                                <span className={styles.statLabel}>Total de Cartões Criados:</span>
                                <span className={styles.statValue}>{formatCount(user.counters?.totalFlashcardsCreated || 0)}</span>
                            </div>
                        </div>
                    </div>

                    {/* Ring Charts */}
                    <div className={styles.circleWrapper}>
                        {/* Big Donut */}
                        <RingProgress
                            size={140}
                            thickness={14}
                            roundCaps
                            sections={[{ value: 65, color: "blue.4" }]}
                            label={
                                <Text size="2rem" fw={800} c="blue.4" ta="center" style={{ fontFamily: 'sans-serif' }}>
                                    S
                                </Text>
                            }
                        />

                        {/* Small Donut Stack */}
                        <div className={styles.smallCircles}>
                            <div className={styles.smallCircleItem}>
                                <span className={styles.smallCircleLabel}>Línguas Estrangeiras</span>
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
                            </div>
                            <div className={styles.smallCircleItem}>
                                <span className={styles.smallCircleLabel}>Medicina</span>
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
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Subject Distribution */}
            <div className={styles.segmentedBarContainer}>
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

                <div className={styles.legendGrid}>
                    {stats.statsDistribution?.map((item, idx) => (
                        <div key={idx} className={styles.legendItem}>
                            <div 
                                className={styles.legendColor} 
                                style={{ backgroundColor: item.color }} 
                            />
                            <span>{item.label}: {item.percentage}%</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
