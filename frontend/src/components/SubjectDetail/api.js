// Shared fetch helpers and formatting utilities for the subject detail pages
// (materia overview, summary reader, mind map viewer, deck flashcards).

const API_URL = import.meta.env.VITE_API_URL;

/**
 * Formats an ISO date/datetime string as pt-BR text.
 * Accepts either a plain date ("2026-07-08") or a full ISO datetime
 * ("2026-07-08T03:52:41"): older records only have the date part, newer
 * ones also carry the time, which is appended as "às HH:MM" when present.
 *
 * @param {string} dateStr - ISO date or datetime string.
 * @returns {string} Formatted "dd/mm/yyyy" or "dd/mm/yyyy às HH:MM".
 */
export function formatDate(dateStr) {
    if (!dateStr) return '';

    const [datePart, timePart] = String(dateStr).split('T');
    const [year, month, day] = datePart.split('-');
    if (!year || !month || !day) return dateStr;

    const formattedDate = `${day}/${month}/${year}`;
    if (!timePart) return formattedDate;

    const [hour, minute] = timePart.split(':');
    if (hour === undefined || minute === undefined) return formattedDate;

    return `${formattedDate} às ${hour}:${minute}`;
}

// Suffixes the generation pipeline appends to material titles. The subject
// detail cards already group items by type in their own section, so the
// suffix is redundant there and is stripped entirely instead of just deduped.
const KNOWN_TITLE_SUFFIXES = ['— Mapa Mental de Estudo', '— Flashcards'];

/**
 * Strips any known trailing type suffix from a material title, however
 * many times it appears (some titles carry it more than once).
 *
 * @param {string} title - Raw material title.
 * @returns {string} Title with no trailing type suffix.
 */
export function stripMaterialSuffix(title) {
    if (!title) return '';

    let base = String(title).trim();
    for (const suffix of KNOWN_TITLE_SUFFIXES) {
        const escaped = suffix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        base = base.replace(new RegExp(`(\\s*${escaped}\\s*)+$`), '').trim();
    }
    return base;
}

/**
 * Kept for backwards compatibility with existing callers (e.g. MindMapPage);
 * now fully strips the suffix instead of deduping it, since the section
 * heading already names the material type.
 *
 * @param {string} title - Raw mind map title.
 * @returns {string} Title with no trailing suffix.
 */
export function dedupeMindMapTitle(title) {
    return stripMaterialSuffix(title);
}

/** Deck title: backend field is "titulo" on creation but "subtitle" on to_dict. */
export function deckTitle(deck) {
    return stripMaterialSuffix(deck?.titulo || deck?.subtitle) || 'Baralho sem título';
}

/**
 * Parses a material's "conteudo" field, which the backend stores as a JSON
 * string but some callers may already have as a plain object.
 *
 * @param {string|Object|null} conteudo
 * @returns {Object|null} Parsed content, or null if missing/invalid.
 */
export function parseConteudo(conteudo) {
    if (!conteudo) return null;
    if (typeof conteudo === 'object') return conteudo;
    try {
        return JSON.parse(conteudo);
    } catch {
        return null;
    }
}

/** Deck creation date: backend field is "creation_date" on some routes, "date" on others. */
export function deckDate(deck) {
    return deck?.creation_date || deck?.date || '';
}

/** GETs a JSON resource; a 404 response resolves to null instead of throwing. */
async function getJson(url) {
    const res = await fetch(url);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`request failed (${res.status})`);
    return res.json();
}

export function fetchSubject(userId, subjectId) {
    return getJson(`${API_URL}/users/${userId}/subjects/${subjectId}`);
}

export async function fetchSummaries(userId, subjectId) {
    const data = await getJson(`${API_URL}/users/${userId}/subjects/${subjectId}/summaries`);
    return Array.isArray(data) ? data : [];
}

export function fetchSummary(userId, subjectId, summaryId) {
    return getJson(`${API_URL}/users/${userId}/subjects/${subjectId}/summaries/${summaryId}`);
}

export async function fetchMindMaps(userId, subjectId) {
    const data = await getJson(`${API_URL}/users/${userId}/subjects/${subjectId}/mindmaps`);
    return Array.isArray(data) ? data : [];
}

export async function fetchDecks(userId, subjectId) {
    const data = await getJson(`${API_URL}/users/${userId}/subjects/${subjectId}/decks`);
    return Array.isArray(data) ? data : [];
}

/**
 * Fetches the spaced-repetition study queue for a deck: the deck's own
 * summary plus the cards due for review, capped at `limit`.
 *
 * @param {string|number} userId
 * @param {string|number} subjectId
 * @param {string|number} deckId
 * @param {number} limit - Max cards to bring back in this session.
 * @returns {Promise<{deck: Object, cards: Array<Object>, total: number}|null>}
 */
export function fetchStudyQueue(userId, subjectId, deckId, limit) {
    return getJson(`${API_URL}/users/${userId}/subjects/${subjectId}/decks/${deckId}/study?limit=${limit}`);
}

/**
 * Fetches the global spaced-repetition study queue: due cards across every
 * deck of every subject the user has, capped at `limit`.
 *
 * @param {string|number} userId
 * @param {number} limit - Max cards to bring back in this session.
 * @returns {Promise<{cards: Array<Object>, total: number}|null>}
 */
export function fetchGlobalStudyQueue(userId, limit) {
    return getJson(`${API_URL}/users/${userId}/study?limit=${limit}`);
}

/**
 * Submits a spaced-repetition review for a single flashcard.
 *
 * @param {string|number} userId
 * @param {string|number} subjectId
 * @param {string|number} deckId
 * @param {string|number} flashcardId
 * @param {'reset'|'dificil'|'bom'|'facil'} rating
 * @returns {Promise<Object>} The updated card.
 */
export async function reviewFlashcard(userId, subjectId, deckId, flashcardId, rating) {
    const res = await fetch(
        `${API_URL}/users/${userId}/subjects/${subjectId}/decks/${deckId}/flashcards/${flashcardId}/review`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rating }),
        }
    );
    if (!res.ok) throw new Error(`request failed (${res.status})`);
    return res.json();
}
