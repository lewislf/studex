import { Container, Stack, Group, Text } from "@mantine/core";
import { IconFlame, IconCheck } from '@tabler/icons-react';
import styles from '../../styles/Statistics/Statistics.module.css';

export default function StreakCard({ user }) {
    // weekdays abbreviations
    const weekdaysLabels = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
    const todayIndex = new Date().getDay(); // Current day of the week

    return (
        <Container className={styles.rightCard}>
            <Stack align="center" justify="center" gap="xs">
                <IconFlame size={80} color="#ff9f1c" className={styles.flameIcon} />
                <Text className={styles.streakCount}>{user.gamification?.streak || 0}</Text>
                <Text className={styles.streakLabel}>dias de ofensiva</Text>

                {/* Weekdays Row with increased horizontal spacing */}
                <Group className={styles.weekdaysContainer} justify="center" gap="md" mb="md" wrap="nowrap">
                    {weekdaysLabels.map((day, idx) => {
                        const isActive = idx === todayIndex;
                        return (
                            <Stack key={day} className={styles.weekdayItem} gap={4} align="center">
                                <Text size="xs" fw={600} c="dimmed">
                                    {day}
                                </Text>
                                <div 
                                    className={`${styles.checkmarkCircle} ${
                                        isActive ? styles.checkmarkBlue : styles.checkmarkOrange
                                    }`}
                                >
                                    <IconCheck size={16} stroke={3} />
                                </div>
                            </Stack>
                        );
                    })}
                </Group>

                {/* Motivator message */}
                <Text className={styles.streakMessage}>
                    Você manteve sua ofensiva com mais de <Text span className={styles.streakHighlight}>13 horas</Text> restantes no dia. Bom trabalho!
                </Text>
            </Stack>
        </Container>
    );
}
