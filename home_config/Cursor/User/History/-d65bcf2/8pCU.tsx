import React, { useState, useCallback } from 'react';
import ReactFlow, { ReactFlowProvider, useOnViewportChange } from 'reactflow';
import 'reactflow/dist/style.css';
import { TestNode } from './TestNode';

const nodeTypes = {
  test: TestNode,
};

export function MinimalTest() {
  const [nodes, setNodes] = useState([
    {
      id: '1',
      type: 'test',
      position: { x: 250, y: 250 },
      data: {},
    },
  ]);
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
            onKeyDown={(e) => {
              console.log('ReactFlow keydown:', e.key);
              // Only prevent default for specific keys, allow input events
              const target = e.target as HTMLElement;
              const isInputField = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
              
              if (isInputField) {
                // Allow input field events
                return;
              }
              
              // Prevent default for other keys
              e.preventDefault();
            }}
            deleteKeyCode={null}
            multiSelectionKeyCode={null}
            panOnDrag={true}
            panOnScroll={false}
            zoomOnScroll={true}
            zoomOnPinch={true}
            zoomOnDoubleClick={false}
            fitView
          />
        </ReactFlowProvider>
      </div>
    </div>
  );
} 