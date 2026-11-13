import { render, screen } from './render';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router';
import MobileNav from '../components/Common/MobileNav';
import { isActiveLink } from '../utils/navHelpers';

describe('MobileNav', () => {
    it('mostra as cinco seções', () => {
        render(
            <MemoryRouter initialEntries={['/']}>
                <MobileNav />
            </MemoryRouter>
        );
        for (const label of ['Home', 'Revisões', 'Matérias', 'Chats', 'Estatísticas']) {
            expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
        }
    });

    it('marca a seção ativa também em sub-rotas', () => {
        render(
            <MemoryRouter initialEntries={['/materias/3/resumos/7']}>
                <MobileNav />
            </MemoryRouter>
        );
        const materias = screen.getByRole('link', { name: 'Matérias' });
        expect(materias).toHaveAttribute('data-active', 'true');
        expect(materias).toHaveAttribute('aria-current', 'page');
        expect(screen.getByRole('link', { name: 'Home' })).not.toHaveAttribute('data-active');
    });
});

describe('isActiveLink', () => {
    it('trata a raiz e as sub-rotas', () => {
        expect(isActiveLink('/', '/')).toBe(true);
        expect(isActiveLink('/materias', '/')).toBe(false);
        expect(isActiveLink('/materias/3', '/materias')).toBe(true);
        expect(isActiveLink('/revisoes/estudar', '/revisoes')).toBe(true);
        expect(isActiveLink('/materiasx', '/materias')).toBe(false);
    });
});
