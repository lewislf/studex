// Pure radial layout for mind map nodes: no external layout dependency.
// tema_central sits at the origin, categoria nodes ring around it, and each
// categoria's detalhe nodes fan out further along that categoria's own
// angular slice. Positions are packed by each label's ESTIMATED pixel width
// (not a fixed count-per-ring): a long title ("A Sociedade de Planolândia")
// takes more angular room than a short one ("O Quadrado"), so packing by
// real width is what actually prevents overlap, uniform division doesn't.

const CATEGORY_RADIUS = 380;
const DETAIL_RADIUS = 230;
const RING_STEP = 130; // extra radius per ring, when a ring's angular budget fills up
const GAP_PX = 18; // minimum breathing room between two neighboring pills
const MAX_FAN_SPREAD = (150 * Math.PI) / 180; // cap fan width even when there are few categories

// Rough px-per-character + pill chrome (padding/border), just enough to size
// the angular slot each node needs. Doesn't need to be exact, only order-of-
// magnitude honest, since it directly drives the anti-overlap packing below.
function estimateNodeWidth(label, kind) {
    const text = String(label || '');
    if (kind === 'tema_central') return text.length * 10 + 64;
    if (kind === 'categoria') return text.length * 8.5 + 56;
    return text.length * 7.2 + 48;
}

// Pill height barely varies with text (single line, wraps at 2 lines only
// for very long labels), so a constant per type is honest enough.
function estimateNodeHeight(kind) {
    if (kind === 'tema_central') return 56;
    if (kind === 'categoria') return 46;
    return 38;
}

// Neutral, dark color for the root so it contrasts with every branch color.
const ROOT_COLOR = '#2B2D42';

// One vivid + one light tint per branch, cycled by category index. The
// category node uses `strong`, its details and hierarchy edges reuse it too,
// except detail nodes which use `light` so the whole branch reads as one
// colored unit while staying visually lighter than its category.
const BRANCH_COLORS = [
    { strong: '#FF5A5F', light: '#FFD9DB' }, // coral red
    { strong: '#1E88E5', light: '#CDE7FC' }, // vivid blue
    { strong: '#00A878', light: '#CFF3E6' }, // emerald green
    { strong: '#FB8C00', light: '#FFE3BF' }, // orange
    { strong: '#8E24AA', light: '#EAD1F2' }, // purple
    { strong: '#00ACC1', light: '#CDEFF4' }, // cyan
    { strong: '#E91E63', light: '#FBD2E1' }, // pink
    { strong: '#F9A825', light: '#FDECC8' }, // mustard yellow
];

/**
 * Greedily packs `items` into concentric rings around a center, so that no
 * two items sharing a ring overlap: each item's angular width (at that
 * ring's radius) is estimated from its label, and a new ring starts as soon
 * as the current one runs out of angular budget. Returns each item with its
 * assigned {angle, radius} (angle in radians, absolute).
 *
 * @param {Array} items - Each must have a `label` used to estimate width.
 * @param {(item) => number} widthOf - Returns the item's estimated pixel width.
 * @param {number} centerAngle - Middle angle (radians) of the whole budget.
 * @param {number} angleBudget - Total angular width (radians) available per ring.
 * @param {number} radius0 - Radius of the first ring.
 * @param {number} ringStep - Extra radius added per further-out ring.
 */
