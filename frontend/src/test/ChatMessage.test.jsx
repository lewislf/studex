import { render, screen, userEvent } from './render';
import { describe, it, expect } from 'vitest';
import ChatMessage from '../components/Chats/ChatMessage';

const sources = [
    { n: 1, file_name: 'grafos.pdf', excerpt: 'Uma k-coloração atribui' },
    { n: 2, file_name: 'grafos.pdf', excerpt: 'O número cromático' },
];

describe('ChatMessage', () => {
    it('mostra a resposta e abre as fontes ao tocar', async () => {
        render(<ChatMessage papel="assistant" msg="É uma coloração com k cores [1]." sources={sources} />);

        expect(screen.getByText('É uma coloração com k cores [1].')).toBeInTheDocument();
        const toggle = screen.getByRole('button', { name: /2 fontes/ });
        expect(screen.queryByText('[1] grafos.pdf')).not.toBeInTheDocument();

        await userEvent.click(toggle);
        expect(screen.getByText('[1] grafos.pdf')).toBeInTheDocument();
        expect(toggle).toHaveAttribute('aria-expanded', 'true');
    });

    it('pergunta do usuário não tem fontes', () => {
        render(<ChatMessage papel="user" msg="O que é k-coloração?" />);
        expect(screen.getByText('O que é k-coloração?')).toBeInTheDocument();
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });
});
