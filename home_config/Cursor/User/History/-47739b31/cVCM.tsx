import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';

export function TestNode({ data }: any) {
  const [inputValue, setInputValue] = useState('');

  return (
    <div className="bg-white border-2 border-gray-300 rounded-lg p-4 min-w-[200px]">
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="mb-3">
        <h3 className="font-bold text-sm">Test Node</h3>
      </div>
      
      <div className="space-y-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => {
            console.log('Test node input changed:', e.target.value);
            setInputValue(e.target.value);
          }}
          onMouseDown={(e) => {
            console.log('Test node input mousedown');
            e.stopPropagation();
          }}
          onClick={(e) => {
            console.log('Test node input clicked');
            e.stopPropagation();
          }}
          onKeyDown={(e) => {
            console.log('Test node input keydown:', e.key);
            e.stopPropagation();
          }}
          placeholder="Type in this input..."
          className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          style={{ position: 'relative', zIndex: 1000 }}
        />
        <p className="text-xs text-gray-600">Value: {inputValue}</p>
      </div>
      
      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
} 