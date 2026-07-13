import { useEffect, useMemo, useState } from 'react';
import { useParams, useOutletContext } from 'react-router';
import { Container, Box, Loader, Alert, Group } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import SubjectBreadcrumb from './SubjectBreadcrumb.jsx';
import MindMapCanvas from './MindMapCanvas.jsx';
import { layoutMindMap } from './MindMapLayout.js';
import { fetchSubject, fetchMindMaps, dedupeMindMapTitle } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

const HIERARCHY_EDGE_STYLE = { stroke: 'var(--mantine-color-gray-4)', strokeWidth: 1.5 };

/** `conteudo` may come back from the API as a JSON string or already parsed. */
function parseConteudo(conteudo) {
    if (typeof conteudo === 'string') {
        try {
            return JSON.parse(conteudo);
        } catch {
            return { nodes: [], edges: [] };
        }
    }
    return conteudo || { nodes: [], edges: [] };
}

/** Hierarchical edges render as a plain solid line; "relacao" edges keep their custom (dashed) type. */
function buildEdges(rawEdges) {
    return (rawEdges || []).map((edge) =>
        edge.type === 'relacao' ? edge : { ...edge, type: 'straight', style: HIERARCHY_EDGE_STYLE }
    );
}

/**
 * Mind map viewer page ("Suas Matérias > {matéria} > {mapa}"): fetches the
 * subject (for the breadcrumb) and the single mind map, then renders it
 * with the existing MindMapCanvas.
 */
export default function MindMapPage() {
    const { subjectId, mapaId } = useParams();
    const { refreshUser: _r, ...user } = useOutletContext();

    const [subject, setSubject] = useState(null);
    const [mindMap, setMindMap] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!user.id || !subjectId || mapaId === undefined) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const [subjectData, mapsData] = await Promise.all([
                    fetchSubject(user.id, subjectId),
                    fetchMindMaps(user.id, subjectId),
                ]);
                if (cancelled) return;
                const mapData = mapsData.find((m) => String(m.id) === String(mapaId));
                if (!subjectData || !mapData) {
                    setError('Mapa mental não encontrado.');
                    return;
                }
                setSubject(subjectData);
                setMindMap(mapData);
            } catch {
                if (!cancelled) setError('Não foi possível carregar o mapa mental.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [user.id, subjectId, mapaId]);

    const { nodes, edges } = useMemo(() => {
        if (!mindMap) return { nodes: [], edges: [] };
        const conteudo = parseConteudo(mindMap.conteudo);
        return {
            nodes: layoutMindMap(conteudo.nodes, conteudo.edges),
            edges: buildEdges(conteudo.edges),
        };
    }, [mindMap]);

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
                <SubjectBreadcrumb
                    items={[
                        { label: 'Suas Matérias', to: '/materias' },
                        { label: subject.title || subject.name, to: `/materias/${subjectId}` },
                        { label: dedupeMindMapTitle(mindMap.titulo) },
                    ]}
                />
                <MindMapCanvas nodes={nodes} edges={edges} />
            </Box>
        </Container>
    );
}
