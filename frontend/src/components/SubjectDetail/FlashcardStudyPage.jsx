import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, useOutletContext, Link } from 'react-router';
import {
    Container, Box, Loader, Alert, Group, Paper, Progress, Text, Title,
    Button, ActionIcon, Menu, Stack, SimpleGrid, Divider,
} from '@mantine/core';
import {
    IconAlertCircle, IconSettings, IconCheck, IconRotate, IconTrophy,
    IconRefresh,
} from '@tabler/icons-react';
import { notifications } from '@mantine/notifications';
import SubjectBreadcrumb from './SubjectBreadcrumb.jsx';
import {
    fetchSubject, fetchStudyQueue, fetchGlobalStudyQueue, reviewFlashcard, deckTitle, stripMaterialSuffix,
} from './api.js';
import styles from '../../styles/SubjectDetail/Flashcards.module.css';

const STORAGE_KEY = 'studex.flashcardsPerSession';
const SESSION_SIZE_OPTIONS = [10, 20, 50, 100];
const DEFAULT_SESSION_SIZE = 20;

/** Reads the persisted "cards per session" preference, falling back to the default. */
function readSessionSize() {
    const raw = Number(localStorage.getItem(STORAGE_KEY));
    return SESSION_SIZE_OPTIONS.includes(raw) ? raw : DEFAULT_SESSION_SIZE;
}

const RATINGS = [
    { value: 'reset', label: 'Reset', color: 'red', Icon: IconRotate, key: '1' },
    { value: 'dificil', label: 'Difícil', color: 'orange', Icon: null, key: '2' },
    { value: 'bom', label: 'Bom', color: 'blue', Icon: null, key: '3' },
    { value: 'facil', label: 'Fácil', color: 'green', Icon: null, key: '4' },
];

/**
 * Spaced-repetition flashcard study page. Supports two modes:
 * - Per-deck ("Suas Matérias > {matéria} > Flashcards > {baralho}"): fetches
 *   the due queue for a single deck via the route params.
 * - Global ("Revisões > Estudo do dia", route "/revisoes/estudar", no
 *   subjectId/deckId params): fetches the due queue across every deck of
 *   every subject, each card carrying its own subject/deck info.
 *
 * Either way it walks the user through the queue one card at a time,
 * submitting a review after each answer. A "reset" rating requeues the card
 * at the end of the session instead of removing it.
 */
