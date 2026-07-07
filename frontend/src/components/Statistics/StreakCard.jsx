import { Container, Stack, Group, Text } from "@mantine/core";
import { IconFlame, IconCheck } from '@tabler/icons-react';
import styles from '../../styles/Statistics/Statistics.module.css';

import { WEEKDAYS_TITLE } from '../../config/Constants';

/**
 * StreakCard displays the user's active streak count alongside
 * a visual calendar tracking streak compliance across the current week.
 */
export default function StreakCard({ user }) {
    const todayIndex = new Date().getDay(); // Current day of the week index (0-6)

    return (
        <Container className={styles.rightCard}>
            <Stack align="center" justify="center" gap="xs">
                {/* Active gamification fire icon marker */}
                <IconFlame size={80} color="#ff9f1c" className={styles.flameIcon} />
                {/* Consecutive study days count */}
                <Text className={styles.streakCount}>{user.gamification?.streak || 0}</Text>
                <Text className={styles.streakLabel}>dias de ofensiva</Text>

                {/* Weekdays Row displaying status circles */}
                <Group className={styles.weekdaysContainer} justify="center" gap="md" mb="md" wrap="nowrap">
                    {WEEKDAYS_TITLE.map((day, idx) => {
                        const isActive = idx === todayIndex;
                        return (
                            <Stack key={day} className={styles.weekdayItem} gap={4} align="center">
                                {/* Weekday letter header label */}
                                <Text size="xs" fw={600} c="dimmed">
                                    {day}
                                </Text>
                                {/* Indicator circle with active glow styling */}
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

                {/* Encouraging motivational message footer */}
                <Text className={styles.streakMessage}>
                    Você manteve sua ofensiva com mais de <Text span className={styles.streakHighlight}>13 horas</Text> restantes no dia. Bom trabalho!
                </Text>
            </Stack>
        </Container>
    );
}
