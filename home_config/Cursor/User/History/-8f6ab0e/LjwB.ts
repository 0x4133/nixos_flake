import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { AppState, Project, Graph, NodeData, Edge, LogEntry } from '../types';
import { v4 as uuidv4 } from 'uuid';

interface AppStore extends AppState {
  // Actions
  setTheme: (theme: 'light' | 'dark') => void;
  createProject: (name: string) => void;
  loadProject: (project: Project) => void;
  updateProject: (updates: Partial<Project>) => void;
  addNode: (node: Omit<NodeData, 'id'>) => string;
  updateNode: (id: string, updates: Partial<NodeData>) => void;
  removeNode: (id: string) => void;
  addEdge: (edge: Omit<Edge, 'id'>) => string;
  removeEdge: (id: string) => void;
  setSelectedNode: (id: string | null) => void;
  setIsRunning: (isRunning: boolean) => void;
  addExecutionLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  clearExecutionLogs: () => void;
  resetProject: () => void;
}

const createDefaultProject = (name: string): Project => ({
  id: uuidv4(),
  name,
  graph: { nodes: [], edges: [] },
  createdAt: new Date(),
  updatedAt: new Date(),
});

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      // Initial state
      currentProject: null,
      theme: 'light',
      selectedNodeId: null,
      isRunning: false,
      executionLogs: [],

      // Actions
      setTheme: (theme) => set({ theme }),

      createProject: (name) => {
        const project = createDefaultProject(name);
        set({ currentProject: project });
      },

      loadProject: (project) => set({ currentProject: project }),

      updateProject: (updates) => {
        const { currentProject } = get();
        if (currentProject) {
          set({
            currentProject: {
              ...currentProject,
              ...updates,
              updatedAt: new Date(),
            },
          });
        }
      },

      addNode: (node) => {
        const id = uuidv4();
        const { currentProject } = get();
        if (currentProject) {
          const newNode: NodeData = {
            ...node,
            id,
            logs: [],
            status: 'idle',
          };
          const updatedGraph: Graph = {
            ...currentProject.graph,
            nodes: [...currentProject.graph.nodes, newNode],
          };
          set({
            currentProject: {
              ...currentProject,
              graph: updatedGraph,
              updatedAt: new Date(),
            },
          });
        }
        return id;
      },

      updateNode: (id, updates) => {
        const { currentProject } = get();
        if (currentProject) {
          const updatedNodes = currentProject.graph.nodes.map((node) =>
            node.id === id ? { ...node, ...updates } : node
          );
          const updatedGraph: Graph = {
            ...currentProject.graph,
            nodes: updatedNodes,
          };
          set({
            currentProject: {
              ...currentProject,
              graph: updatedGraph,
              updatedAt: new Date(),
            },
          });
        }
      },

      removeNode: (id) => {
        const { currentProject } = get();
        if (currentProject) {
          const updatedNodes = currentProject.graph.nodes.filter(
            (node) => node.id !== id
          );
          const updatedEdges = currentProject.graph.edges.filter(
            (edge) => edge.source !== id && edge.target !== id
          );
          const updatedGraph: Graph = {
            nodes: updatedNodes,
            edges: updatedEdges,
          };
          set({
            currentProject: {
              ...currentProject,
              graph: updatedGraph,
              updatedAt: new Date(),
            },
            selectedNodeId: get().selectedNodeId === id ? null : get().selectedNodeId,
          });
        }
      },

      addEdge: (edge) => {
        const id = uuidv4();
        const { currentProject } = get();
        if (currentProject) {
          const newEdge: Edge = { ...edge, id };
          const updatedGraph: Graph = {
            ...currentProject.graph,
            edges: [...currentProject.graph.edges, newEdge],
          };
          set({
            currentProject: {
              ...currentProject,
              graph: updatedGraph,
              updatedAt: new Date(),
            },
          });
        }
        return id;
      },

      removeEdge: (id) => {
        const { currentProject } = get();
        if (currentProject) {
          const updatedEdges = currentProject.graph.edges.filter(
            (edge) => edge.id !== id
          );
          const updatedGraph: Graph = {
            ...currentProject.graph,
            edges: updatedEdges,
          };
          set({
            currentProject: {
              ...currentProject,
              graph: updatedGraph,
              updatedAt: new Date(),
            },
          });
        }
      },

      setSelectedNode: (id) => set({ selectedNodeId: id }),

      setIsRunning: (isRunning) => set({ isRunning }),

      addExecutionLog: (log) => {
        const newLog: LogEntry = {
          ...log,
          id: uuidv4(),
          timestamp: new Date(),
        };
        set((state) => ({
          executionLogs: [...state.executionLogs, newLog],
        }));
      },

      clearExecutionLogs: () => set({ executionLogs: [] }),

      resetProject: () => {
        const { currentProject } = get();
        if (currentProject) {
          const resetGraph: Graph = {
            nodes: currentProject.graph.nodes.map((node) => ({
              ...node,
              status: 'idle',
              output: undefined,
              error: undefined,
              logs: [],
            })),
            edges: currentProject.graph.edges,
          };
          set({
            currentProject: {
              ...currentProject,
              graph: resetGraph,
              updatedAt: new Date(),
            },
            executionLogs: [],
            isRunning: false,
          });
        }
      },
    }),
    {
      name: 'api-caller-storage',
      partialize: (state) => ({
        currentProject: state.currentProject,
        theme: state.theme,
      }),
    }
  )
); 