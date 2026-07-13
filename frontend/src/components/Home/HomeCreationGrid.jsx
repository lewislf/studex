import { SimpleGrid, Stack, Title, Text } from '@mantine/core';
import HomeCreationCard from './HomeCreationCard';
import { CREATION_OPTIONS } from '../../config/Constants';

/**
 * Renders a grid section letting the user pick which study resources will
 * be generated from the next uploaded material.
 * @param {Set<string>} selected - Values (see CREATION_OPTIONS) currently selected.
 * @param {(value: string) => void} onToggle - Flips selection for a given value.
 */
export default function HomeCreationGrid({ selected, onToggle }) {
    const cards = CREATION_OPTIONS.map((item) => (
        <HomeCreationCard
            {...item}
            key={item.title}
            selected={selected?.has(item.value) ?? true}
            onToggle={() => onToggle?.(item.value)}
        />
    ));

    return (
        <Stack gap="md" mt="xl">
            <Stack gap={2}>
                <Title order={2} size="h3" fw={700}>
                    Criar a partir de um material
                </Title>
                <Text size="sm" c="dimmed">
                    Escolha o que gerar ao enviar um arquivo
                </Text>
            </Stack>

            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
                {cards}
            </SimpleGrid>
        </Stack>
    );
}
