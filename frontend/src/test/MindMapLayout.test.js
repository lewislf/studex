import { describe, it, expect } from 'vitest';
import { layoutMindMap, resolveLabelOverlaps, buildNodeObstacles, LABEL_MAX_WIDTH } from '../components/SubjectDetail/MindMapLayout';

function makeGraph({ categoryCount = 4, detailsPerCategory = 3 } = {}) {
    const nodes = [{ id: 'root', type: 'tema_central', data: { label: 'A Sociedade de Planolândia' } }];
    const edges = [];

    for (let c = 0; c < categoryCount; c++) {
        const catId = `cat-${c}`;
        nodes.push({ id: catId, type: 'categoria', data: { label: `Categoria ${c} com título razoavelmente longo` } });
        edges.push({ source: 'root', target: catId, type: 'hierarquia' });

        for (let d = 0; d < detailsPerCategory; d++) {
            const detId = `${catId}-det-${d}`;
            nodes.push({ id: detId, type: 'detalhe', data: { label: `Detalhe ${c}.${d}` } });
            edges.push({ source: catId, target: detId, type: 'hierarquia' });
        }
    }

    return { nodes, edges };
}

// Axis-aligned rectangle overlap area, from a positioned/sized box.
function rectOverlapArea(a, b) {
    const dx = Math.abs(a.x - b.x);
    const dy = Math.abs(a.y - b.y);
    const overlapX = (a.width + b.width) / 2 - dx;
    const overlapY = (a.height + b.height) / 2 - dy;
    return overlapX > 0 && overlapY > 0 ? overlapX * overlapY : 0;
}