export default function FlashcardStudyPage() {
    const { subjectId, deckId } = useParams();
    const isGlobal = !subjectId && !deckId;
    const { refreshUser: _r, ...user } = useOutletContext();

    const [subject, setSubject] = useState(null);
    const [deck, setDeck] = useState(null);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sessionSize, setSessionSize] = useState(readSessionSize);
    const [reloadToken, setReloadToken] = useState(0);
    // Read via a ref inside the fetch effect so changing the setting mid-session
    // doesn't itself trigger a refetch: it only takes effect on the next load
    // (session restart or remount), as requested.
    const sessionSizeRef = useRef(sessionSize);
    useEffect(() => { sessionSizeRef.current = sessionSize; }, [sessionSize]);

    const [queue, setQueue] = useState([]);
    const [revealed, setRevealed] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const [respondedCount, setRespondedCount] = useState(0);
    const [stats, setStats] = useState({ facil: 0, bom: 0, dificil: 0, reset: 0 });

    useEffect(() => {
        if (!user.id) return;
        if (!isGlobal && (!subjectId || !deckId)) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            setRevealed(false);
            setRespondedCount(0);
            setStats({ facil: 0, bom: 0, dificil: 0, reset: 0 });
            try {
                if (isGlobal) {
                    const queueData = await fetchGlobalStudyQueue(user.id, sessionSizeRef.current);
                    if (cancelled) return;
                    if (!queueData) {
                        setError('Não foi possível carregar a fila de estudo.');
                        return;
                    }
                    setSubject(null);
                    setDeck(null);
                    const cards = Array.isArray(queueData.cards) ? queueData.cards : [];
                    setQueue(cards);
                    setTotal(queueData.total ?? cards.length);
                    return;
                }

                const [subjectData, queueData] = await Promise.all([
                    fetchSubject(user.id, subjectId),
                    fetchStudyQueue(user.id, subjectId, deckId, sessionSizeRef.current),
                ]);
                if (cancelled) return;
                if (!subjectData || !queueData) {
                    setError('Baralho não encontrado.');
                    return;
                }
                setSubject(subjectData);
                setDeck(queueData.deck || null);
                const cards = Array.isArray(queueData.cards) ? queueData.cards : [];
                setQueue(cards);
                setTotal(queueData.total ?? cards.length);
            } catch {
                if (!cancelled) setError('Não foi possível carregar os cards para estudo.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [user.id, subjectId, deckId, isGlobal, reloadToken]);

    const currentCard = queue[0] || null;
    const finished = !loading && !error && total > 0 && !currentCard;
    const isEmptyDeck = !loading && !error && total === 0;

    const handleReveal = useCallback(() => {
        if (!currentCard) return;
        setRevealed(true);
    }, [currentCard]);

    const handleRate = useCallback(async (rating) => {
        if (!currentCard || submitting) return;
        setSubmitting(true);
        try {
            // In global mode each card may belong to a different deck/subject,
            // so the review target comes from the card itself.
            const cardSubjectId = isGlobal ? currentCard.subject_id : subjectId;
            const cardDeckId = isGlobal ? currentCard.deck_id : deckId;
            await reviewFlashcard(user.id, cardSubjectId, cardDeckId, currentCard.id, rating);
            setQueue((prev) => {
                const [head, ...rest] = prev;
                return rating === 'reset' ? [...rest, head] : rest;
            });
            setRevealed(false);
            setStats((prev) => ({ ...prev, [rating]: prev[rating] + 1 }));
            if (rating !== 'reset') {
                setRespondedCount((prev) => prev + 1);
            }
        } catch {
            notifications.show({
                title: 'Falha ao registrar revisão',
                message: 'Não foi possível salvar sua resposta. Tente novamente.',
                color: 'red',
            });
        } finally {
            setSubmitting(false);
        }
    }, [currentCard, submitting, user.id, subjectId, deckId, isGlobal]);

    // Keyboard shortcuts: space/enter reveals the answer, 1-4 rate it once revealed.
    useEffect(() => {
        function onKeyDown(event) {
            if (!currentCard || submitting) return;
            if (!revealed) {
                if (event.code === 'Space' || event.code === 'Enter') {
                    event.preventDefault();
                    handleReveal();
                }
                return;
            }
            const rating = RATINGS.find((r) => r.key === event.key);
            if (rating) {
                event.preventDefault();
                handleRate(rating.value);
            }
        }

        window.addEventListener('keydown', onKeyDown);
        return () => window.removeEventListener('keydown', onKeyDown);
    }, [currentCard, revealed, submitting, handleReveal, handleRate]);

    const progressPct = total > 0 ? Math.min(100, (respondedCount / total) * 100) : 0;

    const breadcrumbItems = useMemo(() => {
        if (isGlobal) {
            return [
                { label: 'Revisões', to: '/revisoes' },
                { label: 'Estudo do dia' },
            ];
        }
        if (!subject) return [];
        return [
            { label: 'Suas Matérias', to: '/materias' },
            { label: subject.title || subject.name, to: `/materias/${subjectId}` },
            { label: 'Flashcards', to: `/materias/${subjectId}` },
            { label: deck ? deckTitle(deck) : '' },
        ];
    }, [isGlobal, subject, subjectId, deck]);

    function handleSelectSessionSize(size) {
        setSessionSize(size);
        localStorage.setItem(STORAGE_KEY, String(size));
    }

    function handleRestart() {
        setReloadToken((prev) => prev + 1);
    }

    if (loading) {
        return (
            <Container size="xl" py="xl">
                <Group justify="center"><Loader size="md" /></Group>
            </Container>
        );
    }

    if (error) {
        return (
            <Container size="xl" py="xl">
                <Alert color="red" icon={<IconAlertCircle size={16} />} title="Erro ao carregar">
                    {error}
                </Alert>
            </Container>
        );
    }

    return (
        <Container size="xl" py="md">
            <Box className={styles.page}>
                <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                    <SubjectBreadcrumb items={breadcrumbItems} />
                    <Menu shadow="md" width={220} position="bottom-end">
                        <Menu.Target>
                            <ActionIcon variant="subtle" color="gray" size="lg" aria-label="Configurações de estudo">
                                <IconSettings size={20} />
                            </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                            <Menu.Label>Cards por sessão</Menu.Label>
                            {SESSION_SIZE_OPTIONS.map((size) => (
                                <Menu.Item
                                    key={size}
                                    leftSection={sessionSize === size ? <IconCheck size={14} /> : <Box w={14} />}
                                    onClick={() => handleSelectSessionSize(size)}
                                >
                                    {size}
                                </Menu.Item>
                            ))}
                            <Divider my={4} />
                            <Text size="xs" c="dimmed" px="sm" py={4}>
                                Vale a partir da próxima sessão
                            </Text>
                        </Menu.Dropdown>
                    </Menu>
                </Group>

                {isEmptyDeck && (
                    <EmptyState backTo={isGlobal ? '/revisoes' : `/materias/${subjectId}`} />
                )}

                {finished && (
                    <CompletionState
                        stats={stats}
                        backTo={isGlobal ? '/revisoes' : `/materias/${subjectId}`}
                        onRestart={handleRestart}
                    />
                )}

                {!isEmptyDeck && !finished && currentCard && (
                    <StudyCard
                        card={currentCard}
                        isGlobal={isGlobal}
                        revealed={revealed}
                        respondedCount={respondedCount}
                        total={total}
                        progressPct={progressPct}
                        submitting={submitting}
                        onReveal={handleReveal}
                        onRate={handleRate}
                    />
                )}
            </Box>
        </Container>
    );
}

function EmptyState({ backTo }) {
    return (
        <Paper radius="lg" className={styles.studyCard}>
            <div className={styles.stripe} />
            <Stack align="center" justify="center" gap="md" className={styles.centerState}>
                <Text size="xl">Nenhum card para revisar agora</Text>
                <Button component={Link} to={backTo} variant="light" color="orange">
                    Voltar
                </Button>
            </Stack>
        </Paper>
    );
}

function CompletionState({ stats, backTo, onRestart }) {
    return (
        <Paper radius="lg" className={styles.studyCard}>
            <div className={styles.stripe} />
            <Stack align="center" justify="center" gap="lg" className={styles.centerState}>
                <IconTrophy size={56} color="var(--mantine-color-orange-6)" />
                <Title order={2}>Sessão concluída!</Title>
                <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="lg" className={styles.statsGrid}>
                    <StatTile label="Fácil" value={stats.facil} color="green" />
                    <StatTile label="Bom" value={stats.bom} color="blue" />
                    <StatTile label="Difícil" value={stats.dificil} color="orange" />
                    <StatTile label="Reset" value={stats.reset} color="red" />
                </SimpleGrid>
                <Group gap="sm" mt="md">
                    <Button variant="light" color="gray" leftSection={<IconRefresh size={16} />} onClick={onRestart}>
                        Estudar novamente
                    </Button>
                    <Button component={Link} to={backTo} color="orange">
                        Voltar
                    </Button>
                </Group>
            </Stack>
        </Paper>
    );
}

function StatTile({ label, value, color }) {
    return (
        <Stack align="center" gap={2}>
            <Text size="xl" fw={700} c={color}>{value}</Text>
            <Text size="xs" c="dimmed">{label}</Text>
        </Stack>
    );
}

function StudyCard({ card, isGlobal, revealed, respondedCount, total, progressPct, submitting, onReveal, onRate }) {
    // Global mode mixes cards from different decks/subjects, so each card
    // carries a small breadcrumb-like label above the question.
    const cardOrigin = isGlobal && card.subject_name && card.deck_titulo
        ? `${card.subject_name} · ${stripMaterialSuffix(card.deck_titulo)} — Flashcards`
        : null;

    return (
        <Paper radius="lg" className={styles.studyCard}>
            <div className={styles.stripe} />
            <div className={styles.studyCardInner}>
                <Group justify="space-between" align="center" gap="md" wrap="nowrap">
                    <Progress value={progressPct} color="orange" size="xs" className={styles.progress} />
                    <Text className={styles.counter}>{respondedCount + 1}/{total}</Text>
                </Group>

                {!revealed ? (
                    <Stack align="center" justify="center" gap="xl" className={styles.centerState}>
                        {cardOrigin && <Text size="xs" c="dimmed">{cardOrigin}</Text>}
                        <Text className={styles.question}>{card.pergunta}</Text>
                        <Button size="lg" color="orange" fullWidth className={styles.mainAction} onClick={onReveal}>
                            Mostrar resposta
                        </Button>
                    </Stack>
                ) : (
                    <Stack justify="center" gap="lg" className={styles.centerState}>
                        {cardOrigin && <Text size="xs" c="dimmed">{cardOrigin}</Text>}
                        <Text className={styles.questionSmall}>{card.pergunta}</Text>
                        <Divider />
                        <Text className={styles.answer}>{card.resposta}</Text>
                        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="sm" className={styles.ratingGrid}>
                            {RATINGS.map(({ value, label, color, Icon }) => (
                                <Button
                                    key={value}
                                    size="md"
                                    variant="light"
                                    color={color}
                                    leftSection={Icon ? <Icon size={16} /> : null}
                                    disabled={submitting}
                                    onClick={() => onRate(value)}
                                >
                                    {label}
                                </Button>
                            ))}
                        </SimpleGrid>
                    </Stack>
                )}
            </div>
        </Paper>
    );
}
