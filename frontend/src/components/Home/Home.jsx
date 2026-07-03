import { Container, Stack } from "@mantine/core";
import HomeTitle from "./HomeTitle";
import { parseUserProfile } from '../../utils/userHelpers.js'
import mock from '../../config/userProfileMock.json'
import styles from '../../styles/Home/Home.module.css'

export default function Home() {
    const user = parseUserProfile(mock);

    return (
        <Container size="xl" className={styles.container}>
            <Stack>
                <HomeTitle name={user.name} totalFlashcards={user.gamification.streak}/>
            </Stack>
        </Container>
    )
}

