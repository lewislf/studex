import { Handle, Position } from '@xyflow/react';
import styles from '../../styles/SubjectDetail/MindMap.module.css';

// Inline (not a CSS module class) so it always wins over react-flow's own
// handle stylesheet regardless of selector specificity/import order.
const HANDLE_STYLE = {
    opacity: 0,
    width: 1,
    height: 1,
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    border: 'none',
    background: 'transparent',
    pointerEvents: 'none',
};

// Handles are hidden and centered on the node: since the layout is radial
// (not top-to-bottom), a straight edge anchored at the node's center looks
// correct regardless of which direction the connected node is in.
function CenteredHandles() {
    return (
        <>
            <Handle type="target" position={Position.Top} style={HANDLE_STYLE} isConnectable={false} />
            <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} isConnectable={false} />
        </>
    );
}

/** Root node: the subject/topic the whole mind map is about. */
export function TemaCentralNode({ data }) {
    return (
        <div className={styles.temaCentralNode} style={{ backgroundColor: data?.color }}>
            <CenteredHandles />
            <span>{data?.label}</span>
        </div>
    );
}

/** Category node: a major theme branching off the root, colored by its branch. */
export function CategoriaNode({ data }) {
    return (
        <div className={styles.categoriaNode} style={{ backgroundColor: data?.color }}>
            <CenteredHandles />
            <span>{data?.label}</span>
        </div>
    );
}

/** Detail node: a leaf entity/fact under a category, tinted with its branch's light color. */
export function DetalheNode({ data }) {
    return (
        <div className={styles.detalheNode} style={{ backgroundColor: data?.color }}>
            <CenteredHandles />
            <span>{data?.label}</span>
        </div>
    );
}
