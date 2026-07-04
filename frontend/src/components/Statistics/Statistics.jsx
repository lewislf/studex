import { Container, Stack } from "@mantine/core";
import { useOutletContext } from "react-router";
import styles from '../../styles/Statistics/Statistics.module.css';
import userStatsMock from '../../config/userStatsMock.json';
import { parseUserStats } from '../../utils/userHelpers.js';

import StatisticsTitle from "./StatisticsTitle.jsx";
import StatisticsOverviewCard from "./StatisticsOverviewCard.jsx";
import StreakCard from "./StreakCard.jsx";
import StatisticsHeatmap from "./StatisticsHeatmap.jsx";

/**
 * Parent view container for the application statistics dashboard route entry point.
 * Integrates overview metrics, streaks, and historical calendars.
 */
export default function Statistics() {
    // Consume global profile entities streamed down from the root route layout context
    const user = useOutletContext();
    const stats = parseUserStats(userStatsMock);

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                {/* Greeting banner introducing the statistics view */}
                <StatisticsTitle />

                {/* Dashboard layout partitioning user counters and streak widgets */}
                <div className={styles.dashboardGrid}>
                    {/* General performance overview card */}
                    <StatisticsOverviewCard user={user} stats={stats} />
                    {/* Gamified weekly streak component */}
                    <StreakCard user={user} />
                </div>

                {/* Historical contribution calendar widget */}
                <StatisticsHeatmap stats={stats} />
            </Stack>
        </Container>
    );
}
