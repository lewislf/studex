import { useEffect, useRef, useState } from 'react';
import { useParams, useOutletContext } from 'react-router';
import { Container, Box, Loader, Alert, Group, Textarea, ActionIcon, Text } from '@mantine/core';
import { IconAlertCircle, IconSend } from '@tabler/icons-react';
import SubjectBreadcrumb from '../SubjectDetail/SubjectBreadcrumb.jsx';
import ChatMessage from './ChatMessage.jsx';
import { fetchChat, sendMessage } from './api.js';
import styles from '../../styles/Chats/Chats.module.css';

const MAX_PERGUNTA = 1000;

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
    const endRef = useRef(null);

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
        endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }, [mensagens, sending]);

    async function handleSend() {
        const texto = question.trim();
        if (!texto || sending) return;

        setSendError(null);
        setSending(true);
        setQuestion('');
        setMensagens((prev) => [...prev, { id: `tmp-${Date.now()}`, papel: 'user', msg: texto }]);

        try {
            const { answer, sources } = await sendMessage(userId, chatId, texto);
            setMensagens((prev) => [...prev, { id: `tmp-${Date.now()}-a`, papel: 'assistant', msg: answer, sources }]);
            if (chat?.titulo === 'Novo chat') setChat((c) => ({ ...c, titulo: texto.slice(0, 50) }));
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
            handleSend();
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

    return (
        <Container size="xl" py={{ base: 0, sm: 'md' }} px={{ base: 0, sm: 'md' }}>
            <Box className={styles.chatPage}>
                <SubjectBreadcrumb items={[{ label: 'Seus Chats', to: '/chats' }, { label: chat.titulo }]} />
                <Text className={styles.chatSubject}>{chat.materia_nome || 'Matéria'}</Text>

                <div className={styles.messages} aria-live="polite">
                    {mensagens.length === 0 && !sending && (
                        <Text c="dimmed" ta="center" className={styles.hint}>
                            Pergunte algo sobre o material desta matéria. Ex.: &quot;Explique o conceito principal do capítulo 2&quot;.
                        </Text>
                    )}
                    {mensagens.map((m) => (
                        <ChatMessage key={m.id} papel={m.papel} msg={m.msg} sources={m.sources} />
                    ))}
                    {sending && (
                        <div className={styles.rowAssistant}>
                            <div className={styles.bubbleAssistant}>
                                <Group gap="xs"><Loader size="xs" type="dots" /><Text size="sm" c="dimmed">Procurando no material…</Text></Group>
                            </div>
                        </div>
                    )}
                    <div ref={endRef} />
                </div>

                {sendError && (
                    <Alert color="red" icon={<IconAlertCircle size={16} />} withCloseButton onClose={() => setSendError(null)} mb="xs">
                        {sendError}
                    </Alert>
                )}

                <div className={styles.composer}>
                    <Textarea
                        value={question}
                        onChange={(e) => setQuestion(e.currentTarget.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Escreva sua pergunta…"
                        aria-label="Sua pergunta"
                        autosize
                        minRows={1}
                        maxRows={5}
                        maxLength={MAX_PERGUNTA}
                        disabled={sending}
                        className={styles.composerInput}
                    />
                    <ActionIcon
                        size={42}
                        radius="xl"
                        className={styles.sendButton}
                        onClick={handleSend}
                        disabled={!question.trim() || sending}
                        aria-label="Enviar pergunta"
                    >
                        <IconSend size={18} />
                    </ActionIcon>
                </div>
            </Box>
        </Container>
    );
}
