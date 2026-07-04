import { Text } from "@mantine/core";
import { IconFlame, IconCheck } from '@tabler/icons-react';
import styles from '../../styles/Statistics/Statistics.module.css';

export default function StreakCard({ user }) {
    const weekdaysLabels = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];
    const todayIndex = new Date().getDay(); // Current day of the week

    return (
        <div className={styles.rightCard}>
            <IconFlame size={80} color="#ff9f1c" style={{ fill: "#ff9f1c" }} />
            <span className={styles.streakCount}>{user.gamification?.streak || 0}</span>
            <span className={styles.streakLabel}>day streak</span>

            {/* Weekdays Row */}
            <div className={styles.weekdaysContainer}>
                {weekdaysLabels.map((day, idx) => {
                    const isActive = idx === todayIndex;
                    return (
                        <div key={day} className={styles.weekdayItem}>
                            <span className={styles.weekdayName}>{day}</span>
                            <div 
                                className={`${styles.checkmarkCircle} ${
                                    isActive ? styles.checkmarkBlue : styles.checkmarkOrange
                                }`}
                            >
                                <IconCheck size={16} stroke={3} />
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Motivator message */}
            <Text className={styles.streakMessage}>
                You extended your streak with over <span className={styles.streakHighlight}>13 hours</span> left in the day. Nice work!
            </Text>
        </div>
    );
}
