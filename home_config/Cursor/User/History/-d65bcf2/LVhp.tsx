import React, { useState } from 'react';
import ReactFlow, { ReactFlowProvider } from 'reactflow';
import 'reactflow/dist/style.css';

const nodeTypes = {};

export function MinimalTest() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [inputValue, setInputValue] = useState('');

  return (
    <div className="h-screen flex">
      {/* Simple input outside ReactFlow */}
      <div className="w-64 p-4 bg-gray-100">
        <h3 className="font-bold mb-4">Input Test</h3>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            console.log('Input changed:', e.target.value);
            setInputValue(e.target.value);
          }}
          placeholder="Type here..."
          className="w-full p-2 border rounded"
        />
        <p className="mt-2 text-sm">Value: {inputValue}</p>
      </div>

      {/* ReactFlow with minimal config */}
      <div className="flex-1">
        <ReactFlowProvider>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={() => {}}
            onEdgesChange={() => {}}
            onConnect={() => {}}
            fitView
          />
        </ReactFlowProvider>
      </div>
    </div>
  );
} 