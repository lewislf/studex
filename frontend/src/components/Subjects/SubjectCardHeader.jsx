import { Text, Stack } from "@mantine/core";
import SubjectIcon from '../Common/SubjectIcon';
import styles from '../../styles/Subjects/Subjects.module.css';

/**
 * SubjectCardHeader renders the icon, title, and total topics of the subject.
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
