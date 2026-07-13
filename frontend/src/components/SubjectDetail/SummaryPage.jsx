import { useEffect, useState } from 'react';
import { useParams, useOutletContext } from 'react-router';
import { Container, Box, Loader, Alert, Group } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import SubjectBreadcrumb from './SubjectBreadcrumb.jsx';
import SummariesReader from './SummariesReader.jsx';
import { fetchSubject, fetchSummary } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * Summary reader page ("Suas Matérias > {matéria} > {resumo}"): fetches the
 * subject (for the breadcrumb) and the single summary, then renders it with
 * the existing SummariesReader.
 */
export default function SummaryPage() {
    const { subjectId, resumoId } = useParams();
    const { refreshUser: _r, ...user } = useOutletContext();

    const [subject, setSubject] = useState(null);
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!user.id || !subjectId || !resumoId) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const [subjectData, summaryData] = await Promise.all([
                    fetchSubject(user.id, subjectId),
                    fetchSummary(user.id, subjectId, resumoId),
                ]);
                if (cancelled) return;
                if (!subjectData || !summaryData) {
                    setError('Resumo não encontrado.');
                    return;
                }
                setSubject(subjectData);
                setSummary(summaryData);
            } catch {
                if (!cancelled) setError('Não foi possível carregar o resumo.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [user.id, subjectId, resumoId]);

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
                        { label: summary.titulo },
                    ]}
                />
                <SummariesReader summary={summary} />
            </Box>
        </Container>
    );
}
