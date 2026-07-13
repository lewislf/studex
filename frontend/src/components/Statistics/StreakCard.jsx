import { Container, Stack, Group, Text } from "@mantine/core";
import { IconFlame, IconCheck } from '@tabler/icons-react';
import styles from '../../styles/Statistics/Statistics.module.css';

import { WEEKDAYS_TITLE } from '../../config/Constants';

/**
 * StreakCard displays the user's active streak count alongside
 * a visual calendar tracking streak compliance across the current week.
 *
 * @param {Object} user - Outlet context user, carrying gamification.current_streak.
 * @param {Object<string, number>} [days] - Local ISO day -> activity count map,
 * used to mark which days of the current week already had activity.
 */
export default function StreakCard({ user, days = {} }) {
    const now = new Date();
    const todayIndex = now.getDay(); // Current day of the week index (0-6)
    const todayLocal = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const streak = user.gamification?.current_streak ?? user.gamification?.streak ?? 0;

    // Horas reais restantes até meia-noite, não um número fixo.
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    const hoursRemaining = Math.max(1, Math.round((midnight - now) / (1000 * 60 * 60)));

    // Sunday of the current week, so the row always reflects the week in progress
    const weekStart = new Date(todayLocal);
    weekStart.setDate(weekStart.getDate() - todayIndex);

    const weekDays = WEEKDAYS_TITLE.map((label, idx) => {
        const date = new Date(weekStart);
        date.setDate(weekStart.getDate() + idx);
        const yyyy = date.getFullYear();
        const mm = String(date.getMonth() + 1).padStart(2, '0');
        const dd = String(date.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;

        return {
            label,
            isToday: idx === todayIndex,
            isFuture: date > todayLocal,
            hasActivity: Boolean(days[dateStr]),
        };
    });

    return (
        <Container className={styles.rightCard}>
            <Stack align="center" justify="center" gap="xs">
                {/* Active gamification fire icon marker */}
                <IconFlame size={80} color="#ff9f1c" className={styles.flameIcon} />
                {/* Consecutive study days count */}
                <Text className={styles.streakCount}>{streak}</Text>
                <Text className={styles.streakLabel}>dias de ofensiva</Text>

                {/* Weekdays Row displaying status circles */}
                <Group className={styles.weekdaysContainer} justify="center" gap="md" mb="md" wrap="nowrap">
                    {weekDays.map((day) => {
                        // Blue + check only for today when it already has activity;
                        // an outline marks today while it's still pending. Past days
                        // get an orange check when they had activity, and stay dim
                        // otherwise. Future days always stay dim.
                        let modifierClass = '';
                        let showCheck = false;

                        if (day.isToday && day.hasActivity) {
                            modifierClass = styles.checkmarkBlue;
                            showCheck = true;
                        } else if (day.isToday) {
                            modifierClass = styles.checkmarkTodayOutline;
                        } else if (!day.isFuture && day.hasActivity) {
                            modifierClass = styles.checkmarkOrange;
                            showCheck = true;
                        }

                        return (
                            <Stack key={day.label} className={styles.weekdayItem} gap={4} align="center">
                                {/* Weekday letter header label */}
                                <Text size="xs" fw={600} c="dimmed">
                                    {day.label}
                                </Text>
                                {/* Indicator circle with active glow styling */}
                                <div className={`${styles.checkmarkCircle} ${modifierClass}`.trim()}>
                                    {showCheck && <IconCheck size={16} stroke={3} />}
                                </div>
                            </Stack>
                        );
                    })}
                </Group>

                {/* Encouraging motivational message footer: never claims an
                    active streak for a user who hasn't studied anything yet. */}
                <Text className={styles.streakMessage}>
                    {streak === 0 ? (
                        <>Você ainda não tem uma ofensiva. Revise um baralho hoje pra começar!</>
                    ) : (
                        <>Você manteve sua ofensiva com mais de <Text span className={styles.streakHighlight}>{hoursRemaining} horas</Text> restantes no dia. Bom trabalho!</>
                    )}
                </Text>
            </Stack>
        </Container>
    );
}
