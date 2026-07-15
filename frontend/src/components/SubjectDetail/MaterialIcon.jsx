import { IconFileText, IconSitemap, IconCards } from '@tabler/icons-react';
import styles from '../../styles/SubjectDetail/Materials.module.css';

// Each material type keeps its own identity color (not the subject color),
// so resumos/mapas/flashcards read the same way across every subject.
const TYPE_CONFIG = {
    resumo: { Icon: IconFileText, bg: 'var(--mantine-color-blue-1)', color: 'var(--mantine-color-blue-6)' },
    mapa: { Icon: IconSitemap, bg: 'var(--mantine-color-violet-1)', color: 'var(--mantine-color-violet-6)' },
    flashcards: { Icon: IconCards, bg: 'var(--mantine-color-orange-1)', color: 'var(--mantine-color-orange-6)' },
};

/**
 * MaterialIcon renders a type icon inside a colored rounded-square badge
 * (used both in section headers and material cards).
 *
 * @param {Object} props
 * @param {'resumo'|'mapa'|'flashcards'} props.type
 * @param {number} [props.iconSize=18]
 */
export default function MaterialIcon({ type, iconSize = 18 }) {
    const config = TYPE_CONFIG[type];
    if (!config) return null;

    const { Icon, bg, color } = config;
    return (
        <span className={styles.materialIconBadge} style={{ backgroundColor: bg }}>
            <Icon size={iconSize} color={color} />
        </span>
    );
}
