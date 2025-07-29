import React from 'react';
import type { ApiNodeData, TransformNodeData, OutputNodeData } from '../types';

const nodeTypes = [
  {
    type: 'api',
    label: 'API Call',
    description: 'Make HTTP requests to APIs',
    icon: '🌐',
    defaultData: {
      method: 'GET' as const,
      url: '',
      headers: {},
      body: '',
      useCorsProxy: false,
    } as ApiNodeData,
  },
  {
    type: 'transform',
    label: 'Transform',
    description: 'Transform data with JavaScript',
    icon: '⚙️',
    defaultData: {
      expression: '',
    } as TransformNodeData,
  },
  {
    type: 'output',
    label: 'Output',
    description: 'Display final results',
    icon: '📊',
    defaultData: {} as OutputNodeData,
  },
];

export function NodePalette() {
  const onDragStart = (event: React.DragEvent, nodeType: string, nodeData: any) => {
    console.log('Drag started:', nodeType, nodeData);
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/nodedata', JSON.stringify(nodeData));
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setDragImage(event.currentTarget, 0, 0);
  };

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 p-4 overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Node Palette</h2>
        <p className="text-sm text-gray-600">
          Drag nodes to the canvas to build your API workflow
        </p>
      </div>

      <div className="space-y-3">
        {nodeTypes.map((node) => (
          <div
            key={node.type}
            className="bg-white border border-gray-200 rounded-lg p-4 cursor-move hover:shadow-md transition-shadow"
            draggable
            onDragStart={(e) => onDragStart(e, node.type, node.defaultData)}
          >
            <div className="flex items-center space-x-3">
              <span className="text-2xl">{node.icon}</span>
              <div className="flex-1">
                <h3 className="font-medium text-gray-800">{node.label}</h3>
                <p className="text-sm text-gray-600">{node.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="font-medium text-blue-800 mb-2">💡 Tips</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Connect nodes by dragging from output to input</li>
          <li>• Use &#123;&#123;variable&#125;&#125; syntax in API calls</li>
          <li>• Transform nodes support lodash/fp functions</li>
          <li>• Press ⌘R to run the entire graph</li>
        </ul>
      </div>
    </div>
  );
} 