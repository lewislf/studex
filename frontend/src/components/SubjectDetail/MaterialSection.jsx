import { SimpleGrid, Stack, Title, Text, Loader, Alert, Group, Badge } from '@mantine/core';
import { IconAlertCircle } from '@tabler/icons-react';
import MaterialCard from './MaterialCard.jsx';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * MaterialSection renders one stacked section of the subject page (Resumos,
 * Mapas Mentais or Flashcards): an icon + title + count badge heading, a grid
 * of material cards, and the loading/error/empty states for that section's
 * own fetch.
 *
 * @param {Object} props
 * @param {string} props.title - Section heading.
 * @param {React.ReactNode} props.icon - Icon shown next to the section heading.
 * @param {Array<{id: string|number, to: string, title: string, date: string}>} props.items
 * @param {boolean} props.loading
 * @param {string|null} props.error
 * @param {string} props.emptyText - Message shown when there are no items yet.
 * @param {string} props.color - Subject color passed through to each card's stripe.
 * @param {(item: Object) => React.ReactNode} props.renderPreview - Builds the type-specific card body for an item.
 * @param {boolean} [props.disabled] - Shows previews but blocks navigation into every item in this section.
 */
export default function MaterialSection({ title, icon, items, loading, error, emptyText, color, renderPreview, disabled = false }) {
    return (
        <Stack gap="md" className={styles.section}>
            <Group gap="xs" align="center">
                {icon}
                <Title order={3} className={styles.sectionTitle}>{title}</Title>
                {!loading && !error && (
                    <Badge variant="light" color="gray" circle>{items.length}</Badge>
                )}
            </Group>

            {loading && (
                <Group py="md" justify="center">
                    <Loader size="sm" />
                </Group>
            )}

            {!loading && error && (
                <Alert color="red" icon={<IconAlertCircle size={16} />}>{error}</Alert>
            )}

            {!loading && !error && items.length === 0 && (
                <Text c="dimmed" size="sm" className={styles.emptyText}>{emptyText}</Text>
            )}

            {!loading && !error && items.length > 0 && (
                <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
                    {items.map((item) => (
                        <MaterialCard key={item.id} to={item.to} title={item.title} date={item.date} color={color} icon={icon} disabled={disabled}>
                            {renderPreview(item)}
                        </MaterialCard>
                    ))}
                </SimpleGrid>
            )}
        </Stack>
    );
}
