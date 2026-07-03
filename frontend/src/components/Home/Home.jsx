import { Container, Stack } from "@mantine/core";
import HomeTitle from "./HomeTitle";
import HomeStats from "./HomeStats.jsx";
import styles from '../../styles/Home/Home.module.css'
import { useOutletContext } from "react-router";
import HomeCreationGrid from "./CreationGrid.jsx";
import HomePdfDropzone from "./HomePdfDropzone.jsx";

export default function Home() {
    const user = useOutletContext();

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                <HomeTitle
                    name={user.name}
                    totalFlashcards={user.counters.totalFlashcardsCreated}
                />
                <HomeStats
                    streak={user.gamification.streak}
                    summaries={user.counters.summariesCount}
                    mind_maps={user.counters.mapsCount}
                    today={user.counters.pendingFlashcardsToday}
                />
                <HomeCreationGrid />
                <HomePdfDropzone />
            </Stack>
        </Container>
    )
}

