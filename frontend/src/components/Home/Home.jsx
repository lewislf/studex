import { Container, Stack } from "@mantine/core";
import HomeTitle from "./HomeTitle";
import { useUser } from '../../hooks/useUser.js'
import mock from '../../config/userMock.json'
import styles from '../../styles/Home/Home.module.css'

export default function Home() {
    const user = useUser(mock);

    return (
        <Container size="xl" className={styles.container}>
            <Stack>
                <HomeTitle name={user.name} totalFlashcards={user.metrics.queueCount}/>
            </Stack>
        </Container>
    )
}

