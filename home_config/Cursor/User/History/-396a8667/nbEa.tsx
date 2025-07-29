import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeData, ApiNodeData } from '../../types';

interface ApiNodeProps {
  data: NodeData & { data: ApiNodeData; onUpdate?: (updates: any) => void };
  selected: boolean;
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] as const;

export function ApiNode({ data, selected }: ApiNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const { status, output, error } = data;
  const { method, url, headers, body, useCorsProxy } = data.data || {};

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
    <div className={`bg-white border-2 rounded-xl shadow-lg min-w-[280px] ${selected ? 'border-blue-500' : 'border-gray-200'} hover:shadow-xl transition-all duration-300`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-t-xl">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()} shadow-sm`} />
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs">🌐</span>
            </div>
            <span className="font-semibold text-sm text-gray-800">API Call</span>
          </div>
        </div>
        <div className="flex items-center space-x-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-6 h-6 bg-white rounded-lg border border-gray-200 flex items-center justify-center text-gray-500 hover:text-blue-600 hover:border-blue-300 transition-all duration-200 hover:scale-110"
          >
            <span className="text-sm font-bold">{isExpanded ? '−' : '+'}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (data.onDelete) {
                data.onDelete();
              }
            }}
            className="w-6 h-6 bg-white rounded-lg border border-gray-200 flex items-center justify-center text-gray-400 hover:text-red-600 hover:border-red-300 transition-all duration-200 hover:scale-110"
            title="Delete node"
          >
            <span className="text-xs">🗑️</span>
          </button>
        </div>
      </div>

      {/* Method and URL */}
      <div className="p-4">
        <div className="flex items-center space-x-3 mb-3">
          <select
            value={method || 'GET'}
            onChange={(e) => {
              // Update the node data
              if (data.onUpdate) {
                data.onUpdate({ data: { ...data.data, method: e.target.value as any } });
              }
            }}
            className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200"
          >
            {HTTP_METHODS.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <span className="text-xs text-gray-500 font-medium">Method</span>
        </div>
        
        <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
          <div className="text-xs text-gray-500 mb-1 font-medium">URL</div>
          <div className="text-sm text-gray-700 truncate font-mono" title={url || ''}>
            {url || 'Enter URL...'}
          </div>
        </div>
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="p-4 border-t border-gray-100 space-y-4 bg-gray-50">
          {/* URL Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">URL</label>
            <input
              type="text"
              value={url || ''}
              onChange={(e) => {
                if (data.onUpdate) {
                  data.onUpdate({ data: { ...data.data, url: e.target.value } });
                }
              }}
              placeholder="https://api.example.com/endpoint"
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200"
            />
          </div>

          {/* Headers */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Headers</label>
            <textarea
              value={JSON.stringify(headers || {}, null, 2)}
              onChange={(e) => {
                try {
                  const parsedHeaders = JSON.parse(e.target.value);
                  if (data.onUpdate) {
                    data.onUpdate({ data: { ...data.data, headers: parsedHeaders } });
                  }
                } catch (error) {
                  // Invalid JSON, ignore
                }
              }}
              placeholder='{"Content-Type": "application/json"}'
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 h-20 font-mono"
            />
          </div>

          {/* Body */}
          {method !== 'GET' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Body</label>
              <textarea
                value={body || ''}
                onChange={(e) => {
                  if (data.onUpdate) {
                    data.onUpdate({ data: { ...data.data, body: e.target.value } });
                  }
                }}
                placeholder='{"key": "value"}'
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 h-20 font-mono"
              />
            </div>
          )}

          {/* CORS Proxy */}
          <div className="flex items-center space-x-3 p-3 bg-white rounded-lg border border-gray-200">
            <input
              type="checkbox"
              checked={useCorsProxy || false}
              onChange={(e) => {
                if (data.onUpdate) {
                  data.onUpdate({ data: { ...data.data, useCorsProxy: e.target.checked } });
                }
              }}
              className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 focus:ring-2"
            />
            <label className="text-sm text-gray-700 font-medium">Use CORS Proxy</label>
          </div>
        </div>
      )}

      {/* Status and output preview */}
      {status === 'success' && output && (
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-gray-600 mb-1">Response:</div>
          <div className="text-xs bg-gray-100 p-2 rounded max-h-20 overflow-y-auto">
            {JSON.stringify(output.data || output, null, 2).substring(0, 100)}
            {JSON.stringify(output.data || output).length > 100 && '...'}
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