function packRing(items, widthOf, centerAngle, angleBudget, radius0, ringStep) {
    const placements = [];
    let ring = 0;
    let ringItems = [];

    function flushRing() {
        if (!ringItems.length) return;
        const radius = radius0 + ring * ringStep;
        const totalAngle = ringItems.reduce((sum, r) => sum + r.angleWidth, 0);
        let cursor = centerAngle - totalAngle / 2;
        for (const r of ringItems) {
            const angle = cursor + r.angleWidth / 2;
            placements.push({ item: r.item, angle, radius });
            cursor += r.angleWidth;
        }
        ringItems = [];
    }

    let used = 0;
    for (const item of items) {
        const radius = radius0 + ring * ringStep;
        const widthPx = widthOf(item) + GAP_PX;
        // Angular width this item needs at this ring's radius, so it doesn't
        // visually collide with its ring-mates (chord approximation).
        const angleWidth = Math.min(angleBudget, 2 * Math.asin(Math.min(1, widthPx / 2 / radius)));

        if (used + angleWidth > angleBudget && ringItems.length > 0) {
            flushRing();
            ring += 1;
            used = 0;
        }
        ringItems.push({ item, angleWidth });
        used += angleWidth;
    }
    flushRing();

    return placements;
}

/**
 * Distributes `items` evenly around a FULL circle (used for categories
 * around the root): unlike packRing (which packs a bounded fan as tightly
 * as it needs, then centers that tight cluster on one angle, right for a
 * category's own detail fan), a ring around the root should always use the
 * whole 360°, not just the minimum arc the items require, or a handful of
 * categories bunch up near the top instead of surrounding the root. Any
 * leftover slack (2π minus what the items strictly need) is spread as extra
 * gap between them. Only wraps to a further-out ring if items genuinely
 * don't fit even at their minimum width.
 *
 * @param {Array} items - Each must have a `label` used to estimate width.
 * @param {(item) => number} widthOf - Returns the item's estimated pixel width.
 * @param {number} radius0 - Radius of the first ring.
 * @param {number} ringStep - Extra radius added per further-out ring.
 */
function packFullCircle(items, widthOf, radius0, ringStep) {
    const placements = [];
    let ring = 0;
    let remaining = items;

    while (remaining.length) {
        const radius = radius0 + ring * ringStep;
        const widths = remaining.map((item) => ({
            item,
            angleWidth: Math.min(
                2 * Math.PI,
                2 * Math.asin(Math.min(1, (widthOf(item) + GAP_PX) / 2 / radius))
            ),
        }));

        // Greedily take as many as fit this ring's 2π budget, in order; the
        // rest overflow to a further-out ring (rare: MAX_TEMAS caps this low).
        let used = 0;
        const thisRing = [];
        const overflow = [];
        for (const w of widths) {
            if (thisRing.length === 0 || used + w.angleWidth <= 2 * Math.PI) {
                thisRing.push(w);
                used += w.angleWidth;
            } else {
                overflow.push(w.item);
            }
        }

        // Spread thisRing across the FULL circle, not just the arc it needs:
        // leftover slack becomes extra gap between items, so a few categories
        // don't cluster near the top with a huge empty arc on the other side.
        const extraGapEach = Math.max(0, 2 * Math.PI - used) / thisRing.length;
        let cursor = -Math.PI / 2;
        for (const w of thisRing) {
            const slot = w.angleWidth + extraGapEach;
            const angle = cursor + slot / 2;
            placements.push({ item: w.item, angle, radius });
            cursor += slot;
        }

        remaining = overflow;
        ring += 1;
    }

    return placements;
}

/**
 * Computes {x, y} positions for a mind map's nodes.
 *
 * @param {Array} nodes - Nodes without position (tema_central, categoria, detalhe).
 * @param {Array} edges - Hierarchical + "relacao" edges; only non-relacao edges define the tree.
 * @returns {Array} Same nodes with a `position` field added.
 */
