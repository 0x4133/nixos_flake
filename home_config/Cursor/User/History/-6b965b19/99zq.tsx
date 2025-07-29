import React from 'react';
import { useAppStore } from '../store';

export function ExecutionPanel() {
  const { executionLogs, clearExecutionLogs, theme } = useAppStore();

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'info': return 'text-blue-600';
      case 'warn': return 'text-yellow-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'info': return 'ℹ️';
      case 'warn': return '⚠️';
      case 'error': return '❌';
      default: return '📝';
    }
  };

  return (
    <div className="w-80 bg-white border-l border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Execution Logs</h2>
        <button
          onClick={clearExecutionLogs}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          Clear
        </button>
      </div>

      {/* Logs */}
      <div className="flex-1 overflow-y-auto p-4">
        {executionLogs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <div className="text-4xl mb-2">📋</div>
            <p>No execution logs yet</p>
            <p className="text-sm">Run your graph to see logs here</p>
          </div>
        ) : (
          <div className="space-y-3">
            {executionLogs.map((log) => (
              <div
                key={log.id}
                className="bg-gray-50 rounded-lg p-3 border border-gray-200"
              >
                <div className="flex items-start space-x-2">
                  <span className="text-sm">{getLogLevelIcon(log.level)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-sm font-medium ${getLogLevelColor(log.level)}`}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">
                        {log.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-800 mb-2">{log.message}</p>
                    {log.data && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-gray-600 hover:text-gray-800">
                          View Details
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-x-auto">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-600">
          <div className="flex items-center justify-between mb-1">
            <span>Total Logs:</span>
            <span className="font-medium">{executionLogs.length}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Errors:</span>
            <span className="font-medium text-red-600">
              {executionLogs.filter(log => log.level === 'error').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
} 