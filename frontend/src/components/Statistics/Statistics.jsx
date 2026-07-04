import { Container, Stack } from "@mantine/core";
import { useOutletContext } from "react-router";
import styles from '../../styles/Statistics/Statistics.module.css';
import userStatsMock from '../../config/userStatsMock.json';
import { parseUserStats } from '../../utils/userHelpers.js';

import StatisticsTitle from "./StatisticsTitle.jsx";
import StatisticsOverviewCard from "./StatisticsOverviewCard.jsx";
import StreakCard from "./StreakCard.jsx";
import ActivityHeatmap from "./ActivityHeatmap.jsx";

/**
 * Main dashboard view module representing the Statistics layout.
 * Cohesive integration of child widgets monitoring student progress metrics.
 */
export default function Statistics() {
    const user = useOutletContext();
    const stats = parseUserStats(userStatsMock);

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                {/* Header title block */}
                <StatisticsTitle />

                {/* Dashboard section */}
                <div className={styles.dashboardGrid}>
                    <StatisticsOverviewCard user={user} stats={stats} />
                    <StreakCard user={user} />
                </div>

                {/* Year activity heatmap block */}
                <ActivityHeatmap stats={stats} />
            </Stack>
        </Container>
    );
}
