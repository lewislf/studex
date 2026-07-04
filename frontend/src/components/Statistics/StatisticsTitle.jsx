import { Stack, Title, Text } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';

/**
 * Component for rendering the header section of the statistics module.
 * Provides a clean title and description banner.
 */
export default function StatisticsTitle() {
    return (
        <Stack className={styles.titleSection} gap={4}>
            {/* Main module page title */}
            <Title className={styles.pageTitle} order={1}>
                Suas Estatísticas
            </Title>
            {/* Supporting subtitle */}
            <Text className={styles.pageSubtitle}>
                Monitore a sua evolução
            </Text>
        </Stack>
    );
}
