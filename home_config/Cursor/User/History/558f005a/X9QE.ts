export interface NodeData {
  id: string;
  type: 'api' | 'transform' | 'output';
  position: { x: number; y: number };
  data: ApiNodeData | TransformNodeData | OutputNodeData;
  status: NodeStatus;
  output?: any;
  error?: string;
  logs: LogEntry[];
}

export interface ApiNodeData {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  headers: Record<string, string>;
  body: string;
  useCorsProxy: boolean;
}

export interface TransformNodeData {
  expression: string;
}

export interface OutputNodeData {
  // No additional data needed for output nodes
}

export type NodeStatus = 'idle' | 'running' | 'success' | 'error';

export interface LogEntry {
  id: string;
  timestamp: Date;
  level: 'info' | 'warn' | 'error';
  message: string;
  data?: any;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface Graph {
  nodes: NodeData[];
  edges: Edge[];
}

export interface ExecutionContext {
  nodeOutputs: Record<string, any>;
  nodeErrors: Record<string, string>;
  nodeStatuses: Record<string, NodeStatus>;
}

export interface Project {
  id: string;
  name: string;
  graph: Graph;
  createdAt: Date;
  updatedAt: Date;
}

export interface AppState {
  currentProject: Project | null;
  theme: 'light' | 'dark';
  selectedNodeId: string | null;
  isRunning: boolean;
  executionLogs: LogEntry[];
}

export interface SafeEvalContext {
  _: any; // lodash/fp
  data: any;
  Math: typeof Math;
  JSON: typeof JSON;
  Array: typeof Array;
  Object: typeof Object;
  String: typeof String;
  Number: typeof Number;
  Boolean: typeof Boolean;
  Date: typeof Date;
  RegExp: typeof RegExp;
} 