import { describe, it, expect } from 'vitest';
import { parseSubjectsList, parseDailyReviews } from '../utils/userHelpers';

describe('userHelpers', () => {
    describe('parseSubjectsList', () => {
        it('preserves real backend data instead of falling back to mock values', () => {
            const json = [
                {
                    id: 'sub-1',
                    title: 'Cálculo I',
                    icon: 'sigma',
                    color: '#123456',
                    last_activity: '2026-07-01',
                    mastery_percentage: 73,
                    pending_in_queue: 4,
                    counters: { summaries: 2, mind_maps: 1, flashcards: 30 },
                },
            ];

            const result = parseSubjectsList(json);
            expect(result).toEqual([
                {
                    id: 'sub-1',
                    title: 'Cálculo I',
                    icon: 'sigma',
                    color: '#123456',
                    lastActivity: '2026-07-01',
                    masteryPercentage: 73,
                    pendingInQueue: 4,
                    counters: { summaries: 2, mindMaps: 1, flashcards: 30 },
                },
            ]);
        });

        it('accepts a wrapper object with a subjects array', () => {
            const json = { subjects: [{ id: 1, title: 'Física' }] };
            const result = parseSubjectsList(json);
            expect(result).toHaveLength(1);
            expect(result[0].id).toBe(1);
            expect(result[0].title).toBe('Física');
        });

        it('falls back to name when title is missing, and zero-defaults counters', () => {
            const json = [{ id: 2, name: 'Química' }];
            const result = parseSubjectsList(json);
            expect(result[0].title).toBe('Química');
            expect(result[0].masteryPercentage).toBe(0);
            expect(result[0].pendingInQueue).toBe(0);
            expect(result[0].counters).toEqual({ summaries: 0, mindMaps: 0, flashcards: 0 });
        });

        it('falls back to domain when mastery_percentage is not present', () => {
            const json = [{ id: 3, title: 'Bio', domain: 55 }];
            const result = parseSubjectsList(json);
            expect(result[0].masteryPercentage).toBe(55);
        });

        it('returns an empty array for missing/invalid input', () => {
            expect(parseSubjectsList(null)).toEqual([]);
            expect(parseSubjectsList({})).toEqual([]);
        });
    });

    describe('parseDailyReviews', () => {
        it('maps deck id/new/learning/review fields correctly', () => {
            const json = {
                summary: { total_pending: 10, estimated_time_minutes: 15, split: { new: 3, learning: 4, review: 3 } },
                decks_today: [
                    {
                        id: 'deck-1',
                        subject_id: 'sub-1',
                        subject_name: 'Cálculo I',
                        subtitle: 'Derivadas',
                        color: '#ff0000',
                        icon: 'sigma',
                        new: 2,
                        learning: 1,
                        review: 5,
                        total_cards: 8,
                    },
                ],
                next_7_days_projection: [{ day_offset: 1, cards_count: 12, is_free: false }],
            };

            const result = parseDailyReviews(json);

            expect(result.summary).toEqual({
                totalPending: 10,
                estimatedTimeMinutes: 15,
                split: { new: 3, learning: 4, review: 3 },
            });

            expect(result.decksToday).toEqual([
                {
                    id: 'deck-1',
                    subjectId: 'sub-1',
                    subjectName: 'Cálculo I',
                    subtitle: 'Derivadas',
                    color: '#ff0000',
                    icon: 'sigma',
                    new: 2,
                    learning: 1,
                    review: 5,
                    totalCards: 8,
                },
            ]);

            expect(result.next7DaysProjection).toEqual([
                { dayOffset: 1, cardsCount: 12, isFree: false },
            ]);
        });

        it('zero-defaults deck fields that are missing', () => {
            const json = { decks_today: [{ id: 'deck-2' }] };
            const result = parseDailyReviews(json);
            expect(result.decksToday[0]).toEqual({
                id: 'deck-2',
                subjectId: undefined,
                subjectName: 'Untitled',
                subtitle: '',
                color: '#gray',
                icon: 'book',
                new: 0,
                learning: 0,
                review: 0,
                totalCards: 0,
            });
        });

        it('returns an empty object for missing input', () => {
            expect(parseDailyReviews(null)).toEqual({});
        });
    });
});
