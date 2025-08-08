import type { Graph, NodeData, Edge, ExecutionContext, NodeStatus, LogEntry } from '../types';
import { executeApiNode, executeTransformNode, executeOutputNode } from './nodes';
import { interpolateVariables } from './interpolation';

export function detectCycles(graph: Graph): string[] {
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const cycles: string[] = [];

  function dfs(nodeId: string, path: string[] = []): boolean {
    if (recursionStack.has(nodeId)) {
      const cycleStart = path.indexOf(nodeId);
      cycles.push(...path.slice(cycleStart));
      return true;
    }

    if (visited.has(nodeId)) {
      return false;
    }

    visited.add(nodeId);
    recursionStack.add(nodeId);

    const outgoingEdges = graph.edges.filter(edge => edge.source === nodeId);
    for (const edge of outgoingEdges) {
      if (dfs(edge.target, [...path, nodeId])) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  }

  for (const node of graph.nodes) {
    if (!visited.has(node.id)) {
      dfs(node.id);
    }
  }

  return cycles;
}

export function topologicalSort(graph: Graph): string[] {
  const inDegree: Record<string, number> = {};
  const adjacencyList: Record<string, string[]> = {};

  // Initialize
  for (const node of graph.nodes) {
    inDegree[node.id] = 0;
    adjacencyList[node.id] = [];
  }

  // Build adjacency list and calculate in-degrees
  for (const edge of graph.edges) {
    adjacencyList[edge.source].push(edge.target);
    inDegree[edge.target]++;
  }

  // Kahn's algorithm
  const queue: string[] = [];
  const result: string[] = [];

  // Add nodes with no incoming edges
  for (const node of graph.nodes) {
    if (inDegree[node.id] === 0) {
      queue.push(node.id);
    }
  }

  while (queue.length > 0) {
    const current = queue.shift()!;
    result.push(current);

    for (const neighbor of adjacencyList[current]) {
      inDegree[neighbor]--;
      if (inDegree[neighbor] === 0) {
        queue.push(neighbor);
      }
    }
  }

  // Check if all nodes were processed
  if (result.length !== graph.nodes.length) {
    throw new Error('Graph contains cycles');
  }

  return result;
}

export async function executeGraph(
  graph: Graph,
  onNodeUpdate: (nodeId: string, status: NodeStatus, output?: any, error?: string) => void,
  onLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void
): Promise<ExecutionContext> {
  // Detect cycles
  const cycles = detectCycles(graph);
  if (cycles.length > 0) {
    throw new Error(`Graph contains cycles: ${cycles.join(' -> ')}`);
  }

  // Topological sort
  const executionOrder = topologicalSort(graph);

  const context: ExecutionContext = {
    nodeOutputs: {},
    nodeErrors: {},
    nodeStatuses: {},
  };

  onLog({
    level: 'info',
    message: `Starting execution of ${graph.nodes.length} nodes in order: ${executionOrder.join(', ')}`,
  });

  for (const nodeId of executionOrder) {
    const node = graph.nodes.find(n => n.id === nodeId);
    if (!node) continue;

    try {
      onNodeUpdate(nodeId, 'running');
      context.nodeStatuses[nodeId] = 'running';

      onLog({
        level: 'info',
        message: `Executing node: ${nodeId} (${node.type})`,
      });

      let output: any;

      switch (node.type) {
        case 'api':
          output = await executeApiNode(node, context, onLog);
          break;
        case 'transform':
          output = await executeTransformNode(node, context, onLog);
          break;
        case 'output':
          output = await executeOutputNode(node, context, onLog);
          break;
        default:
          throw new Error(`Unknown node type: ${(node as any).type}`);
      }

      context.nodeOutputs[nodeId] = output;
      context.nodeStatuses[nodeId] = 'success';
      onNodeUpdate(nodeId, 'success', output);

      onLog({
        level: 'info',
        message: `Node ${nodeId} completed successfully`,
        data: output,
      });

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      context.nodeErrors[nodeId] = errorMessage;
      context.nodeStatuses[nodeId] = 'error';
      onNodeUpdate(nodeId, 'error', undefined, errorMessage);

      onLog({
        level: 'error',
        message: `Node ${nodeId} failed: ${errorMessage}`,
        data: error,
      });

      // Continue execution for other nodes
    }
  }

  onLog({
    level: 'info',
    message: 'Graph execution completed',
    data: {
      successful: Object.values(context.nodeStatuses).filter(s => s === 'success').length,
      failed: Object.values(context.nodeStatuses).filter(s => s === 'error').length,
      total: graph.nodes.length,
    },
  });

  return context;
}

export function getNodeDependencies(nodeId: string, graph: Graph): string[] {
  return graph.edges
    .filter(edge => edge.target === nodeId)
    .map(edge => edge.source);
}

export function getNodeDependents(nodeId: string, graph: Graph): string[] {
  return graph.edges
    .filter(edge => edge.source === nodeId)
    .map(edge => edge.target);
} 