import { useEffect, useState } from 'react';
import { Text } from '@mantine/core';
import MaterialSection from './MaterialSection.jsx';
import MaterialIcon from './MaterialIcon.jsx';
import { materialTypeColor } from './materialColors.js';
import { fetchSummaries, formatDate, stripMaterialSuffix, parseConteudo } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * SummariesSection fetches and lists the summaries generated for a subject.
 *
 * @param {Object} props
 * @param {string|number} props.userId
 * @param {string|number} props.subjectId
 */
export default function SummariesSection({ userId, subjectId }) {
    const color = materialTypeColor('resumo');
    const [summaries, setSummaries] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!userId || !subjectId) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const data = await fetchSummaries(userId, subjectId);
                if (!cancelled) setSummaries(data);
            } catch {
                if (!cancelled) setError('Não foi possível carregar os resumos.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [userId, subjectId]);

    const items = summaries.map((summary) => {
        const conteudo = parseConteudo(summary.conteudo);
        return {
            id: summary.id,
            to: `/materias/${subjectId}/resumos/${summary.id}`,
            title: stripMaterialSuffix(summary.titulo),
            date: formatDate(summary.creation_date),
            texto: conteudo?.texto || '',
            topicosChave: Array.isArray(conteudo?.topicos_chave) ? conteudo.topicos_chave : [],
        };
    });

    function renderPreview(item) {
        return (
            <>
                {item.texto && (
                    <Text className={styles.materialCardPreview}>{item.texto}</Text>
                )}
                <Text className={styles.materialCardMeta}>
                    {item.topicosChave.length} tópicos-chave
                </Text>
            </>
        );
    }

    return (
        <MaterialSection
            title="Resumos"
            icon={<MaterialIcon type="resumo" />}
            items={items}
            loading={loading}
            error={error}
            emptyText="Nenhum resumo ainda."
            color={color}
            renderPreview={renderPreview}
        />
    );
}
