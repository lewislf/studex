/**
 * Parser for: userProfileMock.json
 * Handles global profile data, authentication, and core metrics counters.
 */
export function parseUserProfile(json) {
    if (!json) return {};
    return {
        id: json.id || '',
        name: json.name || 'User',
        email: json.email || '',
        gamification: {
            streak: Number(json.gamification?.current_streak) || 0,
            activeYesterday: Boolean(json.gamification?.active_yesterday)
        },
        counters: {
            summariesCount: Number(json.counters?.summaries) || 0,
            mapsCount: Number(json.counters?.mind_maps) || 0,
            pendingFlashcardsToday: Number(json.counters?.pending_flashcards_today) || 0,
            totalFlashcardsCreated: Number(json.counters?.total_flashcards_created) || 0,
        }
    };
}

/**
 * Parser for: dailyReviewsMock.json
 * Handles the FSRS review queue summary, current day decks, and future projections.
 */
export function parseDailyReviews(json) {
    if (!json) return {};
    return {
        summary: {
            totalPending: Number(json.summary?.total_pending) || 0,
            estimatedTimeMinutes: Number(json.summary?.estimated_time_minutes) || 0,
            split: {
                new: Number(json.summary?.split?.new) || 0,
                learning: Number(json.summary?.split?.learning) || 0,
                review: Number(json.summary?.split?.review) || 0,
            }
        },
        decksToday: (json.decks_today || []).map(deck => ({
            id: deck.id,
            subjectId: deck.subject_id,
            subjectName: deck.subject_name || 'Untitled',
            subtitle: deck.subtitle || '',
            color: deck.color || '#gray',
            icon: deck.icon || 'book',
            new: Number(deck.new) || 0,
            learning: Number(deck.learning) || 0,
            review: Number(deck.review) || 0,
            totalCards: Number(deck.total_cards) || 0,
        })),
        next7DaysProjection: (json.next_7_days_projection || []).map(day => ({
            dayOffset: Number(day.day_offset) || 0,
            cardsCount: Number(day.cards_count) || 0,
            isFree: Boolean(day.is_free)
        }))
    };
}

import { DEFAULT_SUBJECT_ICON, DEFAULT_SUBJECT_COLOR } from '../config/Constants';

/**
 * Parser for the API's subjects list response. Every field comes straight
 * from the backend, with sane zero-defaults for a brand-new subject, no
 * mock-data fallback (a previous version filled gaps by name-matching a
 * bundled mock file, which could silently swap in fake numbers for a real
 * subject that happened to share a name with a mock entry).
 */
export function parseSubjectsList(json) {
    if (!json) return [];

    // Support both API response array or wrapper object containing subjects array
    const rawSubjects = Array.isArray(json)
        ? json
        : (Array.isArray(json.subjects) ? json.subjects : []);

    return rawSubjects.map(subject => ({
        id: subject.id,
        title: subject.title || subject.name || 'Untitled',
        icon: subject.icon || DEFAULT_SUBJECT_ICON,
        color: subject.color || DEFAULT_SUBJECT_COLOR,
        lastActivity: subject.last_activity || '',
        masteryPercentage: Number(subject.mastery_percentage !== undefined ? subject.mastery_percentage : subject.domain) || 0,
        pendingInQueue: Number(subject.pending_in_queue) || 0,
        counters: {
            summaries: Number(subject.counters?.summaries) || 0,
            mindMaps: Number(subject.counters?.mind_maps) || 0,
            flashcards: Number(subject.counters?.flashcards) || 0,
        }
    }));
}

/**
 * Parser for: userStats.json
 * Handles exclusively analytical metrics
 */
export function parseUserStats(json) {
    if (!json) return {};
    return {
        userId: json.user_id || '',
        statsDistribution: (json.stats_distribution?.categories || []).map(category => ({
            label: category.label || 'Others',
            percentage: Number(category.percentage) || 0,
            color: category.color || '#gray'
        })),
        activityHeatmap: json.activity_heatmap || {}
    };
}
