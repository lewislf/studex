import { useEffect, useState } from 'react';
import { Text, Group, Badge } from '@mantine/core';
import MaterialSection from './MaterialSection.jsx';
import MaterialIcon from './MaterialIcon.jsx';
import { materialTypeColor } from './materialColors.js';
import { fetchDecks, formatDate, deckTitle, deckDate } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * FlashcardsSection fetches and lists the flashcard decks created for a subject.
 *
 * @param {Object} props
 * @param {string|number} props.userId
 * @param {string|number} props.subjectId
 */
export default function FlashcardsSection({ userId, subjectId }) {
    const color = materialTypeColor('flashcards');
    const [decks, setDecks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!userId || !subjectId) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const data = await fetchDecks(userId, subjectId);
                if (!cancelled) setDecks(data);
            } catch {
                if (!cancelled) setError('Não foi possível carregar os baralhos.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [userId, subjectId]);

    const items = decks.map((deck) => ({
        id: deck.id,
        to: `/materias/${subjectId}/flashcards/${deck.id}`,
        title: deckTitle(deck),
        date: formatDate(deckDate(deck)),
        novos: deck.new || 0,
        aprendendo: deck.learning || 0,
        review: deck.review || 0,
        totalCards: deck.total_cards ?? (deck.new || 0) + (deck.learning || 0) + (deck.review || 0),
    }));

    function renderPreview(item) {
        return (
            <>
                <Group gap={6} wrap="wrap">
                    <Badge size="sm" variant="light" color="blue">{item.novos} novos</Badge>
                    <Badge size="sm" variant="light" color="yellow">{item.aprendendo} aprendendo</Badge>
                    <Badge size="sm" variant="light" color="green">{item.review} revisão</Badge>
                </Group>
                <Text className={styles.materialCardMeta}>{item.totalCards} cards</Text>
            </>
        );
    }

    return (
        <MaterialSection
            title="Flashcards"
            icon={<MaterialIcon type="flashcards" />}
            items={items}
            loading={loading}
            error={error}
            emptyText="Nenhum baralho de flashcards ainda."
            color={color}
            renderPreview={renderPreview}
        />
    );
}
