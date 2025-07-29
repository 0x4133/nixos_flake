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
    <div className="w-72 bg-gradient-to-b from-gray-50 to-gray-100 border-r border-gray-200 p-6 overflow-y-auto animate-slide-in">
      <div className="mb-8">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">⚡</span>
          </div>
          <h2 className="text-xl font-bold bg-gradient-to-r from-gray-800 to-gray-600 bg-clip-text text-transparent">
            Node Palette
          </h2>
        </div>
        <p className="text-sm text-gray-600 leading-relaxed">
          Drag nodes to the canvas to build your API workflow
        </p>
      </div>

      <div className="space-y-4">
        {nodeTypes.map((node, index) => (
          <div
            key={node.type}
            className="group bg-white border border-gray-200 rounded-xl p-5 cursor-move hover:shadow-xl hover:border-blue-300 transition-all duration-300 transform hover:-translate-y-1 animate-fade-in"
            style={{ animationDelay: `${index * 100}ms` }}
            draggable
            onDragStart={(e) => onDragStart(e, node.type, node.defaultData)}
          >
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-br from-blue-50 to-purple-50 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                <span className="text-2xl">{node.icon}</span>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-gray-800 group-hover:text-blue-600 transition-colors">
                  {node.label}
                </h3>
                <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                  {node.description}
                </p>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="text-xs text-gray-500 font-medium">
                Drag to canvas →
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-5 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-xl">
        <div className="flex items-center space-x-2 mb-3">
          <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center">
            <span className="text-white text-xs">💡</span>
          </div>
          <h3 className="font-semibold text-blue-800">Quick Tips</h3>
        </div>
        <ul className="text-sm text-blue-700 space-y-2">
          <li className="flex items-start space-x-2">
            <span className="text-blue-500 mt-1">•</span>
            <span>Connect nodes by dragging from output to input</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-500 mt-1">•</span>
            <span>Use <code className="bg-blue-100 px-1 rounded">&#123;&#123;variable&#125;&#125;</code> syntax in API calls</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-500 mt-1">•</span>
            <span>Transform nodes support lodash/fp functions</span>
          </li>
          <li className="flex items-start space-x-2">
            <span className="text-blue-500 mt-1">•</span>
            <span>Press <kbd className="bg-blue-100 px-2 py-1 rounded text-xs">⌘R</kbd> to run the entire graph</span>
          </li>
        </ul>
      </div>
    </div>
  );
} 