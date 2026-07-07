import { SimpleGrid, Stack, Title } from '@mantine/core';
import HomeCreationCard from './HomeCreationCard';
import { CREATION_OPTIONS } from '../../config/Constants';

/**
 * Renders a grid section presenting options to generate study resources from raw data.
 */
export default function HomeCreationGrid() {
    const cards = CREATION_OPTIONS.map((item) => <HomeCreationCard {...item} key={item.title} />);

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
