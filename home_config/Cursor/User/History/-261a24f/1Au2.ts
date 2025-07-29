import { describe, it, expect } from 'vitest';
import { detectCycles, topologicalSort } from '../utils/execution';
import type { Graph } from '../types';

describe('Execution Engine', () => {
  describe('detectCycles', () => {
    it('should detect cycles in a graph', () => {
      const graph: Graph = {
        nodes: [
          { id: '1', type: 'api', position: { x: 0, y: 0 }, data: {}, status: 'idle', logs: [] },
          { id: '2', type: 'transform', position: { x: 0, y: 100 }, data: {}, status: 'idle', logs: [] },
          { id: '3', type: 'output', position: { x: 0, y: 200 }, data: {}, status: 'idle', logs: [] },
        ],
        edges: [
          { id: '1-2', source: '1', target: '2' },
          { id: '2-3', source: '2', target: '3' },
          { id: '3-1', source: '3', target: '1' }, // This creates a cycle
        ],
      };

      const cycles = detectCycles(graph);
      expect(cycles.length).toBeGreaterThan(0);
      expect(cycles).toContain('1');
      expect(cycles).toContain('2');
      expect(cycles).toContain('3');
    });

    it('should not detect cycles in a valid graph', () => {
      const graph: Graph = {
        nodes: [
          { id: '1', type: 'api', position: { x: 0, y: 0 }, data: {}, status: 'idle', logs: [] },
          { id: '2', type: 'transform', position: { x: 0, y: 100 }, data: {}, status: 'idle', logs: [] },
          { id: '3', type: 'output', position: { x: 0, y: 200 }, data: {}, status: 'idle', logs: [] },
        ],
        edges: [
          { id: '1-2', source: '1', target: '2' },
          { id: '2-3', source: '2', target: '3' },
        ],
      };

      const cycles = detectCycles(graph);
      expect(cycles.length).toBe(0);
    });
  });

  describe('topologicalSort', () => {
    it('should sort nodes in correct order', () => {
      const graph: Graph = {
        nodes: [
          { id: '1', type: 'api', position: { x: 0, y: 0 }, data: {}, status: 'idle', logs: [] },
          { id: '2', type: 'transform', position: { x: 0, y: 100 }, data: {}, status: 'idle', logs: [] },
          { id: '3', type: 'output', position: { x: 0, y: 200 }, data: {}, status: 'idle', logs: [] },
        ],
        edges: [
          { id: '1-2', source: '1', target: '2' },
          { id: '2-3', source: '2', target: '3' },
        ],
      };

      const sorted = topologicalSort(graph);
      expect(sorted).toEqual(['1', '2', '3']);
    });

    it('should throw error for cyclic graph', () => {
      const graph: Graph = {
        nodes: [
          { id: '1', type: 'api', position: { x: 0, y: 0 }, data: {}, status: 'idle', logs: [] },
          { id: '2', type: 'transform', position: { x: 0, y: 100 }, data: {}, status: 'idle', logs: [] },
        ],
        edges: [
          { id: '1-2', source: '1', target: '2' },
          { id: '2-1', source: '2', target: '1' },
        ],
      };

      expect(() => topologicalSort(graph)).toThrow('Graph contains cycles');
    });
  });
}); 