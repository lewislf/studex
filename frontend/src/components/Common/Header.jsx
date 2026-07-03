import { Container, Group, Title, Avatar } from '@mantine/core';
import { Link, useLocation } from 'react-router';
import classes from '../../styles/Mantine/Header.module.css';

const links = [
    { link: '/', label: 'Home' },
    { link: '/revisoes', label: 'Revisões' },
    { link: '/materias', label: 'Matérias' },
    { link: '/estatisticas', label: 'Estatísticas' },
];
export default function Header({name, avatarUrl}) { const location = useLocation();

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

                <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <Title order={3} className={classes.title}>Studex</Title>
                </Link>
                <Group gap={3} visibleFrom="xs" className={classes.subjects}>
                    {items}
                </Group>
                <Group>
                    <Title order={4} className={classes.profile}>{name}</Title>
                    <Avatar src={avatarUrl} alt={name} radius="xl" size="md" />
                </Group>
            </Container>
        </header>
    );
}
