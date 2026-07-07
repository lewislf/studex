import { render, screen } from './render';
import { describe, it, expect } from 'vitest';
import HomeCard from '../components/Home/HomeCard';

describe('HomeCard Component', () => {
    it('renders the title and body text', () => {
        render(
            <HomeCard title="Estudos de Hoje" text="Você completou todos os cartões do dia!" />
        );

        expect(screen.getByText('Estudos de Hoje')).toBeInTheDocument();
        expect(screen.getByText('Você completou todos os cartões do dia!')).toBeInTheDocument();
    });

    it('renders the custom icon when provided and passes correct props', () => {
        const IconMock = (props) => (
            <svg data-testid="custom-icon" {...props}>
                <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
            </svg>
        );

        render(
            <HomeCard 
                title="Estudos" 
                text="Teste" 
                Icon={IconMock} 
                iconColor="red" 
            />
        );

        const icon = screen.getByTestId('custom-icon');
        expect(icon).toBeInTheDocument();
        expect(icon).toHaveAttribute('color', 'red');
        expect(icon).toHaveAttribute('size', '40');
    });

    it('does not render icon when Icon is not provided', () => {
        render(
            <HomeCard title="Estudos" text="Teste" />
        );

        expect(screen.queryByTestId('custom-icon')).not.toBeInTheDocument();
    });
});
