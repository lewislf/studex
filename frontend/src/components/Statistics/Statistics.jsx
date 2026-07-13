import { useEffect, useState } from "react";
import { Container, Stack, Alert } from "@mantine/core";
import { IconAlertCircle } from '@tabler/icons-react';
import { useOutletContext } from "react-router";
import styles from '../../styles/Statistics/Statistics.module.css';
import { parseUserStats } from '../../utils/userHelpers.js';
import { fetchActivity } from './api.js';

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

    // Activity summary (heatmap days + streak) comes from its own endpoint,
    // fetched on mount. Starts null: the dashboard renders right away with an
    // empty heatmap, then fills in once the request resolves.
    const [activity, setActivity] = useState(null);
    const [activityError, setActivityError] = useState(false);

    useEffect(() => {
        let cancelled = false;

        fetchActivity(user.id)
            .then((data) => {
                if (!cancelled) setActivity(data);
            })
            .catch(() => {
                if (!cancelled) setActivityError(true);
            });

        return () => {
            cancelled = true;
        };
    }, [user.id]);

    const stats = parseUserStats(activity ? { activity_heatmap: activity.days } : {});

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                {/* Greeting banner introducing the statistics view */}
                <StatisticsTitle />

                {activityError && (
                    <Alert variant="light" color="yellow" icon={<IconAlertCircle size={16} />}>
                        Não foi possível carregar sua atividade recente agora.
                    </Alert>
                )}

                {/* Dashboard layout partitioning user counters and streak widgets */}
                <div className={styles.dashboardGrid}>
                    {/* General performance overview card */}
                    <StatisticsOverviewCard user={user} stats={stats} />
                    {/* Gamified weekly streak component */}
                    <StreakCard user={user} days={stats.activityHeatmap} />
                </div>

                {/* Historical contribution calendar widget */}
                <StatisticsHeatmap stats={stats} />
            </Stack>
        </Container>
    );
}
