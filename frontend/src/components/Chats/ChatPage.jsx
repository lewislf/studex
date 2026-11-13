import { useEffect, useRef, useState } from 'react';
import { Link, useParams, useOutletContext } from 'react-router';
import { Container, Loader, Alert, Group, Textarea, ActionIcon, Text, Button } from '@mantine/core';
import { IconAlertCircle, IconArrowLeft, IconArrowUp, IconMessageCircle } from '@tabler/icons-react';
import ChatMessage from './ChatMessage.jsx';
import { fetchChat, sendMessage } from './api.js';
import { DEFAULT_SUBJECT_COLOR } from '../../config/Constants';
import styles from '../../styles/Chats/Chats.module.css';

const MAX_PERGUNTA = 1000;

const SUGESTOES = [
    'Resuma os pontos principais do material',
    'Quais conceitos mais caem em prova?',
    'Explique o tema mais difícil com um exemplo',
];

/**
 * Tela de uma conversa: histórico, pergunta e resposta com as fontes.
 */
export default function ChatPage() {
    const { chatId } = useParams();
    const user = useOutletContext();
    const userId = user?.id;

    const [chat, setChat] = useState(null);
    const [mensagens, setMensagens] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(null);
    const [sendError, setSendError] = useState(null);
    const [question, setQuestion] = useState('');
    const [sending, setSending] = useState(false);
    const listRef = useRef(null);

    useEffect(() => {
        if (!userId || !chatId) return;
        let cancelled = false;

        async function load() {
            setLoading(true);
            setLoadError(null);
            try {
                const data = await fetchChat(userId, chatId);
                if (cancelled) return;
                setChat(data);
                setMensagens(data.mensagens || []);
            } catch (err) {
                if (!cancelled) setLoadError(err.status === 404 ? 'Chat não encontrado.' : 'Não foi possível carregar o chat.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [userId, chatId]);

    useEffect(() => {
        // rola só a lista; scrollIntoView rolava a página inteira e tremia com o teclado aberto
        const el = listRef.current;
        if (el) el.scrollTop = el.scrollHeight;
    }, [mensagens, sending]);

    async function send(texto) {
        texto = texto.trim();
        if (!texto || sending) return;

        setSendError(null);
        setSending(true);
        setQuestion('');
        setMensagens((prev) => [...prev, { id: `tmp-${Date.now()}`, papel: 'user', msg: texto }]);

        try {
            const { answer, sources } = await sendMessage(userId, chatId, texto);
            setMensagens((prev) => [...prev, { id: `tmp-${Date.now()}-a`, papel: 'assistant', msg: answer, sources }]);
            setChat((c) => (c?.titulo === 'Novo chat' ? { ...c, titulo: texto.slice(0, 50) } : c));
        } catch (err) {
            // o backend não salvou nada: tira o balão e devolve o texto para tentar de novo
            setMensagens((prev) => prev.slice(0, -1));
            setQuestion(texto);
            setSendError(err.message);
        } finally {
            setSending(false);
        }
    }

    function handleKeyDown(event) {
        // Enter envia; Shift+Enter quebra linha
        if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            send(question);
        }
    }

    if (loading) {
        return (
            <Container size="xl" py="xl">
                <Group justify="center"><Loader size="md" /></Group>
            </Container>
        );
    }

    if (loadError) {
        return (
            <Container size="xl" py="xl">
                <Alert color="red" icon={<IconAlertCircle size={16} />} title="Erro ao carregar">
                    {loadError}
                </Alert>
            </Container>
        );
    }

    const cor = chat.materia_cor || DEFAULT_SUBJECT_COLOR;

    return (
        <Container size="md" px={{ base: 0, sm: 'md' }} py={{ base: 0, sm: 'md' }}>
            <div className={styles.chatPage}>
                <header className={styles.chatHeader}>
                    <ActionIcon component={Link} to="/chats" variant="subtle" color="dark" size="lg" radius="xl" aria-label="Voltar para os chats">
                        <IconArrowLeft size={20} />
                    </ActionIcon>
                    <span className={styles.headerBadge} style={{ backgroundColor: cor }}>
                        <IconMessageCircle size={18} color="white" />
                    </span>
                    <div className={styles.headerText}>
                        <Text className={styles.headerTitle} title={chat.titulo}>{chat.titulo}</Text>
                        <Text className={styles.headerSubject}>{chat.materia_nome || 'Matéria'}</Text>
                    </div>
                </header>

                <div ref={listRef} className={styles.messages} aria-live="polite">
                    <div className={styles.messagesInner}>
                        {mensagens.length === 0 && !sending && (
                            <div className={styles.welcome}>
                                <span className={styles.welcomeBadge} style={{ backgroundColor: cor }}>
                                    <IconMessageCircle size={26} color="white" />
                                </span>
                                <Text className={styles.welcomeTitle}>Pergunte sobre {chat.materia_nome || 'esta matéria'}</Text>
                                <Text className={styles.welcomeText}>
                                    As respostas vêm dos PDFs desta matéria e citam os trechos usados.
                                </Text>
                                <div className={styles.suggestions}>
                                    {SUGESTOES.map((s) => (
                                        <Button key={s} variant="default" radius="xl" size="xs" className={styles.suggestion} onClick={() => send(s)}>
                                            {s}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        )}
                        {mensagens.map((m) => (
                            <ChatMessage key={m.id} papel={m.papel} msg={m.msg} sources={m.sources} />
                        ))}
                        {sending && (
                            <div className={styles.rowAssistant}>
                                <span className={styles.avatar} aria-hidden="true"><Loader size={14} color="white" /></span>
                                <div className={styles.bubbleAssistant}>
                                    <Text size="sm" c="dimmed">Procurando no material…</Text>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className={styles.composerWrap}>
                    {sendError && (
                        <Alert color="red" icon={<IconAlertCircle size={16} />} withCloseButton onClose={() => setSendError(null)} mb="xs" py={6}>
                            {sendError}
                        </Alert>
                    )}
                    <div className={styles.composer}>
                        <Textarea
                            value={question}
                            onChange={(e) => setQuestion(e.currentTarget.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Pergunte algo sobre o material…"
                            aria-label="Sua pergunta"
                            variant="unstyled"
                            autosize
                            minRows={1}
                            maxRows={5}
                            maxLength={MAX_PERGUNTA}
                            disabled={sending}
                            className={styles.composerInput}
                        />
                        <ActionIcon
                            size={38}
                            radius="xl"
                            className={styles.sendButton}
                            onClick={() => send(question)}
                            disabled={!question.trim() || sending}
                            aria-label="Enviar pergunta"
                        >
                            <IconArrowUp size={20} />
                        </ActionIcon>
                    </div>
                    <Text className={styles.composerHint} visibleFrom="sm">
                        Enter envia · Shift+Enter quebra linha
                    </Text>
                </div>
            </div>
        </Container>
    );
}
