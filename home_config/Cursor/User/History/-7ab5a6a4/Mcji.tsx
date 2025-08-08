import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import Editor from '@monaco-editor/react';
import type { NodeData, OutputNodeData } from '../../types';

interface OutputNodeProps {
  data: NodeData & { data: OutputNodeData; onUpdate?: (updates: any) => void };
  selected: boolean;
}

export function OutputNode({ data, selected }: OutputNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { status, output, error } = data;

  const getStatusColor = () => {
    switch (status) {
      case 'idle': return 'bg-gray-400';
      case 'running': return 'bg-yellow-400';
      case 'success': return 'bg-green-400';
      case 'error': return 'bg-red-400';
      default: return 'bg-gray-400';
    }
  };

  const formatOutput = (data: any) => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  };

  return (
    <div className={`bg-white border-2 rounded-lg shadow-lg min-w-[300px] ${selected ? 'border-blue-500' : 'border-gray-300'}`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="font-semibold text-sm">Output</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-500 hover:text-gray-700"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Status preview */}
      <div className="p-3">
        <div className="text-xs text-gray-600">
          {status === 'idle' && 'Waiting for input...'}
          {status === 'running' && 'Processing...'}
          {status === 'success' && 'Data received'}
          {status === 'error' && 'Error occurred'}
        </div>
      </div>

      {/* Expanded content with Monaco editor */}
      {isExpanded && (
        <div className="border-t border-gray-200">
          {status === 'success' && output ? (
            <div className="h-64">
              <Editor
                height="100%"
                defaultLanguage="json"
                value={formatOutput(output)}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 12,
                  lineNumbers: 'on',
                  wordWrap: 'on',
                }}
                theme="vs-light"
              />
            </div>
          ) : status === 'error' && error ? (
            <div className="p-3">
              <div className="text-xs text-red-600 mb-2">Error:</div>
              <div className="text-xs bg-red-50 p-3 rounded text-red-700 font-mono">
                {error}
              </div>
            </div>
          ) : (
            <div className="p-3 text-center text-gray-500 text-sm">
              No data available
            </div>
          )}
        </div>
      )}

      {/* Collapsed output preview */}
      {!isExpanded && status === 'success' && output && (
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-1">Preview:</div>
          <div className="text-xs bg-gray-100 p-2 rounded max-h-20 overflow-y-auto font-mono">
            {formatOutput(output).substring(0, 150)}
            {formatOutput(output).length > 150 && '...'}
          </div>
        </div>
      )}

      {!isExpanded && status === 'error' && error && (
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-red-600 mb-1">Error:</div>
          <div className="text-xs bg-red-50 p-2 rounded text-red-700">
            {error.substring(0, 100)}
            {error.length > 100 && '...'}
          </div>
        </div>
      )}
    </div>
  );
} 