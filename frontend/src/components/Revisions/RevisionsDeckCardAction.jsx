import { Box, Group, Text } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsDeckCardAction displays the split review counts, total cards, and a
 * "revisar" indicator. The card itself is the clickable link (see
 * RevisionsDeckCard), so this is a plain visual cue instead of a nested button.
 *
 * @param {Object} props
 * @param {number} props.newCount - Quantity of new cards.
 * @param {number} props.learningCount - Quantity of learning cards.
 * @param {number} props.reviewCount - Quantity of cards to review.
 * @param {number} props.totalCards - Sum of cards inside this deck.
 */
export default function RevisionsDeckCardAction({ newCount, learningCount, reviewCount, totalCards }) {
    // A divisão só soma informação quando o baralho tem uma mistura de
    // status: com um baralho 100% novo, "20 novos" e "20 cards" repetem o
    // mesmo número, então a divisão fica escondida e só o total aparece.
    const nonZeroBuckets = [newCount, learningCount, reviewCount].filter((c) => c > 0).length;
    const showBreakdown = nonZeroBuckets > 1;

    return (
        <Group gap="xl">
            {showBreakdown && (
                <Box className={styles.countsGroup}>
                    {newCount > 0 && (
                        <Text className={styles.countLabel} c="dimmed">
                            <Text span className={`${styles.countValue} ${styles.countNew}`}>{newCount}</Text> novos
                        </Text>
                    )}
                    {learningCount > 0 && (
                        <Text className={styles.countLabel} c="dimmed">
                            <Text span className={`${styles.countValue} ${styles.countLearning}`}>{learningCount}</Text> aprender
                        </Text>
                    )}
                    {reviewCount > 0 && (
                        <Text className={styles.countLabel} c="dimmed">
                            <Text span className={`${styles.countValue} ${styles.countReview}`}>{reviewCount}</Text> revisar
                        </Text>
                    )}
                </Box>
            )}
            <Text className={styles.totalCards}>
                {totalCards} cards
            </Text>
            <Text className={styles.revisarButton} component="span">
                revisar &gt;
            </Text>
        </Group>
    );
}
