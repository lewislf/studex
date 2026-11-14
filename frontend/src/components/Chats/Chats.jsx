import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useOutletContext } from 'react-router';
import {
    Container, Stack, Flex, Title, Text, Button, Loader, Alert, Group, ActionIcon,
} from '@mantine/core';
import { IconPlus, IconTrash, IconAlertCircle, IconMessageCircle, IconChevronRight } from '@tabler/icons-react';
import SubjectPickerModal from '../Common/SubjectPickerModal';
import { formatDate } from '../SubjectDetail/api.js';
import { fetchChats, createChat, deleteChat } from './api.js';
import { DEFAULT_SUBJECT_COLOR } from '../../config/Constants';
import subjectStyles from '../../styles/Subjects/Subjects.module.css';
import styles from '../../styles/Chats/Chats.module.css';

/**
 * Aba "Chats": lista as conversas do usuário (cada uma ligada a uma matéria)
 * e cria uma nova a partir da escolha de uma matéria.
 */
export default function Chats() {
    const user = useOutletContext();
    const userId = user?.id;
    const navigate = useNavigate();

    const [chats, setChats] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [pickerOpened, setPickerOpened] = useState(false);

    const load = useCallback(async () => {
        if (!userId) return;
        setLoading(true);
        setError(null);
        try {
            setChats(await fetchChats(userId));
        } catch {
            setError('Não foi possível carregar seus chats.');
        } finally {
            setLoading(false);
        }
    }, [userId]);

    useEffect(() => { load(); }, [load]);

    async function handleCreate(subjectId) {
        setPickerOpened(false);
        try {
            const chat = await createChat(userId, Number(subjectId));
            navigate(`/chats/${chat.id}`);
        } catch (err) {
            setError(err.message);
        }
    }

    async function handleDelete(chatId) {
        if (!window.confirm('Apagar este chat e todas as mensagens dele?')) return;
        try {
            await deleteChat(userId, chatId);
            setChats((prev) => prev.filter((c) => c.id !== chatId));
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <Container size="xl" className={subjectStyles.container}>
            <Stack gap="sm">
                <Flex
                    justify="space-between"
                    align={{ base: 'flex-start', sm: 'center' }}
                    direction={{ base: 'column', sm: 'row' }}
                    gap="md"
                    className={subjectStyles.titleSection}
                >
                    <Stack gap={4}>
                        <Title className={subjectStyles.pageTitle} order={1}>Seus Chats</Title>
                        <Text className={subjectStyles.pageSubtitle}>
                            Tire dúvidas sobre o material de uma matéria. As respostas citam os trechos dos seus PDFs.
                        </Text>
                    </Stack>
                    <Button
                        leftSection={<IconPlus size={16} />}
                        className={subjectStyles.addButton}
                        onClick={() => setPickerOpened(true)}
                    >
                        Novo chat
                    </Button>
                </Flex>

                {error && (
                    <Alert color="red" icon={<IconAlertCircle size={16} />} withCloseButton onClose={() => setError(null)}>
                        {error}
                    </Alert>
                )}

                {loading ? (
                    <Group justify="center" py="xl"><Loader size="md" /></Group>
                ) : chats.length === 0 ? (
                    <Stack align="center" gap="xs" className={styles.empty}>
                        <IconMessageCircle size={40} stroke={1.5} />
                        <Text fw={600}>Nenhum chat ainda</Text>
                        <Text size="sm" c="dimmed" ta="center">
                            Crie um chat, escolha a matéria e pergunte sobre o conteúdo dela.
                        </Text>
                    </Stack>
                ) : (
                    <Stack gap="sm">
                        {chats.map((chat) => (
                            <div key={chat.id} className={styles.chatCard}>
                                <Link to={`/chats/${chat.id}`} className={styles.chatLink}>
                                    <span
                                        className={styles.headerBadge}
                                        style={{ backgroundColor: chat.materia_cor || DEFAULT_SUBJECT_COLOR }}
                                    >
                                        <IconMessageCircle size={18} color="white" />
                                    </span>
                                    <span className={styles.chatText}>
                                        <Text className={styles.chatTitle}>{chat.titulo}</Text>
                                        <Text className={styles.chatMeta}>
                                            {chat.materia_nome} · {formatDate(chat.creation_date)}
                                        </Text>
                                    </span>
                                    <IconChevronRight size={18} className={styles.chatChevron} />
                                </Link>
                                <ActionIcon
                                    variant="subtle"
                                    color="gray"
                                    size="lg"
                                    className={styles.chatDelete}
                                    aria-label={`Apagar o chat ${chat.titulo}`}
                                    onClick={() => handleDelete(chat.id)}
                                >
                                    <IconTrash size={18} />
                                </ActionIcon>
                            </div>
                        ))}
                    </Stack>
                )}
            </Stack>

            <SubjectPickerModal
                opened={pickerOpened}
                onClose={() => setPickerOpened(false)}
                userId={userId}
                onConfirm={handleCreate}
                onlyExisting
                confirmLabel="Criar chat"
            />
        </Container>
    );
}