export function layoutMindMap(nodes, edges) {
    if (!nodes?.length) return [];

    const byId = new Map(nodes.map(n => [n.id, n]));
    const root = nodes.find(n => n.type === 'tema_central') ?? nodes[0];

    // Relation edges ("relacao") are cross-links, not tree structure.
    const treeEdges = (edges || []).filter(e => e.type !== 'relacao');
    const childrenOf = (id) =>
        treeEdges.filter(e => e.source === id).map(e => byId.get(e.target)).filter(Boolean);

    const positioned = new Map();
    const colors = new Map();
    positioned.set(root.id, { x: 0, y: 0 });
    colors.set(root.id, ROOT_COLOR);

    const categories = childrenOf(root.id).filter(n => n.type === 'categoria');

    // Categories ring the root, evenly spread across the full circle (not
    // just the minimum arc their labels need, see packFullCircle's doc).
    const categoryPlacements = packFullCircle(
        categories,
        (cat) => estimateNodeWidth(cat.data?.label, 'categoria'),
        CATEGORY_RADIUS,
        RING_STEP
    );

    categoryPlacements.forEach(({ item: cat, angle, radius }, i) => {
        const branch = BRANCH_COLORS[i % BRANCH_COLORS.length];
        const cx = Math.cos(angle) * radius;
        const cy = Math.sin(angle) * radius;
        positioned.set(cat.id, { x: cx, y: cy });
        colors.set(cat.id, branch.strong);

        const details = childrenOf(cat.id).filter(n2 => n2.type === 'detalhe');
        if (!details.length) return;

        // Details fan out from the category's own position, within a slice
        // centered on the category's angle (so fans stay in their own
        // territory instead of drifting toward a neighbor).
        const spread = Math.min(MAX_FAN_SPREAD, (2 * Math.PI) / Math.max(categories.length, 1) * 1.4);
        const detailPlacements = packRing(
            details,
            (det) => estimateNodeWidth(det.data?.label, 'detalhe'),
            angle,
            spread,
            DETAIL_RADIUS,
            RING_STEP
        );

        detailPlacements.forEach(({ item: det, angle: detAngle, radius: detRadius }) => {
            positioned.set(det.id, {
                x: cx + Math.cos(detAngle) * detRadius,
                y: cy + Math.sin(detAngle) * detRadius,
            });
            colors.set(det.id, branch.light);
        });
    });

    // The angle-based packing above keeps each category's own fan tidy, but
    // says nothing about categories/details from DIFFERENT branches, or about
    // the root itself (whose own pill can be very wide with a long title).
    // A generic declutter pass over every positioned node is the safety net:
    // it catches whatever the angular math missed, root included.
    const movableIds = [...positioned.keys()].filter((id) => id !== root.id);
    const movableBoxes = movableIds.map((id) => {
        const node = byId.get(id);
        const pos = positioned.get(id);
        return { id, x: pos.x, y: pos.y, width: estimateNodeWidth(node?.data?.label, node?.type), height: estimateNodeHeight(node?.type) };
    });
    const rootBox = {
        x: 0, y: 0,
        width: estimateNodeWidth(root.data?.label, 'tema_central'),
        height: estimateNodeHeight('tema_central'),
    };
    declutter(movableBoxes, [rootBox], 16);
    movableBoxes.forEach((box) => positioned.set(box.id, { x: box.x, y: box.y }));

    // Defensive fallback: nodes unreachable from the root (malformed data)
    // still get a position so nothing is silently dropped from the canvas.
    let strayIndex = 0;
    return nodes.map((node) => {
        const position = positioned.get(node.id);
        const color = colors.get(node.id) ?? ROOT_COLOR;
        const data = { ...node.data, color };
        if (position) return { ...node, position, data };
        strayIndex += 1;
        return { ...node, position: { x: 60 * strayIndex, y: -CATEGORY_RADIUS - 60 * strayIndex }, data };
    });
}

// Rough size of a relation edge's little label chip, from its text length.
// Height is fixed (labels are single-line); width follows the same
// per-character heuristic as node pills, capped so one long description
// can't eat so much space the declutter pass has nowhere to put it (the
// pill itself truncates with an ellipsis past this width too, see
// MindMap.module.css's .relacaoEdgeLabel).
const LABEL_HEIGHT = 22;
export const LABEL_MAX_WIDTH = 210;
function estimateLabelSize(text) {
    const width = String(text || '').length * 6.4 + 16;
    return { width: Math.min(Math.max(width, 32), LABEL_MAX_WIDTH), height: LABEL_HEIGHT };
}

