import { SimpleGrid } from "@mantine/core";
import styles from '../../styles/Home/Home.module.css';
import HomeCard from "./HomeCard";
import SubjectIcon from "../Common/SubjectIcon";

/**
 * Orchestrator block tracking system gamification and milestones.
 */
export default function HomeStats({ streak, summaries, mind_maps, totalFlashcards }) {
    return (
        // 2 colunas no celular, 4 a partir do "sm"
        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing={{ base: 'sm', sm: 'lg' }} className={styles.stats}>
            <HomeCard
                title="STREAK"
                text={`${streak} dias`}
                Icon={(props) => <SubjectIcon name="flame" {...props} />}
                iconColor="orange"
            />
            <HomeCard title="RESUMOS" text={summaries}/>
            <HomeCard title="MAPAS MENTAIS" text={mind_maps}/>
            <HomeCard title="FLASHCARDS" text={totalFlashcards}/>
        </SimpleGrid>
    );
}
