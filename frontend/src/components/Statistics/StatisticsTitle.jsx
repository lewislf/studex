import { Stack, Title, Text } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';

export default function StatisticsTitle() {
    return (
        <Stack className={styles.titleSection} gap={4}>
            <Title className={styles.pageTitle} order={1}>
                Suas Estatísticas
            </Title>
            <Text className={styles.pageSubtitle}>
                Monitore a sua evolução
            </Text>
        </Stack>
    );
}
