import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface PortalInputProps {
  nodeId: string;
  position: { x: number; y: number };
  onValueChange: (value: string) => void;
}

export function PortalInput({ nodeId, position, onValueChange }: PortalInputProps) {
  const [value, setValue] = useState('');
  const [isVisible, setIsVisible] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Show input when component mounts
    setIsVisible(true);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setValue(newValue);
    onValueChange(newValue);
  };

  const handleBlur = () => {
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return createPortal(
    <div
      style={{
        position: 'absolute',
        left: position.x,
        top: position.y,
        zIndex: 10000,
      }}
    >
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder="Type here..."
        className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        style={{ minWidth: '200px' }}
      />
    </div>,
    document.body
  );
} 