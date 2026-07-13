import { useEffect, useState } from 'react';
import { useParams, useOutletContext } from 'react-router';
import { Container, Box, Loader, Alert, Group } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import SubjectBreadcrumb from './SubjectBreadcrumb.jsx';
import SummariesSection from './SummariesSection.jsx';
import MindMapsSection from './MindMapsSection.jsx';
import FlashcardsSection from './FlashcardsSection.jsx';
import { fetchSubject } from './api.js';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * Subject detail page ("fichário"): breadcrumb back to "Suas Matérias" plus
 * three stacked sections (Resumos, Mapas Mentais, Flashcards), each a grid
 * of material cards that open the corresponding reader/viewer page.
 */
export default function SubjectDetail() {
    const { subjectId } = useParams();
    const { refreshUser: _r, ...user } = useOutletContext();

    const [subject, setSubject] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!user.id || !subjectId) return;

        let cancelled = false;

        async function load() {
            setLoading(true);
            setError(null);
            try {
                const data = await fetchSubject(user.id, subjectId);
                if (cancelled) return;
                if (!data) {
                    setError('Matéria não encontrada.');
                    return;
                }
                setSubject(data);
            } catch {
                if (!cancelled) setError('Não foi possível carregar a matéria.');
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        load();
        return () => { cancelled = true; };
    }, [user.id, subjectId]);

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

    const subjectTitle = subject.title || subject.name;

    return (
        <Container size="xl" py="md">
            {/* Single white card wrapping breadcrumb + all sections, matching Subjects.jsx's container look. */}
            <Box className={styles.page}>
                <SubjectBreadcrumb
                    items={[
                        { label: 'Suas Matérias', to: '/materias' },
                        { label: subjectTitle },
                    ]}
                />

                <SummariesSection userId={user.id} subjectId={subjectId} />
                <MindMapsSection userId={user.id} subjectId={subjectId} />
                <FlashcardsSection userId={user.id} subjectId={subjectId} />
            </Box>
        </Container>
    );
}
