import { useEffect, useState } from 'react';
import { Stack, Text, Progress, Group, ThemeIcon, Loader } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';

// The 3 phases of the generation pipeline (summary → mind map → flashcards).
const PHASES = ['Criando resumo', 'Criando mapa mental', 'Criando flashcards'];

/**
 * Dashboard pane rendered in place of the dropzone while the backend processes the PDF.
 *
 * The backend responds only at the end (a single request), so the phase advancement
 * is simulated on the client-side: the progress bar grows slowly and decelerates as it
 * approaches the end, never hitting 100% until the upload officially completes.
 *
 * @param {string} [fileName] - Name of the file being processed.
 */
export default function HomeUploadProgress({ fileName }) {
    const [value, setValue] = useState(6);

    useEffect(() => {
        const id = setInterval(() => {
            // Expands towards 95% and decelerates ("almost there" effect)
            setValue((v) => (v >= 95 ? 95 : v + Math.max(1, (95 - v) * 0.06)));
        }, 600);
        return () => clearInterval(id);
    }, []);

    // Current phase derived from progress value
    const phase = value < 38 ? 0 : value < 70 ? 1 : 2;

    return (
        <Stack gap="md" py="lg" px="md">
            <Text ta="center" fw={600} fz="sm">
                Processando {fileName ? `"${fileName}"` : 'seu PDF'}...
            </Text>

            <Stack gap="xs" maw={320} mx="auto" w="100%">
                {PHASES.map((label, i) => {
                    const done = i < phase;
                    const current = i === phase;

                    return (
                        <Group key={label} gap="xs" wrap="nowrap">
                            <ThemeIcon
                                size="sm"
                                radius="xl"
                                variant={done ? 'filled' : current ? 'light' : 'default'}
                                color={done ? 'green' : 'blue'}
                            >
                                {done ? (
                                    <IconCheck size={12} />
                                ) : current ? (
                                    <Loader size={10} color="blue" />
                                ) : null}
                            </ThemeIcon>

                            <Text
                                fz="sm"
                                fw={current ? 600 : 400}
                                c={done ? 'green.7' : current ? undefined : 'dimmed'}
                            >
                                {label}
                                {current ? '…' : ''}
                            </Text>
                        </Group>
                    );
                })}
            </Stack>

            <Progress
                value={value}
                striped
                animated
                radius="xl"
                size="md"
                maw={320}
                mx="auto"
                w="100%"
                transitionDuration={500}
            />
        </Stack>
    );
}
