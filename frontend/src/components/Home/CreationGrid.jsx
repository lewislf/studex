import { IconFileText, IconSitemap, IconCards } from '@tabler/icons-react';
import { SimpleGrid, Stack, Title } from '@mantine/core';
import HomeCreationCard from './HomeCreationCard';

// Core layout configuration data for the content creation options
const DATA = [
    {
        icon: IconFileText,
        title: 'Resumo',
        description: 'Estruturado, com tópicos e marcadores',
        color: 'blue',
    },
    {
        icon: IconSitemap,
        title: 'Mapa Mental',
        description: 'Navegável, com visão',
        color: 'grape',
    },
    {
        icon: IconCards,
        title: 'Flashcards',
        description: 'Revisão espaçada',
        color: 'orange',
    },
];

/**
 * Renders a grid section presenting options to generate study resources from raw data.
 */
export default function HomeCreationGrid() {
    const cards = DATA.map((item) => <HomeCreationCard {...item} key={item.title} />);

    return (
        <Stack gap="md" mt="xl">
            <Title order={2} size="h3" fw={700}>
                Criar a partir de um material
            </Title>

            <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
                {cards}
            </SimpleGrid>
        </Stack>
    );
}
