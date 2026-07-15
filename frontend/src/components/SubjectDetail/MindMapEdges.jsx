import { BaseEdge, EdgeLabelRenderer, getStraightPath } from '@xyflow/react';
import styles from '../../styles/SubjectDetail/MindMap.module.css';

/** Dashed cross-link between two nodes, thickness scaled by data.forca, colored
 * by data.color (its branch). The label is always visible, nudged by
 * data.labelOffset (computed once for the whole graph in MindMapCanvas via
 * resolveLabelOverlaps) so labels from relations converging on the same
 * node don't stack on top of each other. When a label had to move, a small
 * dot + leader line (in the same color) ties it back to its true midpoint
 * on the line, so a displaced label is never ambiguous about which edge
 * it belongs to. */
export function RelacaoEdge({ sourceX, sourceY, targetX, targetY, data, markerEnd }) {
    const [edgePath, labelX, labelY] = getStraightPath({ sourceX, sourceY, targetX, targetY });
    const strokeWidth = 1 + (Number(data?.forca) || 4) / 4;
    const color = data?.color || 'var(--mantine-color-grape-6)';
    const offset = data?.labelOffset || { dx: 0, dy: 0 };
    const labelPosX = labelX + offset.dx;
    const labelPosY = labelY + offset.dy;
    const wasMoved = Math.hypot(offset.dx, offset.dy) > 4;

    return (
        <>
            <BaseEdge
                path={edgePath}
                markerEnd={markerEnd}
                className={styles.relacaoEdgePath}
                style={{ strokeWidth, stroke: color }}
            />
            {wasMoved && (
                <>
                    <line
                        x1={labelX} y1={labelY} x2={labelPosX} y2={labelPosY}
                        stroke={color} strokeWidth={1} strokeDasharray="2 2" opacity={0.7}
                    />
                    <circle cx={labelX} cy={labelY} r={3} fill={color} />
                </>
            )}
            {data?.label && (
                <EdgeLabelRenderer>
                    <div
                        className={`${styles.relacaoEdgeLabel} nodrag nopan`}
                        title={data.label}
                        style={{
                            transform: `translate(-50%, -50%) translate(${labelPosX}px, ${labelPosY}px)`,
                            borderColor: color,
                        }}
                    >
                        {data.label}
                    </div>
                </EdgeLabelRenderer>
            )}
        </>
    );
}

// Quadratic bezier through a control point offset perpendicular to the
// source->target line: gives a soft, hand-drawn curve regardless of the
// (fixed, non-directional) handle positions used by the radial layout,
// without relying on react-flow's directional smoothstep/bezier helpers.
function getBranchCurvePath(sourceX, sourceY, targetX, targetY, curvature = 0.18) {
    const dx = targetX - sourceX;
    const dy = targetY - sourceY;
    const midX = (sourceX + targetX) / 2 - dy * curvature;
    const midY = (sourceY + targetY) / 2 + dx * curvature;

    const path = `M ${sourceX},${sourceY} Q ${midX},${midY} ${targetX},${targetY}`;
    // Point at t=0.5 on the quadratic curve, used to anchor an (unused for now) label.
    const labelX = 0.25 * sourceX + 0.5 * midX + 0.25 * targetX;
    const labelY = 0.25 * sourceY + 0.5 * midY + 0.25 * targetY;
    return [path, labelX, labelY];
}

/** Solid hierarchy edge (tema->categoria or categoria->detalhe), colored by its branch. */
export function HierarquiaEdge({ sourceX, sourceY, targetX, targetY, data, markerEnd }) {
    const [edgePath] = getBranchCurvePath(sourceX, sourceY, targetX, targetY);
    return (
        <BaseEdge
            path={edgePath}
            markerEnd={markerEnd}
            style={{ stroke: data?.color || 'var(--mantine-color-gray-4)', strokeWidth: 2 }}
        />
    );
}

