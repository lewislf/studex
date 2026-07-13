import { Box, Text } from '@mantine/core';
import { Link } from 'react-router';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * MaterialCard renders a single study-material entry (summary, mind map or
 * deck) inside a section grid, visually matching the subject cards from the
 * "Suas Matérias" screen: a white card with a colored stripe, a type icon,
 * a type-specific preview body and a footer with the date and "abrir >".
 *
 * @param {Object} props
 * @param {string} props.to - Route to navigate to when the card is opened.
 * @param {string} props.title - Item title.
 * @param {string} props.date - Pre-formatted creation date text.
 * @param {string} props.color - Subject color used for the stripe accent and the "abrir" link.
 * @param {React.ReactNode} props.icon - Type icon shown at the top of the card.
 * @param {React.ReactNode} props.children - Type-specific preview content.
 * @param {boolean} [props.disabled] - Shows the preview but blocks navigation
 * into the item (used while its reader/viewer page isn't ready yet).
 */
export default function MaterialCard({ to, title, date, color, icon, children, disabled = false }) {
    const content = (
        <>
            <Box className={styles.materialCardStripe} style={{ backgroundColor: color }} />
            <Box className={styles.materialCardContent}>
                <Box className={styles.materialCardIcon}>{icon}</Box>
                <Text className={styles.materialCardTitle}>{title}</Text>

                <Box className={styles.materialCardBody}>{children}</Box>

                <Box className={styles.materialCardFooter}>
                    <Text className={styles.materialCardDate}>{date}</Text>
                    {disabled ? (
                        <Text className={styles.materialCardOpen} c="dimmed">em breve</Text>
                    ) : (
                        <Text className={styles.materialCardOpen} style={{ color }}>abrir &gt;</Text>
                    )}
                </Box>
            </Box>
        </>
    );

    if (disabled) {
        return <Box className={`${styles.materialCard} ${styles.materialCardDisabled}`}>{content}</Box>;
    }

    return (
        <Box component={Link} to={to} className={styles.materialCard}>
            {content}
        </Box>
    );
}
