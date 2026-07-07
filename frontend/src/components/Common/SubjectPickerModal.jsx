import { useEffect, useState } from 'react';
import {
    Modal, SegmentedControl, Select, TextInput, Textarea,
    Button, Stack, Group, Text, Loader, Alert, ActionIcon
} from '@mantine/core';
import {
    IconAlertCircle,
    IconGlobe,
    IconRocket,
    IconSchool,
    IconUsers,
    IconDatabase,
    IconBook,
    IconCalculator,
    IconFlask,
    IconCode,
    IconLanguage,
    IconBrain,
    IconPalette,
    IconHistory,
    IconMicroscope,
    IconHeart,
    IconScale
} from '@tabler/icons-react';
import { useSubjects } from '../../hooks/useSubjects';
import styles from '../../styles/Common/SubjectPickerModal.module.css';

const ICON_OPTIONS = [
    { name: 'book', label: 'Livro' },
    { name: 'globe', label: 'Redes/Globo' },
    { name: 'rocket', label: 'Foguete' },
    { name: 'user-teacher', label: 'Professor' },
    { name: 'users', label: 'Pessoas' },
    { name: 'database', label: 'Banco de Dados' },
    { name: 'calculator', label: 'Cálculo/Matemática' },
    { name: 'flask', label: 'Química/Ciência' },
    { name: 'code', label: 'Código/Programação' },
    { name: 'language', label: 'Idiomas' },
    { name: 'brain', label: 'Mente/Psicologia' },
    { name: 'palette', label: 'Artes/Design' },
    { name: 'history', label: 'História' },
    { name: 'microscope', label: 'Biologia/Ciências' },
    { name: 'heart', label: 'Saúde' },
    { name: 'scale', label: 'Direito/Justiça' },
];

const COLOR_OPTIONS = [
    '#e63946', // Red
    '#ffb703', // Yellow
    '#fb8500', // Orange
    '#4caf50', // Leaf Green
    '#4361ee', // Blue
    '#2ec4b6', // Green
    '#4cc9f0', // Sky Blue
    '#7209b7', // Deep Purple
    '#9b5de5', // Purple
    '#ff70a6', // Soft Pink
    '#f72585', // Hot Pink
];

/**
 * Modal menu shown during file upload: the user chooses to save the generated artifacts
 * (summary, mind map, flashcards) into an existing subject or create a new one.
 * Supports dynamic icon and color selections when creating a new subject.
 *
 * @param {boolean} opened - Whether the modal is open.
 * @param {Function} onClose - Action to close the modal (cancelling the upload).
 * @param {string|number} userId - Current user identifier.
 * @param {string} [fileName] - Name of the file being uploaded (shown in the title).
 * @param {Function} onConfirm - Callback invoked with the chosen or created subject_id to trigger the upload.
 * @param {boolean} [onlyCreate] - If true, locks SegmentedControl and displays only the creation form.
 */
export default function SubjectPickerModal({ opened, onClose, userId, fileName, onConfirm, onlyCreate = false }) {
    const { subjects, loading, error, fetchSubjects, createSubject } = useSubjects(userId);

    const [mode, setMode] = useState(onlyCreate ? 'nova' : 'existente');       // 'existente' | 'nova'
    const [selectedId, setSelectedId] = useState(null);  // chosen existing subject
    const [newName, setNewName] = useState('');
    const [newDesc, setNewDesc] = useState('');
    const [selectedIcon, setSelectedIcon] = useState('book');
    const [selectedColor, setSelectedColor] = useState('#4361ee');
    const [submitting, setSubmitting] = useState(false);

    // Fetch subjects every time the modal is opened
    useEffect(() => {
        if (opened) {
            fetchSubjects();
            setMode(onlyCreate ? 'nova' : 'existente');
            setSelectedId(null);
            setNewName('');
            setNewDesc('');
            setSelectedIcon('book');
            setSelectedColor('#4361ee');
        }
    }, [opened, fetchSubjects, onlyCreate]);

    const hasSubjects = subjects.length > 0;

    const getIconElement = (name, size) => {
        switch (name) {
            case 'globe': return <IconGlobe size={size} />;
            case 'rocket': return <IconRocket size={size} />;
            case 'user-teacher': return <IconSchool size={size} />;
            case 'users': return <IconUsers size={size} />;
            case 'database': return <IconDatabase size={size} />;
            case 'calculator': return <IconCalculator size={size} />;
            case 'flask': return <IconFlask size={size} />;
            case 'code': return <IconCode size={size} />;
            case 'language': return <IconLanguage size={size} />;
            case 'brain': return <IconBrain size={size} />;
            case 'palette': return <IconPalette size={size} />;
            case 'history': return <IconHistory size={size} />;
            case 'microscope': return <IconMicroscope size={size} />;
            case 'heart': return <IconHeart size={size} />;
            case 'scale': return <IconScale size={size} />;
            default: return <IconBook size={size} />;
        }
    };

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
                                            {getIconElement(opt.name, 20)}
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
