import { Title, Text, Stack, Group, Button } from "@mantine/core";
import { IconPlayerPlay } from "@tabler/icons-react";
import { Link } from "react-router";
import styles from '../../styles/Revisions/Revisions.module.css';

/**
 * RevisionsTitle renders the greeting banner, page title, algorithmic
 * description subtext, and the entry point into the global study queue.
 *
 * @param {Object} props
 * @param {number} [props.totalPending] - Total cards pending across all decks.
 */
export default function RevisionsTitle({ totalPending = 0 }) {
    return (
        <Group justify="space-between" align="flex-start" wrap="wrap" gap="md">
            <Stack className={styles.pageHeader} gap="xs">
                <Title order={1} className={styles.pageTitle}>
                    Revisões de Hoje
                </Title>
                <Text className={styles.pageSubtitle}>
                    O sistema de repetição espaçada (FSRS) seleciona os cards no ponto ótimo para fixação. Quanto mais consistente, menos cards por dia.
                </Text>
            </Stack>
            <Button
                component={Link}
                to="/revisoes/estudar"
                color="orange"
                leftSection={<IconPlayerPlay size={16} />}
                disabled={totalPending <= 0}
            >
                Revisar tudo
            </Button>
        </Group>
    );
}
