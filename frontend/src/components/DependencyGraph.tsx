import { useMemo } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from '@dagrejs/dagre'
import type { GraphData } from '../types/analysis'

const NODE_W = 220
const NODE_H = 40

const KIND_COLOR: Record<string, string> = {
  class: '#6366f1',
  interface: '#14b8a6',
  enum: '#f59e0b',
  record: '#ec4899',
  method: '#475569',
  constructor: '#64748b',
}

interface Props {
  data: GraphData
  selectedId: string | null
  matchIds: Set<string> | null
  onSelect: (id: string | null) => void
}

function layout(data: GraphData): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 20, ranksep: 80 })
  g.setDefaultEdgeLabel(() => ({}))
  data.nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }))
  data.edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  const pos = new Map<string, { x: number; y: number }>()
  data.nodes.forEach((n) => {
    const p = g.node(n.id)
    pos.set(n.id, { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 })
  })
  return pos
}

export default function DependencyGraph({ data, selectedId, matchIds, onSelect }: Props) {
  // Layout only depends on the data, so it is not recomputed on selection or search.
  const positions = useMemo(() => layout(data), [data])

  const nodes: Node[] = useMemo(
    () =>
      data.nodes.map((n) => {
        const dimmed = matchIds !== null && !matchIds.has(n.id)
        return {
          id: n.id,
          position: positions.get(n.id) ?? { x: 0, y: 0 },
          data: { label: n.label },
          style: {
            width: NODE_W,
            height: NODE_H,
            fontSize: 12,
            color: '#f1f5f9',
            background: KIND_COLOR[n.kind] ?? '#475569',
            border: n.id === selectedId ? '2px solid #f8fafc' : '1px solid #1e293b',
            borderRadius: 6,
            opacity: dimmed ? 0.2 : 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          },
        }
      }),
    [data, positions, selectedId, matchIds],
  )

  const edges: Edge[] = useMemo(
    () =>
      data.edges.map((e, i) => {
        const touches = e.source === selectedId || e.target === selectedId
        return {
          id: `${e.source}->${e.target}-${i}`,
          source: e.source,
          target: e.target,
          animated: touches,
          style: {
            stroke: touches ? '#f8fafc' : '#475569',
            strokeDasharray: e.status === 'resolved' ? undefined : '4 3',
          },
        }
      }),
    [data, selectedId],
  )

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      colorMode="dark"
      fitView
      minZoom={0.05}
      nodesDraggable={false}
      nodesConnectable={false}
      onNodeClick={(_, node) => onSelect(node.id)}
      onPaneClick={() => onSelect(null)}
    >
      <Background />
      <Controls showInteractive={false} />
      <MiniMap pannable zoomable />
    </ReactFlow>
  )
}
