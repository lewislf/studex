import { Container, Stack } from "@mantine/core";
import HomeTitle from "./HomeTitle";
import HomeStats from "./HomeStats.jsx";
import styles from '../../styles/Home/Home.module.css'
import { useOutletContext } from "react-router";
import HomeCreationGrid from "./CreationGrid.jsx";
import HomePdfDropzone from "./HomePdfDropzone.jsx";

/**
 * Parent view container for the application root dashboard entry point.
 */
export default function Home() {
    // Consume global profile entities streamed down from the root route layout context
    const user = useOutletContext();

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                {/* Greeting banner introducing */}
                <HomeTitle
                    name={user.name}
                    totalFlashcards={user.counters.totalFlashcardsCreated}
                />

                {/* Gamification tracking grid */}
                <HomeStats
                    streak={user.gamification.streak}
                    summaries={user.counters.summariesCount}
                    mind_maps={user.counters.mapsCount}
                    today={user.counters.pendingFlashcardsToday}
                />

                {/* Material generator modular option selector */}
                <HomeCreationGrid />

                {/* Core file dropzone gateway handling local pdf multi-part network uploads */}
                <HomePdfDropzone />
            </Stack>
        </Container>
    )
}

