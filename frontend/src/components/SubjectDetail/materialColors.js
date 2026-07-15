// Strong colors per material type, kept out of MaterialIcon.jsx so that file
// stays a pure component module (fast-refresh only works when a file only
// exports components).
const TYPE_COLORS = {
    resumo: 'var(--mantine-color-blue-6)',
    mapa: 'var(--mantine-color-violet-6)',
    flashcards: 'var(--mantine-color-orange-6)',
};

/** Strong color for a material type, reused for the card stripe/"abrir >" link
 * so the whole card matches its section's identity, not the subject's color. */
export function materialTypeColor(type) {
    return TYPE_COLORS[type];
}
