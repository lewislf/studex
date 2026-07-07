/**
 * Parser for: userProfileMock.json
 * Handles global profile data, authentication, and core metrics counters.
 */
export function parseUserProfile(json) {
    if (!json) return {};
    return {
        id: json.id || '',
        name: json.profile?.display_name || 'User',
        email: json.profile?.email || '',
        avatar: json.profile?.photo || '',
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

// MOCKING, WILL BE DELETED WHENEVER THE API IS READY
import subjectsListMock from '../config/subjectsListMock.json';
import { DEFAULT_SUBJECT_ICON, DEFAULT_SUBJECT_COLOR } from '../config/Constants';

/**
 * Parser for: subjectsListMock.json or API subjects list.
 * Maps the raw subjects array and enriches it with visual configurations (colors, icons, counters).
 */
export function parseSubjectsListMock(json) {
    if (!json) return [];
    
    // Support both API response array or wrapper object containing subjects array
    const rawSubjects = Array.isArray(json) 
        ? json 
        : (Array.isArray(json.subjects) ? json.subjects : []);

    const mockSubjects = subjectsListMock.subjects || [];

    return rawSubjects.map(subject => {
        // Normalize property mapping to support database fields (e.g. name -> title)
        const titleStr = subject.title || subject.name || 'Untitled';
        
        // Find matching mock subject by title (case-insensitive) or ID
        const match = mockSubjects.find(
            m => String(m.id) === String(subject.id) ||
                 m.title?.toLowerCase() === titleStr.toLowerCase()
        );

        if (match) {
            return {
                id: subject.id,
                title: titleStr,
                icon: match.icon || DEFAULT_SUBJECT_ICON,
                color: match.color || DEFAULT_SUBJECT_COLOR,
                lastActivity: subject.last_activity || match.last_activity || '',
                totalTopics: Number(subject.total_topics || match.total_topics) || 11,
                masteryPercentage: Number(subject.mastery_percentage !== undefined ? subject.mastery_percentage : subject.domain) !== undefined 
                    ? Number(subject.mastery_percentage !== undefined ? subject.mastery_percentage : subject.domain) 
                    : (Number(match.mastery_percentage) || 0),
                pendingInQueue: Number(subject.pending_in_queue !== undefined ? subject.pending_in_queue : match.pending_in_queue) || 0,
                counters: {
                    summaries: Number(subject.counters?.summaries !== undefined ? subject.counters?.summaries : match.counters?.summaries) || 0,
                    mindMaps: Number(subject.counters?.mind_maps !== undefined ? subject.counters?.mind_maps : match.counters?.mind_maps) || 0,
                    flashcards: Number(subject.counters?.flashcards !== undefined ? subject.counters?.flashcards : match.counters?.flashcards) || 0,
                }
            };
        }

        // Default layout mapping for new/custom subjects
        return {
            id: subject.id,
            title: titleStr,
            icon: subject.icon || DEFAULT_SUBJECT_ICON,
            color: subject.color || DEFAULT_SUBJECT_COLOR,
            lastActivity: subject.last_activity || '',
            totalTopics: Number(subject.total_topics) || 11,
            masteryPercentage: Number(subject.mastery_percentage !== undefined ? subject.mastery_percentage : subject.domain) || 0,
            pendingInQueue: Number(subject.pending_in_queue) || 0,
            counters: {
                summaries: Number(subject.counters?.summaries) || 0,
                mindMaps: Number(subject.counters?.mind_maps) || 0,
                flashcards: Number(subject.counters?.flashcards) || 0,
            }
        };
    });
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
