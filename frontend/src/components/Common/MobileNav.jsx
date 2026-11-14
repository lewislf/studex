import { Link, useLocation } from 'react-router';
import { IconHome, IconCards, IconBooks, IconMessageCircle, IconChartBar } from '@tabler/icons-react';
import classes from '../../styles/Mantine/MobileNav.module.css';
import { LINKS } from '../../config/Constants';
import { isActiveLink } from '../../utils/navHelpers';

const ICONS = {
    '/': IconHome,
    '/revisoes': IconCards,
    '/materias': IconBooks,
    '/chats': IconMessageCircle,
    '/estatisticas': IconChartBar,
};

/**
 * Barra de navegação inferior, usada só no celular (no lugar dos links do
 * cabeçalho e do rodapé).
 */
export default function MobileNav() {
    const { pathname } = useLocation();

    return (
        <nav className={classes.nav} aria-label="Navegação principal">
            {LINKS.map(({ link, label }) => {
                const Icon = ICONS[link] ?? IconHome;
                const active = isActiveLink(pathname, link);
                return (
                    <Link
                        key={link}
                        to={link}
                        className={classes.item}
                        data-active={active || undefined}
                        aria-current={active ? 'page' : undefined}
                    >
                        <Icon size={22} stroke={1.7} />
                        <span className={classes.label}>{label}</span>
                    </Link>
                );
            })}
        </nav>
    );
}
