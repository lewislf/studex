import { Group } from "@mantine/core";
import styles from '../../styles/Home/Home.module.css'
import HomeCard from "./HomeCard";
import { IconFlame } from '@tabler/icons-react';

/**
 * Orchestrator block tracking system gamification and milestones.
 */
export default function HomeStats({streak, summaries, mind_maps, today}) {
    return (
        <Group justify="center" grow className={styles.stats}>
            <HomeCard
                title="STREAK"
                text={`${streak} dias`}
                Icon={IconFlame}
                iconColor="orange"
            />
            <HomeCard title="RESUMOS" text={summaries}/>
            <HomeCard title="MAPAS MENTAIS" text={mind_maps}/>
            <HomeCard title="NA FILA" text={today}/>
        </Group>
    );
}

