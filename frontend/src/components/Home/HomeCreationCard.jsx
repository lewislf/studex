import { Text, ThemeIcon, Card } from '@mantine/core';
import classes from '../../styles/Mantine/CreationCard.module.css';
import SubjectIcon from '../Common/SubjectIcon';

/**
 * A specialty card variant optimized for grid item selection layouts.
 */
export default function HomeCreationCard({ icon, title, description, color }) {
    return (
        <Card shadow="sm" padding="xl" radius="md" withBorder className={classes.card}>
            <ThemeIcon variant="light" size={50} radius="md" color={color}>
                <SubjectIcon name={icon} size={26} stroke={1.5} />
            </ThemeIcon>
            <Text mt="md" fw={700} size="lg">
                {title}
            </Text>
            <Text size="sm" c="dimmed" mt="xs">
                {description}
            </Text>
        </Card>
    );
}
