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

export const KIND_COLOR: Record<string, string> = {
  class: '#6366f1',
  interface: '#14b8a6',
  enum: '#f59e0b',
  record: '#ec4899',
  method: '#475569',
  constructor: '#64748b',
}

export const EDGE_COLOR: Record<string, string> = {
  extends: '#a78bfa',
  implements: '#2dd4bf',
  calls: '#60a5fa',
  instantiates: '#fbbf24',
}

const UPSTREAM = '#f97316' // things that depend on the selected node
const DOWNSTREAM = '#22d3ee' // things the selected node depends on

interface Props {
  data: GraphData
  selectedId: string | null
  matchIds: Set<string> | null
  onSelect: (id: string | null) => void
}

function layout(data: GraphData): Map<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'LR', nodesep: 20, ranksep: 90 })
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
  const positions = useMemo(() => layout(data), [data])

  // Direct neighbours of the selected node.
  const { upstream, downstream } = useMemo(() => {
    const up = new Set<string>()
    const down = new Set<string>()
    if (selectedId) {
      data.edges.forEach((e) => {
        if (e.target === selectedId) up.add(e.source)
        if (e.source === selectedId) down.add(e.target)
      })
    }
    return { upstream: up, downstream: down }
  }, [data, selectedId])

  const nodes: Node[] = useMemo(
    () =>
      data.nodes.map((n) => {
        let opacity = 1
        let border = '1px solid #1e293b'
        if (selectedId) {
          if (n.id === selectedId) border = '2px solid #f8fafc'
          else if (upstream.has(n.id)) border = `2px solid ${UPSTREAM}`
          else if (downstream.has(n.id)) border = `2px solid ${DOWNSTREAM}`
          else opacity = 0.15
        } else if (matchIds !== null && !matchIds.has(n.id)) {
          opacity = 0.2
        }
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
            border,
            borderRadius: 6,
            opacity,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          },
        }
      }),
    [data, positions, selectedId, upstream, downstream, matchIds],
  )

  const edges: Edge[] = useMemo(
    () =>
      data.edges.map((e, i) => {
        const kind = e.kinds[0] ?? 'calls'
        const touches = e.source === selectedId || e.target === selectedId
        const dim = selectedId !== null && !touches
        const color = touches
          ? e.target === selectedId
            ? UPSTREAM
            : DOWNSTREAM
          : (EDGE_COLOR[kind] ?? '#475569')
        return {
          id: `${e.source}->${e.target}-${i}`,
          source: e.source,
          target: e.target,
          animated: touches,
          label: touches ? e.kinds.join(', ') : undefined,
          labelStyle: { fill: '#e2e8f0', fontSize: 11 },
          labelBgStyle: { fill: '#0f172a' },
          style: {
            stroke: color,
            strokeWidth: touches ? 2.5 : 1.2,
            opacity: dim ? 0.06 : 1,
            strokeDasharray: e.status === 'resolved' ? undefined : '4 3',
          },
          markerEnd: { type: 'arrowclosed' as const, color },
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
