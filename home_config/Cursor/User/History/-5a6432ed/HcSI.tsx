import React, { useState } from 'react';

export function TestInput() {
  const [value, setValue] = useState('');

  return (
    <div className="p-4 bg-white border rounded-lg shadow-lg">
      <h3 className="text-lg font-bold mb-4">Test Input</h3>
      <input
        type="text"
        value={value}
        onChange={(e) => {
          console.log('Test input changed:', e.target.value);
          setValue(e.target.value);
        }}
        onClick={(e) => {
          console.log('Test input clicked');
          e.stopPropagation();
        }}
        onKeyDown={(e) => {
          console.log('Test input keydown:', e.key);
          e.stopPropagation();
        }}
        placeholder="Type here to test..."
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        style={{ position: 'relative', zIndex: 1000 }}
      />
      <p className="mt-2 text-sm text-gray-600">Current value: {value}</p>
    </div>
  );
} 