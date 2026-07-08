import { Text, Button, Box } from "@mantine/core";
import { useState } from "react";
import styles from '../../styles/Revisions/Revisions.module.css';
import RevisionsDeckCard from './RevisionsDeckCard';

/**
 * RevisionsDeckList orchestrates the card row grid lists, providing dynamic
 * tab selection buttons to filter cards by subject name.
 *
 * @param {Object} props
 * @param {Array} props.decksToday - List of daily decks.
 */
export default function RevisionsDeckList({ decksToday = [] }) {
    // Selected category pill tab filters
    const [activeFilter, setActiveFilter] = useState('all');

    // Filters cards matching active tabs
    const filteredDecks = activeFilter === 'all'
        ? decksToday
        : decksToday.filter(deck => deck.subjectName === activeFilter);

    return (
        <Box className={styles.decksSection}>
            <Box className={styles.decksHeader}>
                <Text className={styles.decksTitle}>Baralhos de Hoje</Text>

                {/* Filter buttons pills */}
                <Box className={styles.filterRow}>
                    <Button
                        variant="subtle"
                        onClick={() => setActiveFilter('all')}
                        className={`${styles.filterPill} ${activeFilter === 'all' ? styles.filterPillActive : styles.filterPillInactive}`}
                    >
                        Todas
                    </Button>
                    {decksToday.map(deck => (
                        <Button
                            key={deck.subjectId}
                            variant="subtle"
                            onClick={() => setActiveFilter(deck.subjectName)}
                            className={`${styles.filterPill} ${activeFilter === deck.subjectName ? styles.filterPillActive : styles.filterPillInactive}`}
                        >
                            <Box span="span" className={styles.pillDot} style={{ backgroundColor: deck.color }} />
                            {deck.subjectName}
                        </Button>
                    ))}
                </Box>
            </Box>

            {/* List rendered rows */}
            <Box className={styles.deckList}>
                {filteredDecks.length === 0 ? (
                    <Text c="dimmed" ta="center" py="lg">
                        Nenhuma revisão por aqui ainda. Envie um material para gerar baralhos.
                    </Text>
                ) : (
                    filteredDecks.map(deck => (
                        <RevisionsDeckCard key={deck.subjectId} deck={deck} />
                    ))
                )}
            </Box>
        </Box>
    );
}