/** Builds fixed obstacle boxes from already-positioned nodes, so relation
 * labels can be pushed away from the node pills too, not just from each
 * other (a decluttered label stack can otherwise land right on top of a
 * node it's nowhere near touching in the raw/undeclu­ttered position). */
export function buildNodeObstacles(nodes) {
    return (nodes || [])
        .filter((n) => n.position)
        .map((n) => ({
            x: n.position.x,
            y: n.position.y,
            width: estimateNodeWidth(n.data?.label, n.type),
            height: estimateNodeHeight(n.type),
        }));
}

function boxOverlap(a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    return {
        dx,
        dy,
        overlapX: (a.width + b.width) / 2 - Math.abs(dx),
        overlapY: (a.height + b.height) / 2 - Math.abs(dy),
    };
}

/**
 * Rectangle-declutter relaxation, the shared engine behind both node and
 * label anti-overlap: on each pass, every colliding pair of `movable` boxes
 * is pushed apart along whichever axis needs the smaller push (mutual, both
 * move), and any `movable` box colliding with a `fixed` one absorbs the
 * whole push itself (the fixed box never moves). Repeats until nothing
 * collides or `maxIterations` is hit, so a pathological case can't hang the
 * tab. Mutates `movable` boxes' x/y in place.
 *
 * @param {Array<{x, y, width, height}>} movable
 * @param {Array<{x, y, width, height}>} fixed
 */
function declutter(movable, fixed, maxIterations) {
    for (let iter = 0; iter < maxIterations; iter++) {
        let moved = false;

        for (let i = 0; i < movable.length; i++) {
            for (let j = i + 1; j < movable.length; j++) {
                const a = movable[i];
                const b = movable[j];
                const { dx, dy, overlapX, overlapY } = boxOverlap(a, b);
                if (overlapX <= 0 || overlapY <= 0) continue;

                moved = true;
                if (overlapX < overlapY) {
                    const push = overlapX / 2 + 1;
                    const dir = dx >= 0 ? 1 : -1;
                    a.x -= push * dir;
                    b.x += push * dir;
                } else {
                    const push = overlapY / 2 + 1;
                    const dir = dy >= 0 ? 1 : -1;
                    a.y -= push * dir;
                    b.y += push * dir;
                }
            }

            for (const obstacle of fixed) {
                const a = movable[i];
                const { dx, dy, overlapX, overlapY } = boxOverlap(a, obstacle);
                if (overlapX <= 0 || overlapY <= 0) continue;

                moved = true;
                // Obstacle is fixed: the movable box absorbs the whole push, not half.
                if (overlapX < overlapY) {
                    a.x += (overlapX + 2) * (dx >= 0 ? -1 : 1);
                } else {
                    a.y += (overlapY + 2) * (dy >= 0 ? -1 : 1);
                }
            }
        }

        if (!moved) break;
    }
}

/**
 * Nudges apart any relation-edge labels whose boxes would otherwise overlap
 * each other OR one of the graph's node pills (`obstacles`, fixed in place).
 *
 * @param {Array<{id, x, y, label}>} labels - Raw (pre-collision) label positions.
 * @param {Array<{x, y, width, height}>} obstacles - Fixed boxes (node pills) to avoid.
 * @returns {Map<string, {dx: number, dy: number}>} Offset to apply per label id.
 */
export function resolveLabelOverlaps(labels, obstacles = [], maxIterations = 60) {
    const boxes = labels.map((l) => ({ ...l, ...estimateLabelSize(l.label) }));
    declutter(boxes, obstacles, maxIterations);

    const offsets = new Map();
    boxes.forEach((box, i) => {
        offsets.set(labels[i].id, { dx: box.x - labels[i].x, dy: box.y - labels[i].y });
    });
    return offsets;
}
