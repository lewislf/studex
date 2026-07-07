import { Title, Text, Stack } from "@mantine/core";
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsTitle renders the greeting banner, page title, and algorithmic description subtext.
 */
export default function RevisionsTitle() {
    return (
        <Stack className={styles.pageHeader} gap="xs">
            <Title order={1} className={styles.pageTitle}>
                Revisões de Hoje
            </Title>
            <Text className={styles.pageSubtitle}>
                O sistema de repetição espaçada (FSRS) seleciona os cards no ponto ótimo para fixação. Quanto mais consistente, menos cards por dia.
            </Text>
        </Stack>
    );
}
