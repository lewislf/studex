import { render, screen } from './render';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router';
import Header from '../components/Common/Header';

describe('Header Component', () => {
    it('renders the header title and user information', () => {
        render(
            <MemoryRouter initialEntries={['/']}>
                <Header name="João Silva" avatarUrl="https://example.com/avatar.png" />
            </MemoryRouter>
        );

        // Check if application title is rendered
        expect(screen.getByText('Studex')).toBeInTheDocument();

        // Check if user's name is rendered
        expect(screen.getByText('João Silva')).toBeInTheDocument();

        // Check if avatar image is rendered with correct attributes
        const avatar = screen.getByRole('img');
        expect(avatar).toHaveAttribute('src', 'https://example.com/avatar.png');
        expect(avatar).toHaveAttribute('alt', 'João Silva');
    });

    it('renders navigation links and flags the active link', () => {
        render(
            <MemoryRouter initialEntries={['/revisoes']}>
                <Header name="João Silva" />
            </MemoryRouter>
        );

        // Check if links are rendered
        const homeLink = screen.getByRole('link', { name: 'Home' });
        const revisionsLink = screen.getByRole('link', { name: 'Revisões' });
        const subjectsLink = screen.getByRole('link', { name: 'Matérias' });
        const statsLink = screen.getByRole('link', { name: 'Estatísticas' });

        expect(homeLink).toBeInTheDocument();
        expect(revisionsLink).toBeInTheDocument();
        expect(subjectsLink).toBeInTheDocument();
        expect(statsLink).toBeInTheDocument();

        // Check active route link flags
        expect(revisionsLink).toHaveAttribute('data-active', 'true');
        expect(homeLink).not.toHaveAttribute('data-active');
    });
});
