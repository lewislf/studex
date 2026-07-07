import { Text, Group, Button, Box, Stack } from "@mantine/core";
import {
    IconGlobe,
    IconRocket,
    IconSchool,
    IconUsers,
    IconDatabase,
    IconBook,
    IconCalculator,
    IconFlask,
    IconCode,
    IconLanguage,
    IconBrain,
    IconPalette,
    IconHistory,
    IconMicroscope,
    IconHeart,
    IconScale,
    IconAtom
} from '@tabler/icons-react';
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsDeckCard renders a single deck card row with dynamic subject indicators,
 * customized color icons, splits review counts, and action buttons.
 *
 * @param {Object} props
 * @param {Object} props.deck - Individual deck representation attributes.
 */
export default function RevisionsDeckCard({ deck }) {
    if (!deck) return null;

    // Resolve dynamic icon component
    const getDeckIconComponent = (iconName) => {
        switch (iconName) {
            case 'sigma': return () => <span style={{ fontFamily: 'serif', fontSize: '1.25rem', fontWeight: 900 }}>Σ</span>;
            case 'atom': return IconAtom;
            case 'globe': return IconGlobe;
            case 'rocket': return IconRocket;
            case 'user-teacher': return IconSchool;
            case 'users': return IconUsers;
            case 'database': return IconDatabase;
            case 'calculator': return IconCalculator;
            case 'flask': return IconFlask;
            case 'code': return IconCode;
            case 'language': return IconLanguage;
            case 'brain': return IconBrain;
            case 'palette': return IconPalette;
            case 'history': return IconHistory;
            case 'microscope': return IconMicroscope;
            case 'heart': return IconHeart;
            case 'scale': return IconScale;
            default: return IconBook;
        }
    };

    const IconComponent = getDeckIconComponent(deck.icon);

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
                        <IconComponent size={22} />
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
