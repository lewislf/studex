import { useState } from "react";
import { Container, Stack } from "@mantine/core";
import HomeTitle from "./HomeTitle";
import HomeStats from "./HomeStats.jsx";
import styles from '../../styles/Home/Home.module.css'
import { useOutletContext } from "react-router";
import HomeCreationGrid from "./HomeCreationGrid.jsx";
import HomePdfDropzone from "./HomePdfDropzone.jsx";
import { CREATION_OPTIONS } from "../../config/Constants.js";

/**
 * Parent view container for the application root dashboard entry point.
 */
export default function Home() {
    const { refreshUser: _r, ...user } = useOutletContext();

    // Which materials the next upload should generate. Defaults to all
    // three (matches the backend contract: an omitted `materials` field
    // generates everything).
    const [selectedMaterials, setSelectedMaterials] = useState(
        () => new Set(CREATION_OPTIONS.map((option) => option.value))
    );

    function toggleMaterial(value) {
        setSelectedMaterials((prev) => {
            const next = new Set(prev);
            if (next.has(value)) {
                next.delete(value);
            } else {
                next.add(value);
            }
            return next;
        });
    }

    return (
        <Container size="xl" className={styles.container}>
            <Stack gap="xl">
                {/* Greeting banner introducing */}
                <HomeTitle
                    name={user.name}
                    pendingFlashcards={user.counters.pendingFlashcardsToday}
                />

                {/* Gamification tracking grid */}
                <HomeStats
                    streak={user.gamification.streak}
                    summaries={user.counters.summariesCount}
                    mind_maps={user.counters.mapsCount}
                    totalFlashcards={user.counters.totalFlashcardsCreated}
                />

                {/* Material generator modular option selector */}
                <HomeCreationGrid selected={selectedMaterials} onToggle={toggleMaterial} />

                {/* Core file dropzone gateway handling local pdf multi-part network uploads */}
                <HomePdfDropzone selectedMaterials={selectedMaterials} />
            </Stack>
        </Container>
    )
}
