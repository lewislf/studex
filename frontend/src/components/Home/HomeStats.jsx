import { Group } from "@mantine/core";
import styles from '../../styles/Home/Home.module.css';
import HomeCard from "./HomeCard";
import SubjectIcon from "../Common/SubjectIcon";

/**
 * Orchestrator block tracking system gamification and milestones.
 */
export default function HomeStats({ streak, summaries, mind_maps, today }) {
    return (
        <Group justify="center" grow className={styles.stats}>
            <HomeCard
                title="STREAK"
                text={`${streak} dias`}
                Icon={(props) => <SubjectIcon name="flame" {...props} />}
                iconColor="orange"
            />
            <HomeCard title="RESUMOS" text={summaries}/>
            <HomeCard title="MAPAS MENTAIS" text={mind_maps}/>
            <HomeCard title="NA FILA" text={today}/>
        </Group>
    );
}
