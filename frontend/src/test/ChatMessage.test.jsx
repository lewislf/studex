import { render, screen, userEvent } from './render';
import { describe, it, expect } from 'vitest';
import ChatMessage from '../components/Chats/ChatMessage';
import { prepararMarkdown } from '../components/Chats/prepararMarkdown';

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

    it('renderiza LaTeX com KaTeX em vez de mostrar o código cru', () => {
        const { container } = render(
            <ChatMessage
                papel="assistant"
                msg={'A área é $\\pi r^2$ e\n\n$$\\frac{a}{b} \\geq \\sqrt{x}$$\n\nTambém \\(\\alpha \\in \\mathbb{R}\\) [1].'}
            />
        );
        expect(container.querySelectorAll('.katex').length).toBe(3);
        expect(container.querySelector('.katex-display')).not.toBeNull();
        expect(container.textContent).not.toContain('$');
        expect(container.textContent).not.toContain('\\(');
        expect(container.querySelector('a')).toBeNull();
    });

    it('não transforma R$ em fórmula nem citação dentro de fórmula', () => {
        expect(prepararMarkdown('Custa R$ 10 e R$ 20 [1, 2].')).toBe(
            'Custa R\\$ 10 e R\\$ 20 [1](#cite-1)[2](#cite-2).'
        );
        expect(prepararMarkdown('$v[1]$ e `a[2]`')).toBe('$v[1]$ e `a[2]`');

        const { container } = render(<ChatMessage papel="assistant" msg="Custa R$ 10 e R$ 20." />);
        expect(container.querySelector('.katex')).toBeNull();
        expect(container.textContent).toContain('R$ 10 e R$ 20');
    });

    it('não interpreta HTML vindo do modelo', () => {
        const { container } = render(<ChatMessage papel="assistant" msg={'<img src=x onerror="alert(1)"> oi'} />);
        expect(container.querySelector('img')).toBeNull();
    });

    it('não carrega imagem vinda do modelo e limita o tamanho de \\rule', () => {
        const { container } = render(
            <ChatMessage papel="assistant" msg={'![grafo](https://exemplo.invalid/?q=x) $\\rule{500em}{1em}$'} />
        );
        expect(container.querySelector('img')).toBeNull();
        expect(container.textContent).toContain('grafo');
        expect(container.querySelector('.rule').style.borderRightWidth).toBe('10em');
    });
});
