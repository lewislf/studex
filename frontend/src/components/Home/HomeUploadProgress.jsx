import { useEffect, useState } from 'react';
import { Stack, Text, Progress, Group, ThemeIcon, Loader } from '@mantine/core';
import { IconSparkles } from '@tabler/icons-react';

import { UPLOAD_PHASES } from '../../config/Constants';

/**
 * Dashboard pane rendered in place of the dropzone while the backend processes the PDF.
 *
 * The backend responds only at the end (a single request) and gives no per-phase
 * signal, so we do NOT claim any phase as concluded. The bar animates just to show
 * activity, and the copy makes clear the generation runs on the LLM and can take a
 * few minutes. Previous versions marked phases as done on a timer, which stalled on
 * the last phase and read as a hang (issue #45).
 *
 * @param {string} [fileName] - Name of the file being processed.
 */
export default function HomeUploadProgress({ fileName }) {
    const [value, setValue] = useState(6);

    useEffect(() => {
        const id = setInterval(() => {
            // So um indicador de atividade: sobe em direcao a 95% e desacelera,
            // sem nunca afirmar que uma fase terminou.
            setValue((v) => (v >= 95 ? 95 : v + Math.max(1, (95 - v) * 0.06)));
        }, 600);
        return () => clearInterval(id);
    }, []);

    return (
        <Stack gap="md" py="lg" px="md">
            <Group justify="center" gap="xs" wrap="nowrap">
                <Loader size="sm" color="blue" />
                <Text ta="center" fw={600} fz="sm">
                    Processando {fileName ? `"${fileName}"` : 'seu PDF'}...
                </Text>
            </Group>

            <Text ta="center" fz="xs" c="dimmed" maw={340} mx="auto">
                A geração usa IA e pode levar alguns minutos. Pode deixar essa aba
                aberta que os materiais aparecem na matéria assim que ficarem prontos.
            </Text>

            <Stack gap="xs" maw={320} mx="auto" w="100%">
                {UPLOAD_PHASES.map((label) => (
                    <Group key={label} gap="xs" wrap="nowrap">
                        <ThemeIcon size="sm" radius="xl" variant="light" color="blue">
                            <IconSparkles size={12} />
                        </ThemeIcon>
                        <Text fz="sm" c="dimmed">
                            {label}
                        </Text>
                    </Group>
                ))}
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
