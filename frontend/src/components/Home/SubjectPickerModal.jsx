import { useEffect, useState } from 'react';
import {
    Modal, SegmentedControl, Select, TextInput, Textarea,
    Button, Stack, Group, Text, Loader, Alert,
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useSubjects } from '../../hooks/useSubjects';

/**
 * Modal menu shown during file upload: the user chooses to save the generated artifacts
 * (summary, mind map, flashcards) into an existing subject or create a new one.
 *
 * @param {boolean} opened - Whether the modal is open.
 * @param {Function} onClose - Action to close the modal (cancelling the upload).
 * @param {string|number} userId - Current user identifier.
 * @param {string} [fileName] - Name of the file being uploaded (shown in the title).
 * @param {Function} onConfirm - Callback invoked with the chosen or created subject_id to trigger the upload.
 */
export default function SubjectPickerModal({ opened, onClose, userId, fileName, onConfirm }) {
    const { subjects, loading, error, fetchSubjects, createSubject } = useSubjects(userId);

    const [mode, setMode] = useState('existente');       // 'existente' | 'nova'
    const [selectedId, setSelectedId] = useState(null);  // chosen existing subject
    const [newName, setNewName] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [submitting, setSubmitting] = useState(false);

    // Fetch subjects every time the modal is opened
    useEffect(() => {
        if (opened) {
            fetchSubjects();
            setMode('existente');
            setSelectedId(null);
            setNewName('');
            setNewDesc('');
        }
    }, [opened, fetchSubjects]);

    const hasSubjects = subjects.length > 0;

    async function handleConfirm() {
        setSubmitting(true);
        try {
            let subjectId = selectedId;

            if (mode === 'nova') {
                subjectId = await createSubject({ name: newName.trim(), description: newDesc.trim() });
                if (subjectId === null) return; // error already notified by the hook
            }

            if (subjectId === null || subjectId === undefined) return;

            onConfirm(subjectId);
        } finally {
            setSubmitting(false);
        }
    }

    const confirmDisabled =
        submitting ||
        (mode === 'existente' && !selectedId) ||
        (mode === 'nova' && newName.trim() === '');

    return (
        <Modal
            opened={opened}
            onClose={onClose}
            title={fileName ? `Salvar "${fileName}" em uma matéria` : 'Escolher matéria'}
            centered
        >
            <Stack>
                <SegmentedControl
                    value={mode}
                    onChange={setMode}
                    data={[
                        { label: 'Matéria existente', value: 'existente' },
                        { label: 'Nova matéria', value: 'nova' },
                    ]}
                    fullWidth
                />

                {error && (
                    <Alert color="red" icon={<IconAlertCircle size={16} />}>
                        {error}
                    </Alert>
                )}

                {mode === 'existente' && (
                    loading ? (
                        <Group justify="center" py="md"><Loader size="sm" /></Group>
                    ) : hasSubjects ? (
                        <Select
                            label="Escolha a matéria"
                            placeholder="Selecione..."
                            data={subjects.map((s) => ({ value: String(s.id), label: s.title }))}
                            value={selectedId}
                            onChange={setSelectedId}
                            searchable
                        />
                    ) : (
                        <Text c="dimmed" size="sm">
                            Você ainda não tem matérias. Crie uma nova para continuar.
                        </Text>
                    )
                )}

                {mode === 'nova' && (
                    <Stack gap="xs">
                        <TextInput
                            label="Nome da matéria"
                            placeholder="Ex: Redes de Computadores"
                            value={newName}
                            onChange={(e) => setNewName(e.currentTarget.value)}
                            required
                        />
                        <Textarea
                            label="Descrição"
                            placeholder="Breve descrição (opcional)"
                            value={newDesc}
                            onChange={(e) => setNewDesc(e.currentTarget.value)}
                            autosize
                            minRows={2}
                        />
                    </Stack>
                )}

                <Group justify="flex-end" mt="sm">
                    <Button variant="default" onClick={onClose} disabled={submitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirm} loading={submitting} disabled={confirmDisabled}>
                        Enviar e salvar
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
