import { useState } from 'react';
import { Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconChevronUp } from '@tabler/icons-react';
import styles from '../../styles/Chats/Chats.module.css';

/**
 * Um balão da conversa. Respostas do assistente mostram as fontes (trechos
 * dos PDFs) num bloco que abre ao tocar, para funcionar também no celular.
 *
 * @param {Object} props
 * @param {'user'|'assistant'} props.papel
 * @param {string} props.msg
 * @param {Array<{n:number, file_name:string, excerpt:string}>} [props.sources]
 */
export default function ChatMessage({ papel, msg, sources = [] }) {
    const [showSources, setShowSources] = useState(false);
    const isUser = papel === 'user';

    return (
        <div className={isUser ? styles.rowUser : styles.rowAssistant}>
            <div className={isUser ? styles.bubbleUser : styles.bubbleAssistant}>
                {/* shortcut: texto puro com quebras de linha; renderizar markdown se o Gemini passar a usar muita formatação */}
                <Text className={styles.bubbleText}>{msg}</Text>

                {!isUser && sources.length > 0 && (
                    <>
                        <UnstyledButton
                            className={styles.sourcesToggle}
                            onClick={() => setShowSources((v) => !v)}
                            aria-expanded={showSources}
                        >
                            {showSources ? <IconChevronUp size={14} /> : <IconChevronDown size={14} />}
                            {sources.length === 1 ? '1 fonte' : `${sources.length} fontes`}
                        </UnstyledButton>
                        {showSources && (
                            <ol className={styles.sourcesList}>
                                {sources.map((s) => (
                                    <li key={s.n}>
                                        <span className={styles.sourceName}>[{s.n}] {s.file_name || 'documento'}</span>
                                        {s.excerpt && <span className={styles.sourceExcerpt}>{s.excerpt}…</span>}
                                    </li>
                                ))}
                            </ol>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
