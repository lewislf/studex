import { Button, Container, Group, Text, Title } from '@mantine/core';
import { useNavigate } from 'react-router';
import classes from '../../styles/Mantine/ErrorPage.module.css';

/**
 * Standard HTTP 404 Error View Component.
 * Intercepts broken routes or invalid application states and provides navigation safety paths.
 */
export default function ErrorPage() {
    const navigate = useNavigate();

    return (
        <Container className={classes.root}>
            <div className={classes.inner}>
                <div className={classes.image}>404</div>
                <div className={classes.content}>
                    <Title className={classes.title}>Nada para ver aqui</Title>
                    <Text c="dimmed" size="lg" ta="center" className={classes.description}>
                        A página que você está tentando abrir não existe. Você pode ter digitado o
                        endereço incorretamente ou a página foi movida para outra URL.
                    </Text>
                    <Group justify="center">
                        <Button size="md" onClick={() => navigate('/')}>
                            Voltar para a página inicial
                        </Button>
                    </Group>
                </div>
            </div>
        </Container>
    );
}
