import { Title } from '@mantine/core';
import { Link } from 'react-router';
import styles from '../../styles/SubjectDetail/Materials.module.css';

/**
 * SubjectBreadcrumb renders the "fichário" trail above every subject-detail
 * page (e.g. "Suas Matérias > Redes > Camadas TCP/IP") as the page's own h1,
 * matching the size/weight of "Suas Matérias" on the subjects list page. All
 * items except the last one are clickable links; the last item is the
 * current page. Plain <Link>/<span> (not Anchor/Text) so nothing overrides
 * the inherited Title font-size/weight.
 *
 * @param {Object} props
 * @param {Array<{label: string, to?: string}>} props.items - Trail entries in order.
 */
export default function SubjectBreadcrumb({ items }) {
    return (
        <Title order={1} className={styles.breadcrumbTitle}>
            {items.map((item, index) => {
                const isLast = index === items.length - 1;
                return (
                    <span
                        key={index}
                        className={isLast ? styles.breadcrumbCurrentWrap : styles.breadcrumbCrumb}
                    >
                        {index > 0 && <span className={styles.breadcrumbSeparator}>&gt;</span>}
                        {item.to && !isLast ? (
                            <Link to={item.to} className={styles.breadcrumbLink}>{item.label}</Link>
                        ) : (
                            <span className={styles.breadcrumbCurrent} title={item.label}>{item.label}</span>
                        )}
                    </span>
                );
            })}
        </Title>
    );
}
