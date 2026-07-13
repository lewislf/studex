import { useEffect, useState } from 'react';
import { Text } from '@mantine/core';
import MaterialSection from './MaterialSection.jsx';
import MaterialIcon from './MaterialIcon.jsx';
import { materialTypeColor } from './materialColors.js';
import { fetchMindMaps, formatDate, dedupeMindMapTitle, parseConteudo } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/** Node types that count as an actual concept, as opposed to the root/theme node. */
const CONCEPT_NODE_TYPES = new Set(['detalhe', 'categoria']);

/**
 * MindMapsSection fetches and lists the mind maps generated for a subject.
 *
 * @param {Object} props
 * @param {string|number} props.userId
 * @param {string|number} props.subjectId
 */
export default function MindMapsSection({ userId, subjectId }) {
    const color = materialTypeColor('mapa');
    const [mindMaps, setMindMaps] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!userId || !subjectId) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const data = await fetchMindMaps(userId, subjectId);
                if (!cancelled) setMindMaps(data);
            } catch {
                if (!cancelled) setError('Não foi possível carregar os mapas mentais.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [userId, subjectId]);

    const items = mindMaps.map((mindMap) => {
        const conteudo = parseConteudo(mindMap.conteudo);
        const nodes = Array.isArray(conteudo?.nodes) ? conteudo.nodes : [];
        const edges = Array.isArray(conteudo?.edges) ? conteudo.edges : [];
        const concepts = nodes.filter((node) => CONCEPT_NODE_TYPES.has(node.type)).length;

        return {
            id: mindMap.id,
            to: `/materias/${subjectId}/mapas/${mindMap.id}`,
            title: dedupeMindMapTitle(mindMap.titulo),
            date: formatDate(mindMap.creation_date),
            concepts,
            connections: edges.length,
        };
    });

    function renderPreview(item) {
        return (
            <Text className={styles.materialCardMeta}>
                {item.concepts} conceitos &middot; {item.connections} conexões
            </Text>
        );
    }

    return (
        <MaterialSection
            title="Mapas Mentais"
            icon={<MaterialIcon type="mapa" />}
            items={items}
            loading={loading}
            error={error}
            emptyText="Nenhum mapa mental ainda."
            color={color}
            renderPreview={renderPreview}
        />
    );
}
