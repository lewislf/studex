import { Stack, Text, Group, ThemeIcon, Loader } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';

// Same colors as MaterialIcon.jsx (resumo/mapa/flashcards sections), so this
// reads as the same visual language as where the materials show up once ready.
const PHASES = [
    { key: 'resumo', label: 'Criando resumo', color: 'blue' },
    { key: 'mapa_mental', label: 'Criando mapa mental', color: 'violet' },
    { key: 'flashcards', label: 'Criando flashcards', color: 'orange' },
];

// Etapa final: os materiais já foram gravados e os contadores atualizados.
const SAVE_PHASE = { key: 'salvo', label: 'Salvando na matéria', color: 'green' };

/**
 * Dashboard pane rendered in place of the dropzone while the backend processes the PDF.
 *
 * `progress` is polled from GET /users/{id}/documents/progress (see
 * HomePdfDropzone.jsx) every couple seconds while this is mounted, and
 * reflects REAL backend state: each item only gets a checkmark once that
 * material has actually finished generating (materials.py's on_phase_done
 * callback), never a timed simulation. Still-pending items show a spinning
 * loader (not a static icon) so the screen doesn't look inert while waiting,
 * without ever claiming a phase is done before it really is.
 *
 * @param {string} [fileName] - Name of the file being processed.
 * @param {{resumo?: boolean, mapa_mental?: boolean, flashcards?: boolean}} [progress]
 * @param {Set<string>} [phases] - Which material types were actually requested for this
 *   upload (see HomeCreationGrid). When omitted, all phases are shown (matches the
 *   backend default of generating everything when `materials` is not sent).
 */
export default function HomeUploadProgress({ fileName, progress, phases }) {
    const visiblePhases = [
        ...(phases ? PHASES.filter(({ key }) => phases.has(key)) : PHASES),
        SAVE_PHASE,
    ];

    return (
        <Stack gap="md" py="lg" px="md">
            <Text ta="center" fw={600} fz="sm">
                Processando {fileName ? `"${fileName}"` : 'seu PDF'}...
            </Text>

            <Text ta="center" fz="xs" c="dimmed" maw={340} mx="auto">
                A geração usa IA e pode levar alguns minutos. Pode deixar essa aba
                aberta que os materiais aparecem na matéria assim que ficarem prontos.
            </Text>

            <Stack gap="xs" maw={320} mx="auto" w="100%">
                {visiblePhases.map(({ key, label, color }) => {
                    const done = Boolean(progress?.[key]);
                    return (
                        <Group key={key} gap="xs" wrap="nowrap">
                            {done ? (
                                <ThemeIcon size="sm" radius="xl" variant="filled" color={color}>
                                    <IconCheck size={12} />
                                </ThemeIcon>
                            ) : (
                                <Loader size="sm" color={color} />
                            )}
                            <Text fz="sm" c={done ? color : 'dimmed'} fw={done ? 600 : 400}>
                                {label}
                            </Text>
                        </Group>
                    );
                })}
            </Stack>
        </Stack>
    );
}
