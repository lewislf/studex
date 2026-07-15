import { Box, Stack, Text } from "@mantine/core";
import SubjectIcon from "../Common/SubjectIcon";
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsDeckCardInfo displays the subject icon, title name, and course details.
 *
 * @param {Object} props
 * @param {string} props.icon - Name of the custom icon.
 * @param {string} props.color - Hex theme color code.
 * @param {string} props.subjectName - Title of the course/subject.
 * @param {string} [props.subtitle] - Supporting description subtext.
 */
export default function RevisionsDeckCardInfo({ icon, color, subjectName, subtitle }) {
    return (
        <Box className={styles.deckInfo}>
            <Box
                className={styles.iconBox}
                style={{ backgroundColor: `${color}15`, color: color }}
            >
                <SubjectIcon name={icon} size={22} color={color} />
            </Box>
            <Stack gap={2}>
                <Text className={styles.deckTitle}>{subjectName}</Text>
                <Text className={styles.deckSubtitle}>{subtitle?.toLowerCase()}</Text>
            </Stack>
        </Box>
    );
}
