import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: ({ value }: { value: string }) => (
    <div data-testid="monaco-editor">{value}</div>
  ),
}));

// Mock React Flow
vi.mock('reactflow', () => ({
  ReactFlow: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ReactFlowProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Controls: () => <div>Controls</div>,
  MiniMap: () => <div>MiniMap</div>,
  Background: () => <div>Background</div>,
  Handle: ({ position }: { position: string }) => <div data-testid={`handle-${position}`}>Handle</div>,
  Position: {
    Top: 'top',
    Bottom: 'bottom',
    Left: 'left',
    Right: 'right',
  },
  addEdge: vi.fn(),
  useNodesState: vi.fn(() => [[], vi.fn(), vi.fn()]),
  useEdgesState: vi.fn(() => [[], vi.fn(), vi.fn()]),
}));

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock; 