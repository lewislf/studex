import { useState } from 'react';
import { Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconChevronUp, IconSparkles } from '@tabler/icons-react';
import styles from '../../styles/Chats/Chats.module.css';

/**
 * Formata o texto da resposta: **negrito** e citações [n] viram elementos;
 * o resto fica como texto puro (sem HTML vindo do modelo).
 */
export function renderInline(text) {
    return String(text ?? '')
        .split(/(\*\*[^*\n]+\*\*|\[\d+\])/g)
        .map((part, i) => {
            if (part.length > 4 && part.startsWith('**') && part.endsWith('**')) {
                return <strong key={i}>{part.slice(2, -2)}</strong>;
            }
            if (/^\[\d+\]$/.test(part)) {
                return <span key={i} className={styles.cite}>{part.slice(1, -1)}</span>;
            }
            return part;
        });
}

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

    if (papel === 'user') {
        return (
            <div className={styles.rowUser}>
                <div className={styles.bubbleUser}>
                    <Text className={styles.bubbleText}>{msg}</Text>
                </div>
            </div>
        );
    }

    return (
        <div className={styles.rowAssistant}>
            <span className={styles.avatar} aria-hidden="true"><IconSparkles size={16} /></span>
            <div className={styles.bubbleAssistant}>
                <Text className={styles.bubbleText}>{renderInline(msg)}</Text>

                {sources.length > 0 && (
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
                                        <span className={styles.sourceName}>
                                            <span className={styles.cite}>{s.n}</span>
                                            {s.file_name || 'documento'}
                                        </span>
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
