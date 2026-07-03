import { Container, Group, Title } from '@mantine/core';
import { Link, useLocation } from 'react-router';
import classes from '../../styles/Mantine/Header.module.css';

const links = [
    { link: '/', label: 'Home' },
    { link: '/revisoes', label: 'Revisões' },
    { link: '/materias', label: 'Matérias' },
    { link: '/estatisticas', label: 'Estatísticas' },
];

export default function Header() {
    const location = useLocation();

    const items = links.map((link) => (
        <Link
            key={link.label}
            to={link.link}
            className={classes.link}
            data-active={location.pathname === link.link || undefined}
        >
            {link.label}
        </Link>
    ));

    return (
        <header className={classes.header}>
            <Container size="xl" className={classes.inner}>
                <Title order={3} c="black" className={classes.title}>Studex</Title>
                <Group gap={3} visibleFrom="xs" className={classes.subjects}>
                    {items}
                </Group>
            </Container>
        </header>
    );
}
