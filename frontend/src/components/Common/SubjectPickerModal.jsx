import { useEffect, useState } from 'react';
import {
    Modal, SegmentedControl, Select, TextInput, Textarea,
    Button, Stack, Group, Text, Loader, Alert, ActionIcon
} from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import { useSubjects } from '../../hooks/useSubjects';
import SubjectIcon from './SubjectIcon';
import styles from '../../styles/Common/SubjectPickerModal.module.css';

import { COLOR_OPTIONS, ICON_OPTIONS, DEFAULT_SUBJECT_ICON, DEFAULT_SUBJECT_COLOR } from '../../config/Constants';

/**
 * Modal menu shown during file upload.
 *
 * @param {Object} props
 * @param {boolean} props.opened - Whether the modal is open.
 * @param {Function} props.onClose - Action to close the modal (cancelling the upload).
 * @param {string|number} props.userId - Current user identifier.
 * @param {string} [props.fileName] - Name of the file being uploaded (shown in the title).
 * @param {Function} props.onConfirm - Callback invoked with the chosen or created subject_id to trigger the upload.
 * @param {boolean} [props.onlyCreate] - If true, locks SegmentedControl and displays only the creation form.
 */
export default function SubjectPickerModal({ opened, onClose, userId, fileName, onConfirm, onlyCreate = false }) {
    const { subjects, loading, error, fetchSubjects, createSubject } = useSubjects(userId);

    const [mode, setMode] = useState(onlyCreate ? 'nova' : 'existente');       // 'existente' | 'nova'
    const [selectedId, setSelectedId] = useState(null);  // chosen existing subject
    const [newName, setNewName] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [selectedIcon, setSelectedIcon] = useState(DEFAULT_SUBJECT_ICON);
    const [selectedColor, setSelectedColor] = useState(DEFAULT_SUBJECT_COLOR);
    const [submitting, setSubmitting] = useState(false);

    // Fetch subjects every time the modal is opened
    useEffect(() => {
        if (opened) {
            fetchSubjects();
            setMode(onlyCreate ? 'nova' : 'existente');
            setSelectedId(null);
            setNewName('');
            setNewDesc('');
            setSelectedIcon(DEFAULT_SUBJECT_ICON);
            setSelectedColor(DEFAULT_SUBJECT_COLOR);
        }
    }, [opened, fetchSubjects, onlyCreate]);

    const hasSubjects = subjects.length > 0;


    async function handleConfirm() {
        setSubmitting(true);
        try {
            let subjectId = selectedId;

            if (mode === 'nova') {
                subjectId = await createSubject({
                    name: newName.trim(),
                    description: newDesc.trim(),
                    icon: selectedIcon,
                    color: selectedColor
                });
                if (subjectId === null) return; // error already notified by the hook

                // Store selected icon and color in localStorage
                const customVisuals = JSON.parse(localStorage.getItem('subject_visuals') || '{}');
                customVisuals[String(subjectId)] = {
                    icon: selectedIcon,
                    color: selectedColor
                };
                localStorage.setItem('subject_visuals', JSON.stringify(customVisuals));
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
            title={onlyCreate ? 'Adicionar nova Matéria' : (fileName ? `Salvar "${fileName}" em uma matéria` : 'Escolher matéria')}
            centered
        >
            <Stack>
                {!onlyCreate && (
                    <SegmentedControl
                        value={mode}
                        onChange={setMode}
                        data={[
                            { label: 'Matéria existente', value: 'existente' },
                            { label: 'Nova matéria', value: 'nova' },
                        ]}
                        fullWidth
                    />
                )}

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

                        {/* Custom Dynamic Icon Picker */}
                        <Stack gap="xs" mt="xs">
                            <Text size="sm" fw={600} c="dark.4">Ícone da Matéria</Text>
                            <Group gap="xs">
                                {ICON_OPTIONS.map(opt => {
                                    const active = selectedIcon === opt.name;
                                    return (
                                        <ActionIcon
                                            key={opt.name}
                                            variant={active ? "filled" : "default"}
                                            color={active ? selectedColor : "gray"}
                                            onClick={() => setSelectedIcon(opt.name)}
                                            className={styles.iconButton}
                                            aria-label={opt.label}
                                        >
                                            <SubjectIcon name={opt.name} size={20} />
                                        </ActionIcon>
                                    );
                                })}
                            </Group>
                        </Stack>

                        {/* Custom Dynamic Color Picker */}
                        <Stack gap="xs" mt="xs">
                            <Text size="sm" fw={600} c="dark.4">Cor Temática</Text>
                            <Group gap="xs">
                                {COLOR_OPTIONS.map(color => {
                                    const active = selectedColor === color;
                                    return (
                                        <div
                                            key={color}
                                            className={`${styles.colorCircle} ${active ? styles.activeColorCircle : ''}`}
                                            style={{ backgroundColor: color }}
                                            onClick={() => setSelectedColor(color)}
                                        />
                                    );
                                })}
                            </Group>
                        </Stack>
                    </Stack>
                )}

                <Group justify="flex-end" mt="sm">
                    <Button variant="default" onClick={onClose} disabled={submitting}>
                        Cancelar
                    </Button>
                    <Button onClick={handleConfirm} loading={submitting} disabled={confirmDisabled}>
                        {onlyCreate ? 'Adicionar' : 'Enviar e salvar'}
                    </Button>
                </Group>
            </Stack>
        </Modal>
    );
}
