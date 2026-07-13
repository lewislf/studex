import { Space, Stack, Text, Title } from "@mantine/core";
import styles from '../../styles/Home/Home.module.css'

/**
 * Standard welcoming layout block. The subtitle reframes the day's review
 * queue as a call to action instead of a chore ("você tem N para revisar").
 */
export default function HomeTitle({ name, pendingFlashcards }) {
    const subtitle = pendingFlashcards > 0
        ? `${pendingFlashcards} flashcards prontos para revisar. Bora manter o ritmo!`
        : 'Nenhuma revisão pendente por agora. Que tal criar um novo material?';

    return (
        <Stack className={styles.title}>
            <Title order={1}>Olá, {name}!</Title>
            <Space w="md"/>
            <Text size="md">{subtitle}</Text>
        </Stack>
    )
}
