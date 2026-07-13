import { useCallback, useMemo, useState } from 'react';
import { ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { ActionIcon } from '@mantine/core';
import { IconX } from '@tabler/icons-react';
import { TemaCentralNode, CategoriaNode, DetalheNode } from './MindMapNodes.jsx';
import { RelacaoEdge, HierarquiaEdge } from './MindMapEdges.jsx';
import { resolveLabelOverlaps, buildNodeObstacles } from './MindMapLayout.js';
import styles from '../../styles/SubjectDetail/MindMap.module.css';

// Defined outside the component: react-flow requires stable nodeTypes/edgeTypes
// references, otherwise it remounts (and warns) on every render.
const nodeTypes = { tema_central: TemaCentralNode, categoria: CategoriaNode, detalhe: DetalheNode };
const edgeTypes = { relacao: RelacaoEdge, hierarquia: HierarquiaEdge };

const INITIAL_ZOOM = 0.8;

/** Every relation label's raw (pre-declutter) position: the midpoint between
 * its two endpoint nodes. Approximate (node.position isn't exactly the
 * rendered handle point), but consistent across all labels, which is all
 * `resolveLabelOverlaps` needs to detect and fix collisions between them. */
function rawRelationLabelPositions(edges, nodeById) {
    return (edges || [])
        .filter((e) => e.type === 'relacao' && e.data?.label)
        .map((e) => {
            const s = nodeById.get(e.source)?.position;
            const t = nodeById.get(e.target)?.position;
            if (!s || !t) return null;
            return { id: e.id, x: (s.x + t.x) / 2, y: (s.y + t.y) / 2, label: e.data.label };
        })
        .filter(Boolean);
}

/** Colors every edge from its endpoints' branch (set once on each node's data
 * in MindMapLayout.js, so this is a lookup, never a recomputation). Non-
 * "relacao" edges are also re-typed to the curved hierarchy edge. Relation
 * edges also get a `labelOffset` (from `labelOffsets`) so their always-on
 * label can be nudged away from other labels converging on the same node. */
function colorizeEdges(edges, nodes, labelOffsets) {
    const nodeById = new Map(nodes.map((n) => [n.id, n]));

    return (edges || []).map((edge) => {
        const source = nodeById.get(edge.source);
        const target = nodeById.get(edge.target);
        // Prefer whichever endpoint is a categoria/detalhe (has a branch color)
        // over the root's neutral color, so the edge reads as "part of that branch".
        const color =
            (source?.type !== 'tema_central' && source?.data?.color) ||
            (target?.type !== 'tema_central' && target?.data?.color) ||
            source?.data?.color;

        if (edge.type === 'relacao') {
            const labelOffset = labelOffsets.get(edge.id) ?? { dx: 0, dy: 0 };
            return { ...edge, data: { ...edge.data, color, labelOffset } };
        }

        return {
            ...edge,
            type: 'hierarquia',
            style: undefined,
            data: { ...edge.data, color },
            markerEnd: { type: MarkerType.ArrowClosed, color, width: 16, height: 16 },
        };
    });
}

/**
 * Read-only React Flow canvas for a single mind map: nodes are draggable
 * for exploration but nothing is editable (no new nodes/edges, no delete).
 * Clicking a node opens a side panel with its full content; clicking the
 * background or the close button dismisses it.
 *
 * @param {Object} props
 * @param {Array} props.nodes - Positioned nodes (see MindMapLayout.js).
 * @param {Array} props.edges - Hierarchical + relation edges.
 */
export default function MindMapCanvas({ nodes, edges }) {
    const [selected, setSelected] = useState(null);

    const labelOffsets = useMemo(() => {
        const nodeById = new Map(nodes.map((n) => [n.id, n]));
        const rawLabels = rawRelationLabelPositions(edges, nodeById);
        return resolveLabelOverlaps(rawLabels, buildNodeObstacles(nodes));
    }, [edges, nodes]);

    const styledEdges = useMemo(
        () => colorizeEdges(edges, nodes, labelOffsets),
        [edges, nodes, labelOffsets]
    );
    const root = useMemo(() => nodes.find((n) => n.type === 'tema_central'), [nodes]);

    // Center the viewport on the central theme (always at the layout's
    // origin) instead of react-flow's default fitView-the-whole-graph.
    const onInit = useCallback(
        (instance) => {
            const { x, y } = root?.position ?? { x: 0, y: 0 };
            instance.setCenter(x, y, { zoom: INITIAL_ZOOM, duration: 0 });
        },
        [root]
    );

    const handleNodeClick = useCallback((_event, node) => setSelected(node), []);
    const handlePaneClick = useCallback(() => setSelected(null), []);

    return (
        <div className={styles.canvasWrapper}>
            <ReactFlowProvider>
                <ReactFlow
                    nodes={nodes}
                    edges={styledEdges}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    onInit={onInit}
                    onNodeClick={handleNodeClick}
                    onPaneClick={handlePaneClick}
                    nodesConnectable={false}
                    elementsSelectable
                    nodesFocusable
                    edgesReconnectable={false}
                    deleteKeyCode={null}
                >
                    <Background gap={24} />
                    <Controls showInteractive={false} />
                    <MiniMap pannable zoomable className={styles.minimap} />
                </ReactFlow>
            </ReactFlowProvider>

            {selected && (
                <aside className={styles.detailPanel}>
                    <ActionIcon
                        variant="subtle"
                        color="gray"
                        className={styles.detailPanelClose}
                        onClick={handlePaneClick}
                        aria-label="Fechar"
                    >
                        <IconX size={18} />
                    </ActionIcon>
                    <h3 className={styles.detailPanelTitle}>{selected.data?.label}</h3>
                    <p className={styles.detailPanelBody}>{selected.data?.conteudo}</p>
                </aside>
            )}
        </div>
    );
}
