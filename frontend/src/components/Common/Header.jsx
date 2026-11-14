import { Container, Group, Title, Avatar, Menu, UnstyledButton } from '@mantine/core';
import { IconLogout } from '@tabler/icons-react';
import { Link, useLocation } from 'react-router';
import classes from '../../styles/Mantine/Header.module.css';

import { LINKS } from '../../config/Constants';
import { isActiveLink } from '../../utils/navHelpers';

/**
 * Main application header navigation bar.
 * Provides sticky/top accessibility across all view segments and tracks current active location.
 */
export default function Header({name, avatarUrl, onLogout}) { const location = useLocation();

    const items = LINKS.map((link) => (
        <Link
            key={link.label}
            to={link.link}
            className={classes.link}
            data-active={isActiveLink(location.pathname, link.link) || undefined}
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
                <Group gap={3} visibleFrom="sm" className={classes.subjects}>
                    {items}
                </Group>
                <Group>
                    <Title order={4} className={classes.profile} visibleFrom="sm">{name}</Title>
                    <Menu shadow="md" width={160} position="bottom-end">
                        <Menu.Target>
                            <UnstyledButton aria-label="Menu do usuário">
                                <Avatar src={avatarUrl} alt={name} radius="xl" size="md" style={{ cursor: 'pointer' }} />
                            </UnstyledButton>
                        </Menu.Target>
                        <Menu.Dropdown>
                            <Menu.Item
                                color="red"
                                leftSection={<IconLogout size={16} />}
                                onClick={onLogout}
                            >
                                Sair
                            </Menu.Item>
                        </Menu.Dropdown>
                    </Menu>
                </Group>
            </Container>
        </header>
    );
}
