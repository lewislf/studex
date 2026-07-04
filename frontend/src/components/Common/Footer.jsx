import { IconBrandInstagram, IconBrandLinkedin, IconBrandYoutube } from '@tabler/icons-react';
import { ActionIcon, Container, Group, Title } from '@mantine/core';
import { Link, useLocation } from 'react-router';
import classes from '../../styles/Mantine/Footer.module.css';

// Routing configuration
const LINKS = [
    { link: '/', label: 'Home' },
    { link: '/revisoes', label: 'Revisões' },
    { link: '/materias', label: 'Matérias' },
    { link: '/estatisticas', label: 'Estatísticas' },
];

/**
 * Global application footer
 */
export default function Footer() {
    const location = useLocation();

    // Map internal application navigation items using
    const items = LINKS.map((link) => (
        <Link
            key={link.label}
            to={link.link}
            className={classes.linkText}
            data-active={location.pathname === link.link || undefined}
        >
            {link.label}
        </Link>
    ));

    return (
        <div className={classes.footer}>
            <Container size="xl" className={classes.inner}>
                {/* Links setup */}
                <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <Title order={3} className={classes.title}>Studex</Title>
                </Link>

                {/* Link group */}
                <Group className={classes.links}>{items}</Group>

                {/* Social setup */}
                <Group gap="xs" justify="flex-end" wrap="nowrap">
                    <ActionIcon size="lg" variant="default" radius="xl" aria-label="LinkedIn">
                        <IconBrandLinkedin size={18} stroke={1.5} />
                    </ActionIcon>
                    <ActionIcon size="lg" variant="default" radius="xl" aria-label="YouTube">
                        <IconBrandYoutube size={18} stroke={1.5} />
                    </ActionIcon>
                    <ActionIcon size="lg" variant="default" radius="xl" aria-label="Instagram">
                        <IconBrandInstagram size={18} stroke={1.5} />
                    </ActionIcon>
                </Group>
            </Container>
        </div>
    );
}
