import { useEffect, useState } from 'react';
import { Stack, Text, Progress, Group, ThemeIcon, Loader } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';

// As 3 etapas do pipeline de geração (resumo → mapa mental → flashcards).
const PHASES = ['Criando resumo', 'Criando mapa mental', 'Criando flashcards'];

/**
 * Painel exibido no lugar do dropzone enquanto o backend processa o PDF.
 *
 * O backend responde só ao final (uma requisição única), então o avanço das
 * fases é uma animação no frontend — a barra sobe devagar e desacelera perto
 * do fim, sem chegar a 100% até o upload realmente terminar.
 *
 * @param {string} [fileName] - Nome do arquivo em processamento.
 */
export default function UploadProgress({ fileName }) {
    const [value, setValue] = useState(6);

    useEffect(() => {
        const id = setInterval(() => {
            // Cresce em direção a 95% e desacelera (efeito "quase lá")
            setValue((v) => (v >= 95 ? 95 : v + Math.max(1, (95 - v) * 0.06)));
        }, 600);
        return () => clearInterval(id);
    }, []);

    // Fase atual derivada do progresso
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
