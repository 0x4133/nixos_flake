import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  ReactFlowProvider,
} from 'reactflow';
import type { Node, Edge, Connection, NodeTypes } from 'reactflow';
import 'reactflow/dist/style.css';

import { ApiNode } from './nodes/ApiNode';
import { TransformNode } from './nodes/TransformNode';
import { OutputNode } from './nodes/OutputNode';
import { NodePalette } from './NodePalette';
import { ExecutionPanel } from './ExecutionPanel';
import { useAppStore } from '../store';
import { executeGraph } from '../utils/execution';
import type { NodeData, Edge as EdgeType } from '../types';

const nodeTypes: NodeTypes = {
  api: ApiNode,
  transform: TransformNode,
  output: OutputNode,
};

export function Flow() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);
  const [projectNodes, setProjectNodes, onNodesChange] = useNodesState([]);
  const [projectEdges, setProjectEdges, onEdgesChange] = useEdgesState([]);

  const {
    currentProject,
    selectedNodeId,
    isRunning,
    executionLogs,
    setSelectedNode,
    setIsRunning,
    addExecutionLog,
    clearExecutionLogs,
    resetProject,
    updateNode,
    addNode,
    addEdge,
    removeNode,
    removeEdge,
  } = useAppStore();

  // Initialize nodes and edges from project
  React.useEffect(() => {
    if (currentProject) {
      const nodes = currentProject.graph.nodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          onUpdate: (updates: any) => updateNode(node.id, updates),
        },
      })) as Node[];
      
      const edges = currentProject.graph.edges.map(edge => ({
        ...edge,
        type: 'smoothstep',
      })) as Edge[];
      
      setProjectNodes(nodes);
      setProjectEdges(edges);
    }
  }, [currentProject, setProjectNodes, setProjectEdges, updateNode]);

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge: EdgeType = {
        id: `${params.source}-${params.target}`,
        source: params.source!,
        target: params.target!,
        sourceHandle: params.sourceHandle || undefined,
        targetHandle: params.targetHandle || undefined,
      };
      
      addEdge(newEdge);
      setProjectEdges((eds) => [...eds, { 
        id: newEdge.id, 
        source: newEdge.source, 
        target: newEdge.target,
        type: 'smoothstep',
      } as Edge]);
    },
    [addEdge, setProjectEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      console.log('Drop event triggered');

      if (!reactFlowWrapper.current || !reactFlowInstance) {
        console.log('Missing reactFlowWrapper or reactFlowInstance');
        return;
      }

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');
      const nodeData = event.dataTransfer.getData('application/nodedata');

      console.log('Drop data:', { type, nodeData });

      if (!type) {
        console.log('No type found in drop data');
        return;
      }

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const newNodeData: Omit<NodeData, 'id'> = {
        type: type as 'api' | 'transform' | 'output',
        position,
        data: JSON.parse(nodeData || '{}'),
        status: 'idle',
        logs: [],
      };

      const newNodeId = addNode(newNodeData);
      
      const newNode: Node = {
        id: newNodeId,
        type,
        position,
        data: newNodeData,
      };

      setProjectNodes((nds) => [...nds, newNode]);
    },
    [reactFlowInstance, addNode, setProjectNodes]
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node.id);
  }, [setSelectedNode]);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, [setSelectedNode]);

  const handleRunGraph = useCallback(async () => {
    if (!currentProject || isRunning) return;

    setIsRunning(true);
    clearExecutionLogs();
    resetProject();

    try {
      await executeGraph(
        currentProject.graph,
        (nodeId, status, output, error) => {
          updateNode(nodeId, { status, output, error });
        },
        addExecutionLog
      );
    } catch (error) {
      addExecutionLog({
        level: 'error',
        message: `Graph execution failed: ${error instanceof Error ? error.message : String(error)}`,
        data: error,
      });
    } finally {
      setIsRunning(false);
    }
  }, [currentProject, isRunning, setIsRunning, clearExecutionLogs, resetProject, updateNode, addExecutionLog]);

  const handleSave = useCallback(() => {
    // Save is handled automatically by Zustand persistence
    addExecutionLog({
      level: 'info',
      message: 'Project saved automatically',
    });
  }, [addExecutionLog]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault();
        handleSave();
      }
      if ((event.metaKey || event.ctrlKey) && event.key === 'r') {
        event.preventDefault();
        handleRunGraph();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleRunGraph]);

  if (!currentProject) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">No Project Loaded</h2>
          <p className="text-gray-600">Create a new project to get started</p>
        </div>
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className="h-screen flex">
        {/* Node Palette */}
        <NodePalette />

        {/* Main Flow Area */}
        <div className="flex-1 flex flex-col">
          {/* Toolbar */}
          <div className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold">{currentProject.name}</h1>
              <div className="text-sm text-gray-500">
                {projectNodes.length} nodes, {projectEdges.length} connections
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSave}
                className="btn btn-sm btn-outline"
                disabled={isRunning}
              >
                Save (⌘S)
              </button>
              <button
                onClick={handleRunGraph}
                className={`btn btn-sm ${isRunning ? 'btn-disabled' : 'btn-primary'}`}
                disabled={isRunning}
              >
                {isRunning ? 'Running...' : 'Run Graph (⌘R)'}
              </button>
            </div>
          </div>

          {/* Flow Canvas */}
          <div className="flex-1" ref={reactFlowWrapper}>
            <ReactFlow
              nodes={projectNodes}
              edges={projectEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onInit={setReactFlowInstance}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onNodeClick={onNodeClick}
              onPaneClick={onPaneClick}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
            >
              <Controls />
              <MiniMap />
              <Background gap={12} size={1} color="#e5e7eb" />
            </ReactFlow>
          </div>
        </div>

        {/* Execution Panel */}
        <ExecutionPanel />
      </div>
    </ReactFlowProvider>
  );
} 