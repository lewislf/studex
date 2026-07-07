import { Text, Group, Button, Box, Stack } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';
import SubjectIcon from '../Common/SubjectIcon';

/**
 * RevisionsDeckCard renders a single deck card row with dynamic subject indicators,
 * customized color icons, splits review counts, and action buttons.
 *
 * @param {Object} props
 * @param {Object} props.deck - Individual deck representation attributes.
 */
export default function RevisionsDeckCard({ deck }) {
    if (!deck) return null;

    return (
        <Box className={styles.deckCard}>
            {/* Color stripe left indicator */}
            <Box
                className={styles.cardStripe}
                style={{ backgroundColor: deck.color }}
            />

            <Box className={styles.cardContent}>
                {/* Deck details details */}
                <Box className={styles.deckInfo}>
                    <Box
                        className={styles.iconBox}
                        style={{ backgroundColor: `${deck.color}15`, color: deck.color }}
                    >
                        <SubjectIcon name={deck.icon} size={22} color={deck.color} />
                    </Box>
                    <Stack gap={2}>
                        <Text className={styles.deckTitle}>{deck.subjectName}</Text>
                        <Text className={styles.deckSubtitle}>{deck.subtitle?.toLowerCase()}</Text>
                    </Stack>
                </Box>

                {/* Split counts and actions */}
                <Group gap="xl">
                    <Box className={styles.countsGroup}>
                        {deck.new > 0 && (
                            <Text className={styles.countLabel} c="dimmed">
                                <Text span className={`${styles.countValue} ${styles.countNew}`}>{deck.new}</Text> novos
                            </Text>
                        )}
                        {deck.learning > 0 && (
                            <Text className={styles.countLabel} c="dimmed">
                                <Text span className={`${styles.countValue} ${styles.countLearning}`}>{deck.learning}</Text> aprender
                            </Text>
                        )}
                        {deck.review > 0 && (
                            <Text className={styles.countLabel} c="dimmed">
                                <Text span className={`${styles.countValue} ${styles.countReview}`}>{deck.review}</Text> revisar
                            </Text>
                        )}
                    </Box>
                    <Text className={styles.totalCards}>
                        {deck.totalCards} cards
                    </Text>
                    <Button variant="outline" className={styles.revisarButton}>
                        revisar &gt;
                    </Button>
                </Group>
            </Box>
        </Box>
    );
}
