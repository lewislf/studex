import { Box } from "@mantine/core";
import { Link } from "react-router";
import styles from '../../styles/Revisions/Revisions.module.css';
import RevisionsDeckCardInfo from "./RevisionsDeckCardInfo";
import RevisionsDeckCardAction from "./RevisionsDeckCardAction";

/**
 * RevisionsDeckCard renders a single deck card row with dynamic subject indicators,
 * customized color icons, splits review counts, and action buttons. The whole
 * card links to the deck's own flashcard study page.
 *
 * @param {Object} props
 * @param {Object} props.deck - Individual deck representation attributes.
 */
export default function RevisionsDeckCard({ deck }) {
    if (!deck) return null;

    return (
        <Box
            component={Link}
            to={`/materias/${deck.subjectId}/flashcards/${deck.id}`}
            className={styles.deckCard}
        >
            {/* Color stripe left indicator */}
            <Box
                className={styles.cardStripe}
                style={{ backgroundColor: deck.color }}
            />

            <Box className={styles.cardContent}>
                {/* Deck details details */}
                <RevisionsDeckCardInfo
                    icon={deck.icon}
                    color={deck.color}
                    subjectName={deck.subjectName}
                    subtitle={deck.subtitle}
                />

                {/* Split counts and actions */}
                <RevisionsDeckCardAction
                    newCount={deck.new}
                    learningCount={deck.learning}
                    reviewCount={deck.review}
                    totalCards={deck.totalCards}
                />
            </Box>
        </Box>
    );
}
