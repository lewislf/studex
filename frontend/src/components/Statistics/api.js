// Fetch helper for the statistics dashboard route.

const API_URL = import.meta.env.VITE_API_URL;

/** GETs a JSON resource; a 404 response resolves to null instead of throwing. */
async function getJson(url) {
    const res = await fetch(url);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`request failed (${res.status})`);
    return res.json();
}

/**
 * Fetches the user's activity summary: a local ISO day -> activity count map
 * (flashcard reviews + uploads) powering the contribution heatmap, plus the
 * backend-calculated current streak.
 *
 * @param {string|number} userId
 * @returns {Promise<{days: Object<string, number>, current_streak: number, today_active: boolean}|null>}
 */
export function fetchActivity(userId) {
    return getJson(`${API_URL}/users/${userId}/activity`);
}
