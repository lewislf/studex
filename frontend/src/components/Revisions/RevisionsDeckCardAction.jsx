import { Box, Group, Text, Button } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsDeckCardAction displays the split review counts, total cards, and the review button.
 */
export default function RevisionsDeckCardAction({ newCount, learningCount, reviewCount, totalCards }) {
    return (
        <Group gap="xl">
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
            <Text className={styles.totalCards}>
                {totalCards} cards
            </Text>
            <Button variant="outline" className={styles.revisarButton}>
                revisar &gt;
            </Button>
        </Group>
    );
}
