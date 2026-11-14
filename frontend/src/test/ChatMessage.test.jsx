import { render, screen, userEvent } from './render';
import { describe, it, expect } from 'vitest';
import ChatMessage from '../components/Chats/ChatMessage';

const sources = [
    { n: 1, file_name: 'grafos.pdf', excerpt: 'Uma k-coloração atribui' },
    { n: 2, file_name: 'grafos.pdf', excerpt: 'O número cromático' },
];

describe('ChatMessage', () => {
    it('formata negrito e citações e abre as fontes ao tocar', async () => {
        const { container } = render(
            <ChatMessage papel="assistant" msg="É uma **coloração** com k cores [1]." sources={sources} />
        );

        expect(screen.getByText('coloração').tagName).toBe('STRONG');
        expect(container.textContent).not.toContain('**');
        expect(container.textContent).not.toContain('[1]');

        const toggle = screen.getByRole('button', { name: /2 fontes/ });
        expect(screen.queryByText('Uma k-coloração atribui…')).not.toBeInTheDocument();

        await userEvent.click(toggle);
        expect(screen.getByText('Uma k-coloração atribui…')).toBeInTheDocument();
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
    });

    it('pergunta do usuário fica como texto puro, sem fontes', () => {
        render(<ChatMessage papel="user" msg="O que é **k**-coloração?" />);
        expect(screen.getByText('O que é **k**-coloração?')).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