describe('MindMapLayout', () => {
    describe('layoutMindMap', () => {
        it('returns an empty array for no nodes', () => {
            expect(layoutMindMap([], [])).toEqual([]);
            expect(layoutMindMap(null, [])).toEqual([]);
        });

        it('positions the root at the origin', () => {
            const { nodes, edges } = makeGraph();
            const result = layoutMindMap(nodes, edges);
            const root = result.find((n) => n.id === 'root');
            expect(root.position).toEqual({ x: 0, y: 0 });
        });

        it('generates finite, non-NaN positions for every node', () => {
            const { nodes, edges } = makeGraph({ categoryCount: 6, detailsPerCategory: 4 });
            const result = layoutMindMap(nodes, edges);

            expect(result).toHaveLength(nodes.length);
            for (const node of result) {
                expect(node.position).toBeDefined();
                expect(Number.isFinite(node.position.x)).toBe(true);
                expect(Number.isFinite(node.position.y)).toBe(true);
                expect(Number.isNaN(node.position.x)).toBe(false);
                expect(Number.isNaN(node.position.y)).toBe(false);
            }
        });

        it('spreads categories around the full circle instead of clustering', () => {
            const { nodes, edges } = makeGraph({ categoryCount: 4, detailsPerCategory: 0 });
            const result = layoutMindMap(nodes, edges);
            const categories = result.filter((n) => n.type === 'categoria');

            const angles = categories.map((c) => Math.atan2(c.position.y, c.position.x));
            // 4 categories spread across 2*PI should land in at least 3 distinct
            // quadrant-ish buckets, not all bunched in one narrow arc.
            const buckets = new Set(angles.map((a) => Math.round((a + Math.PI) / (Math.PI / 2))));
            expect(buckets.size).toBeGreaterThanOrEqual(3);
        });

        it('assigns a color to every node, root included', () => {
            const { nodes, edges } = makeGraph({ categoryCount: 2, detailsPerCategory: 2 });
            const result = layoutMindMap(nodes, edges);
            for (const node of result) {
                expect(node.data.color).toBeTruthy();
            }
        });

        it('gives stray nodes unreachable from the root a fallback position instead of dropping them', () => {
            const nodes = [
                { id: 'root', type: 'tema_central', data: { label: 'Tema' } },
                { id: 'orphan', type: 'detalhe', data: { label: 'Sem pai' } },
            ];
            const result = layoutMindMap(nodes, []);
            const orphan = result.find((n) => n.id === 'orphan');
            expect(orphan.position).toBeDefined();
            expect(Number.isNaN(orphan.position.x)).toBe(false);
            expect(Number.isNaN(orphan.position.y)).toBe(false);
        });

        it('keeps node pill boxes from overlapping after the declutter pass, even with long labels', () => {
            const { nodes, edges } = makeGraph({ categoryCount: 8, detailsPerCategory: 5 });
            const result = layoutMindMap(nodes, edges);
            const obstacles = buildNodeObstacles(result).map((box, i) => ({ ...box, id: result[i].id }));

            let overlaps = 0;
            for (let i = 0; i < obstacles.length; i++) {
                for (let j = i + 1; j < obstacles.length; j++) {
                    if (rectOverlapArea(obstacles[i], obstacles[j]) > 0) overlaps++;
                }
            }
            expect(overlaps).toBe(0);
        });
    });

    describe('resolveLabelOverlaps', () => {
        it('returns a zero offset when there is nothing to resolve', () => {
            const offsets = resolveLabelOverlaps([]);
            expect(offsets.size).toBe(0);
        });

        it('eliminates overlaps between labels placed on top of each other', () => {
            const labels = [
                { id: 'l1', x: 0, y: 0, label: 'Relacionamento A com B' },
                { id: 'l2', x: 0, y: 0, label: 'Outro relacionamento' },
                { id: 'l3', x: 5, y: 2, label: 'Terceiro rótulo' },
            ];

            const offsets = resolveLabelOverlaps(labels);
            expect(offsets.size).toBe(labels.length);

            const boxes = labels.map((l) => {
                const off = offsets.get(l.id);
                const width = Math.min(Math.max(String(l.label).length * 6.4 + 16, 32), LABEL_MAX_WIDTH);
                return { x: l.x + off.dx, y: l.y + off.dy, width, height: 22 };
            });

            let overlaps = 0;
            for (let i = 0; i < boxes.length; i++) {
                for (let j = i + 1; j < boxes.length; j++) {
                    if (rectOverlapArea(boxes[i], boxes[j]) > 0) overlaps++;
                }
            }
            expect(overlaps).toBe(0);
        });

        it('pushes labels away from fixed node obstacles', () => {
            const labels = [{ id: 'l1', x: 0, y: 0, label: 'Rótulo sobre o nó' }];
            const obstacles = [{ x: 0, y: 0, width: 200, height: 60 }];

            const offsets = resolveLabelOverlaps(labels, obstacles);
            const off = offsets.get('l1');
            // Must have moved away from dead-center overlap with the obstacle.
            expect(off.dx !== 0 || off.dy !== 0).toBe(true);
        });

        it('caps label width via LABEL_MAX_WIDTH regardless of label length', () => {
            const longLabel = 'x'.repeat(200);
            const labels = [{ id: 'l1', x: 0, y: 0, label: longLabel }];
            // No obstacles/collisions: offset should stay zero, but this also
            // exercises the width estimate path without throwing for very long text.
            const offsets = resolveLabelOverlaps(labels);
            expect(offsets.get('l1')).toEqual({ dx: 0, dy: 0 });
            expect(LABEL_MAX_WIDTH).toBeGreaterThan(0);
        });
    });

    describe('buildNodeObstacles', () => {
        it('builds one obstacle box per positioned node', () => {
            const nodes = [
                { id: 'a', type: 'categoria', data: { label: 'A' }, position: { x: 10, y: 20 } },
                { id: 'b', type: 'detalhe', data: { label: 'B' }, position: { x: -5, y: 8 } },
            ];
            const obstacles = buildNodeObstacles(nodes);
            expect(obstacles).toHaveLength(2);
            expect(obstacles[0]).toMatchObject({ x: 10, y: 20 });
            expect(obstacles[0].width).toBeGreaterThan(0);
            expect(obstacles[0].height).toBeGreaterThan(0);
        });

        it('skips nodes without a position', () => {
            const nodes = [{ id: 'a', type: 'categoria', data: { label: 'A' } }];
            expect(buildNodeObstacles(nodes)).toEqual([]);
        });

        it('handles a missing/null nodes argument', () => {
            expect(buildNodeObstacles(null)).toEqual([]);
            expect(buildNodeObstacles(undefined)).toEqual([]);
        });
    });
});
