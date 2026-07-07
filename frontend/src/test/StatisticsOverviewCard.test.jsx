import { render, screen } from './render';
import { describe, it, expect } from 'vitest';
import StatisticsOverviewCard from '../components/Statistics/StatisticsOverviewCard';

describe('StatisticsOverviewCard Component', () => {
    const mockStats = {
        statsDistribution: [
            { label: 'Cálculo', percentage: 60, color: 'blue' },
            { label: 'Física', percentage: 40, color: 'red' }
        ]
    };

    it('renders Rank E for low study scores and formats count < 1000 correctly', () => {
        const mockUser = {
            gamification: { streak: 2 },
            counters: {
                mapsCount: 1,
                summariesCount: 1,
                totalFlashcardsCreated: 10,
                pendingFlashcardsToday: 5
            }
        };

        render(
            <StatisticsOverviewCard user={mockUser} stats={mockStats} />
        );

        // Grade E: score = (10 * 2) + (2 * 25) + (1 * 10) + (1 * 10) = 90
        expect(screen.getByText('E')).toBeInTheDocument();
        expect(screen.getByText('2 dias')).toBeInTheDocument();
        expect(screen.getByText('10')).toBeInTheDocument();
    });

    it('renders Rank C for medium-low study scores', () => {
        const mockUser = {
            gamification: { streak: 40 },
            counters: {
                mapsCount: 2,
                summariesCount: 2,
                totalFlashcardsCreated: 200,
                pendingFlashcardsToday: 5
            }
        };

        render(
            <StatisticsOverviewCard user={mockUser} stats={mockStats} />
        );

        // Grade C: score = (200 * 2) + (40 * 25) + (2 * 10) + (2 * 10) = 400 + 1000 + 20 + 20 = 1440
        expect(screen.getByText('C')).toBeInTheDocument();
        expect(screen.getByText('40 dias')).toBeInTheDocument();
        expect(screen.getByText('200')).toBeInTheDocument();
    });

    it('renders Rank A for medium-high study scores and formats count >= 1000 correctly', () => {
        const mockUser = {
            gamification: { streak: 40 },
            counters: {
                mapsCount: 20,
                summariesCount: 20,
                totalFlashcardsCreated: 1500,
                pendingFlashcardsToday: 15
            }
        };

        render(
            <StatisticsOverviewCard user={mockUser} stats={mockStats} />
        );

        // Grade A: score = (1500 * 2) + (40 * 25) + (20 * 10) + (20 * 10) = 3000 + 1000 + 200 + 200 = 4400
        expect(screen.getByText('A')).toBeInTheDocument();
        expect(screen.getByText('40 dias')).toBeInTheDocument();
        expect(screen.getByText('1.5k')).toBeInTheDocument(); // >= 1000, formatted with 'k'
    });

    it('renders Rank S for very high study scores', () => {
        const mockUser = {
            gamification: { streak: 120 },
            counters: {
                mapsCount: 80,
                summariesCount: 80,
                totalFlashcardsCreated: 2000,
                pendingFlashcardsToday: 0
            }
        };

        render(
            <StatisticsOverviewCard user={mockUser} stats={mockStats} />
        );

        // Grade S: score = (2000 * 2) + (120 * 25) + (80 * 10) + (80 * 10) = 4000 + 3000 + 800 + 800 = 8600 >= 5000
        expect(screen.getByText('S')).toBeInTheDocument();
        expect(screen.getByText('120 dias')).toBeInTheDocument();
    });

    it('renders the subject distribution legend correctly', () => {
        const mockUser = {
            gamification: { streak: 5 },
            counters: {
                mapsCount: 2,
                summariesCount: 2,
                totalFlashcardsCreated: 20,
                pendingFlashcardsToday: 3
            }
        };

        render(
            <StatisticsOverviewCard user={mockUser} stats={mockStats} />
        );

        expect(screen.getByText('Cálculo: 60%')).toBeInTheDocument();
        expect(screen.getByText('Física: 40%')).toBeInTheDocument();
    });
});
