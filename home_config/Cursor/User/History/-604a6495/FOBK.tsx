import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeData, TransformNodeData } from '../../types';

interface TransformNodeProps {
  data: NodeData & { data: TransformNodeData; onUpdate?: (updates: any) => void };
  selected: boolean;
}

export function TransformNode({ data, selected }: TransformNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { status, output, error } = data;
  const { expression } = data.data || {};

  const getStatusColor = () => {
    switch (status) {
      case 'idle': return 'bg-gray-400';
      case 'running': return 'bg-yellow-400';
      case 'success': return 'bg-green-400';
      case 'error': return 'bg-red-400';
      default: return 'bg-gray-400';
    }
  };

  return (
    <div className={`bg-white border-2 rounded-lg shadow-lg min-w-[200px] ${selected ? 'border-blue-500' : 'border-gray-300'}`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="font-semibold text-sm">Transform</span>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-500 hover:text-gray-700"
        >
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {/* Expression preview */}
      <div className="p-3">
        <div className="text-xs text-gray-600 truncate" title={expression}>
          {expression || 'Enter JavaScript expression...'}
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-3 border-t border-gray-200 space-y-3">
          {/* Expression Input */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">JavaScript Expression</label>
            <textarea
              value={expression}
              onChange={(e) => {
                if (data.onUpdate) {
                  data.onUpdate({ data: { ...data.data, expression: e.target.value } });
                }
              }}
              placeholder="_.map(data, item => item.name)"
              className="w-full px-2 py-1 text-xs border border-gray-300 rounded h-24 font-mono"
            />
            <div className="text-xs text-gray-500 mt-1">
              Available: <code>data</code> (input), <code>_</code> (lodash/fp), <code>Math</code>, <code>JSON</code>, etc.
            </div>
          </div>

          {/* Examples */}
          <div>
            <div className="text-xs font-medium text-gray-700 mb-1">Examples:</div>
            <div className="text-xs text-gray-600 space-y-1">
              <div><code>_.map(data, item =&gt; item.name)</code></div>
              <div><code>_.filter(data, item =&gt; item.active)</code></div>
              <div><code>data.map(item =&gt; (&#123; ...item, processed: true &#125;))</code></div>
            </div>
          </div>
        </div>
      )}

      {/* Status and output preview */}
      {status === 'success' && output && (
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-1">Result:</div>
          <div className="text-xs bg-gray-100 p-2 rounded max-h-20 overflow-y-auto">
            {JSON.stringify(output, null, 2).substring(0, 100)}
            {JSON.stringify(output).length > 100 && '...'}
          </div>
        </div>
      )}

      {status === 'error' && error && (
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-red-600 mb-1">Error:</div>
          <div className="text-xs bg-red-50 p-2 rounded text-red-700">
            {error.substring(0, 100)}
            {error.length > 100 && '...'}
          </div>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
} 