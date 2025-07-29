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
import { TestInput } from './TestInput';
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
                  onUpdate: (updates: any) => {
                    console.log('onUpdate called for existing node:', node.id, updates);
                    updateNode(node.id, updates);
                  },
                  onDelete: () => {
                    removeNode(node.id);
                    setProjectNodes((nds) => nds.filter(n => n.id !== node.id));
                    setProjectEdges((eds) => eds.filter(e => e.source !== node.id && e.target !== node.id));
                  },
                },
              })) as Node[];

              const edges = currentProject.graph.edges.map(edge => ({
                ...edge,
                type: 'smoothstep',
              })) as Edge[];

              setProjectNodes(nodes);
              setProjectEdges(edges);
            }
          }, [currentProject, setProjectNodes, setProjectEdges, updateNode, removeNode]);

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
    console.log('Drag over event');
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

      const parsedNodeData = JSON.parse(nodeData || '{}');
      
      const newNodeData: Omit<NodeData, 'id'> = {
        type: type as 'api' | 'transform' | 'output',
        position,
        data: parsedNodeData,
        status: 'idle',
        logs: [],
      };

      const newNodeId = addNode(newNodeData);
      
      const newNode: Node = {
        id: newNodeId,
        type,
        position,
        data: {
          ...parsedNodeData,
          onUpdate: (updates: any) => {
            console.log('onUpdate called for node:', newNodeId, updates);
            updateNode(newNodeId, updates);
          },
          onDelete: () => {
            removeNode(newNodeId);
            setProjectNodes((nds) => nds.filter(n => n.id !== newNodeId));
            setProjectEdges((eds) => eds.filter(e => e.source !== newNodeId && e.target !== newNodeId));
          },
        },
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

            // Keyboard shortcuts are now handled in ReactFlow's onKeyDown

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
          <div className="bg-gradient-to-r from-white to-gray-50 border-b border-gray-200 p-6 flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                  <span className="text-white text-lg font-bold">⚡</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
                    {currentProject.name}
                  </h1>
                  <p className="text-sm text-gray-500">
                    {projectNodes.length} nodes • {projectEdges.length} connections
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 flex items-center space-x-2 disabled:opacity-50"
                disabled={isRunning}
              >
                <span className="text-sm">💾</span>
                <span className="font-medium">Save</span>
                <kbd className="text-xs bg-gray-100 px-2 py-1 rounded">⌘S</kbd>
              </button>
              <button
                onClick={handleRunGraph}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2 ${
                  isRunning 
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed' 
                    : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white hover:from-blue-600 hover:to-purple-700 transform hover:scale-105'
                }`}
                disabled={isRunning}
              >
                <span className="text-sm">{isRunning ? '⏳' : '▶️'}</span>
                <span>{isRunning ? 'Running...' : 'Run Graph'}</span>
                {!isRunning && <kbd className="text-xs bg-white/20 px-2 py-1 rounded">⌘R</kbd>}
              </button>
            </div>
          </div>

          {/* Flow Canvas */}
          <div className="flex-1 relative" ref={reactFlowWrapper}>
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
              onKeyDown={(e) => {
                // Only prevent default for specific keys, allow input events
                const target = e.target as HTMLElement;
                const isInputField = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
                
                if (isInputField) {
                  // Allow input field events
                  return;
                }
                
                // Handle our own shortcuts
                if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                  e.preventDefault();
                  handleSave();
                }
                if ((e.metaKey || e.ctrlKey) && e.key === 'r') {
                  e.preventDefault();
                  handleRunGraph();
                }
                if (e.key === 'Delete' || e.key === 'Backspace') {
                  if (selectedNodeId) {
                    e.preventDefault();
                    removeNode(selectedNodeId);
                    setProjectNodes((nds) => nds.filter(n => n.id !== selectedNodeId));
                    setProjectEdges((eds) => eds.filter(e => e.source !== selectedNodeId && e.target !== selectedNodeId));
                    setSelectedNode(null);
                  }
                }
              }}
              preventScrolling={false}
              nodeTypes={nodeTypes}
              fitView
              attributionPosition="bottom-left"
              deleteKeyCode={null}
              multiSelectionKeyCode={null}
              panOnDrag={true}
              panOnScroll={false}
              zoomOnScroll={true}
              zoomOnPinch={true}
              zoomOnDoubleClick={false}
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
      
      {/* Test Input */}
      <div className="fixed top-20 right-4 z-50">
        <TestInput />
      </div>
    </ReactFlowProvider>
  );
} 