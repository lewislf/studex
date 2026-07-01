import ReactFlow from "reactflow";
import "reactflow/dist/style.css";

const nodes = [
  {
    id: "1",
    data: { label: "React" },
    position: { x: 250, y: 0 },
  },
  {
    id: "2",
    data: { label: "Componentes" },
    position: { x: 100, y: 150 },
  },
  {
    id: "3",
    data: { label: "Hooks" },
    position: { x: 400, y: 150 },
  },
  {
    id: "4",
    data: { label: "useState" },
    position: { x: 350, y: 300 },
  },
  {
    id: "5",
    data: { label: "useEffect" },
    position: { x: 500, y: 300 },
  },
];

const edges = [
  { id: "e1-2", source: "1", target: "2" },
  { id: "e1-3", source: "1", target: "3" },
  { id: "e3-4", source: "3", target: "4" },
  { id: "e3-5", source: "3", target: "5" },
];

function App() {
  return (
    <div style={{ width: "100vw", height: "100vh" }}>
      <ReactFlow nodes={nodes} edges={edges} fitView />
    </div>
  );
}

export default App;