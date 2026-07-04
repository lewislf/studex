import { Space, Stack, Text, Title } from "@mantine/core";
import styles from '../../styles/Home/Home.module.css'

/**
 * Standard welcoming layout block.
 */
export default function HomeTitle({name, totalFlashcards}) {
    return (
        <Stack className={styles.title}>
            <Title order={1}>Olá, {name}!</Title>
            <Space w="md"/>
            <Text size="md">Você tem {totalFlashcards} flashcards para revisar hoje!</Text>
        </Stack>
    )
}

