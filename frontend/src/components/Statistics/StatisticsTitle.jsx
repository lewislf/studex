import { Title, Text } from "@mantine/core";
import styles from '../../styles/Statistics/Statistics.module.css';

export default function StatisticsTitle() {
    return (
        <div className={styles.titleSection}>
            <Title className={styles.pageTitle} order={1}>
                Suas Estatísticas
            </Title>
            <Text className={styles.pageSubtitle}>
                Monitore a sua evolução
            </Text>
        </div>
    );
}
