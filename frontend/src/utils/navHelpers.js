/**
 * Marca o link como ativo também nas sub-rotas (ex.: /materias/3 ativa "Matérias").
 * A raiz "/" só fica ativa na própria Home.
 */
export function isActiveLink(pathname, link) {
    if (link === '/') return pathname === '/';
    return pathname === link || pathname.startsWith(`${link}/`);
}
