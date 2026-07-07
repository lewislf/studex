import { Text, Stack } from "@mantine/core";
import SubjectIcon from '../Common/SubjectIcon';
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardHeader renders the icon, title, and total topics of the subject.
 *
 * @param {Object} props
 * @param {string} props.icon - Icon key identifier.
 * @param {string} props.color - Theme color string.
 * @param {string} props.title - Title text of the subject.
 * @param {number} props.totalTopics - Number of study topics.
 */
export default function SubjectCardHeader({ icon, color, title, totalTopics }) {
    return (
        <Stack gap="xs" className={styles.cardHeader}>
            <SubjectIcon name={icon} size={36} color={color} />
            <Text className={styles.cardTitle}>{title}</Text>
            <Text className={styles.cardSubtext}>
                {totalTopics} tópicos
            </Text>
        </Stack>
    );
}
