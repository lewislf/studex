import { Text, ThemeIcon, Card } from '@mantine/core';
import { IconCheck } from '@tabler/icons-react';
import classes from '../../styles/Mantine/CreationCard.module.css';
import SubjectIcon from '../Common/SubjectIcon';

/**
 * A specialty card variant optimized for grid item selection layouts.
 * Acts as a toggleable selector: `selected` controls the visual emphasis
 * (highlighted border + check badge vs. dimmed/desaturated), `onToggle`
 * flips the selection on click or keyboard activation.
 */
export default function HomeCreationCard({ icon, title, description, color, selected = true, onToggle }) {
    function handleKeyDown(event) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            onToggle?.();
        }
    }

    return (
        <Card
            shadow="sm"
            padding="xl"
            radius="md"
            withBorder
            className={`${classes.card} ${selected ? classes.cardSelected : classes.cardUnselected}`}
            role="checkbox"
            aria-checked={selected}
            tabIndex={0}
            onClick={onToggle}
            onKeyDown={handleKeyDown}
            style={{ '--creation-card-color': `var(--mantine-color-${color}-6)` }}
        >
            {selected && (
                <ThemeIcon
                    className={classes.checkBadge}
                    size={22}
                    radius="xl"
                    variant="filled"
                    color={color}
                >
                    <IconCheck size={14} stroke={3} />
                </ThemeIcon>
            )}

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
