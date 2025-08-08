import React, { useState } from 'react';
import { useAppStore } from '../store';

export function ExecutionPanel() {
  const { executionLogs, clearExecutionLogs, theme } = useAppStore();
  const [showCopyButton, setShowCopyButton] = useState(false);

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

  const formatLogForAI = (logs: any[]) => {
    return logs.map(log => {
      const timestamp = log.timestamp.toLocaleString();
      const level = log.level.toUpperCase();
      const message = log.message;
      const data = log.data ? `\nData: ${JSON.stringify(log.data, null, 2)}` : '';
      
      return `[${timestamp}] ${level}: ${message}${data}`;
    }).join('\n\n');
  };

  const copyLogsToClipboard = async () => {
    const formattedLogs = formatLogForAI(executionLogs);
    try {
      await navigator.clipboard.writeText(formattedLogs);
      setShowCopyButton(true);
      setTimeout(() => setShowCopyButton(false), 2000);
    } catch (err) {
      console.error('Failed to copy logs:', err);
    }
  };

  return (
    <div className="w-80 bg-gradient-to-b from-white to-gray-50 border-l border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-sm">📋</span>
            </div>
            <h2 className="text-lg font-bold text-gray-800">Execution Logs</h2>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={copyLogsToClipboard}
              className="px-3 py-1 text-sm text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all duration-200 flex items-center space-x-1"
              title="Copy logs for AI analysis"
            >
              <span>{showCopyButton ? '✅' : '📋'}</span>
              <span>{showCopyButton ? 'Copied!' : 'Copy'}</span>
            </button>
            <button
              onClick={clearExecutionLogs}
              className="px-3 py-1 text-sm text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-all duration-200"
            >
              Clear
            </button>
          </div>
        </div>
        <div className="text-xs text-gray-500">
          Real-time execution feedback and debugging
        </div>
      </div>

      {/* Logs */}
      <div className="flex-1 overflow-y-auto p-6">
        {executionLogs.length === 0 ? (
          <div className="text-center text-gray-500 py-12">
            <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">📋</span>
            </div>
            <p className="text-lg font-medium mb-2">No execution logs yet</p>
            <p className="text-sm text-gray-400">Run your graph to see logs here</p>
          </div>
        ) : (
          <div className="space-y-4">
            {executionLogs.map((log) => (
              <div
                key={log.id}
                className="bg-white rounded-xl p-4 border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <div className="flex items-start space-x-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getLogLevelColor(log.level).replace('text-', 'bg-').replace('-600', '-100')}`}>
                    <span className="text-sm">{getLogLevelIcon(log.level)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-sm font-semibold ${getLogLevelColor(log.level)}`}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
                        {log.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-gray-800 mb-3 leading-relaxed">{log.message}</p>
                    {log.data && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-gray-600 hover:text-blue-600 font-medium transition-colors">
                          View Details
                        </summary>
                        <div className="mt-3 space-y-2">
                          <pre className="p-3 bg-gray-50 rounded-lg text-xs overflow-x-auto border border-gray-200 font-mono">
                            {JSON.stringify(log.data, null, 2)}
                          </pre>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(JSON.stringify(log.data, null, 2));
                            }}
                            className="w-full px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                          >
                            📋 Copy Data
                          </button>
                        </div>
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
      <div className="p-4 border-t border-gray-200 bg-gradient-to-r from-gray-50 to-white">
        <div className="text-xs text-gray-600">
          <div className="flex items-center justify-between mb-2 p-2 bg-white rounded-lg border border-gray-200">
            <span className="font-medium">Total Logs:</span>
            <span className="font-bold text-blue-600">{executionLogs.length}</span>
          </div>
          <div className="flex items-center justify-between p-2 bg-white rounded-lg border border-gray-200">
            <span className="font-medium">Errors:</span>
            <span className="font-bold text-red-600">
              {executionLogs.filter(log => log.level === 'error').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
} 