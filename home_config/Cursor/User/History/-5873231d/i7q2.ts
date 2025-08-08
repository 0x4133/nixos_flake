import type { NodeData, ExecutionContext, LogEntry, ApiNodeData, TransformNodeData, OutputNodeData } from '../types';
import { interpolateVariables } from './interpolation';
import { safeEval } from './safeEval';
import axios from 'axios';

export async function executeApiNode(
  node: NodeData & { data: ApiNodeData },
  context: ExecutionContext,
  onLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void
): Promise<any> {
  console.log('Executing API node:', { node, nodeData: node.data });
  const { method, url, headers, body, useCorsProxy } = node.data;
  
  console.log('API node data:', { method, url, headers, body, useCorsProxy });
  console.log('Headers type:', typeof headers, 'Headers value:', headers);

  // Interpolate variables in URL, headers, and body
  const interpolatedUrl = interpolateVariables(url, context.nodeOutputs);
  const interpolatedHeaders = headers && typeof headers === 'object' && headers !== null
    ? Object.fromEntries(
        Object.entries(headers).map(([key, value]) => [
          key,
          interpolateVariables(value, context.nodeOutputs)
        ])
      )
    : {};
  const interpolatedBody = body ? interpolateVariables(body, context.nodeOutputs) : undefined;

  onLog({
    level: 'info',
    message: `Making ${method} request to: ${interpolatedUrl}`,
    data: { 
      method,
      url: interpolatedUrl,
      headers: interpolatedHeaders, 
      body: interpolatedBody,
      useCorsProxy 
    },
  });

  try {
    const finalUrl = useCorsProxy && !interpolatedUrl.startsWith('http://localhost') 
      ? `https://cors-anywhere.herokuapp.com/${interpolatedUrl}`
      : interpolatedUrl;

    const response = await axios({
      method,
      url: finalUrl,
      headers: interpolatedHeaders,
      data: interpolatedBody,
      timeout: 30000,
      validateStatus: () => true, // Don't throw on HTTP error status
    });

    onLog({
      level: 'info',
      message: `API call completed with status: ${response.status}`,
      data: { 
        status: response.status, 
        statusText: response.statusText,
        responseHeaders: response.headers,
        responseData: response.data,
        responseSize: JSON.stringify(response.data).length
      },
    });

    return {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
      data: response.data,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    onLog({
      level: 'error',
      message: `API call failed: ${errorMessage}`,
      data: { 
        error: errorMessage,
        originalError: error,
        requestDetails: {
          method,
          url: interpolatedUrl,
          headers: interpolatedHeaders,
          body: interpolatedBody
        }
      },
    });
    throw error;
  }
}

export async function executeTransformNode(
  node: NodeData & { data: TransformNodeData },
  context: ExecutionContext,
  onLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void
): Promise<any> {
  const { expression } = node.data;

  // Get input data from upstream nodes
  const inputData = getNodeInputData(node.id, context);

  onLog({
    level: 'info',
    message: `Executing transform expression`,
    data: { 
      expression, 
      inputData,
      inputDataType: typeof inputData,
      inputDataKeys: inputData && typeof inputData === 'object' ? Object.keys(inputData) : null
    },
  });

  try {
    const result = safeEval(expression, inputData);
    
    onLog({
      level: 'info',
      message: `Transform completed successfully`,
      data: { 
        result,
        resultType: typeof result,
        resultSize: JSON.stringify(result).length,
        isArray: Array.isArray(result),
        arrayLength: Array.isArray(result) ? result.length : null
      },
    });

    return result;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    onLog({
      level: 'error',
      message: `Transform failed: ${errorMessage}`,
      data: error,
    });
    throw error;
  }
}

export async function executeOutputNode(
  node: NodeData & { data: OutputNodeData },
  context: ExecutionContext,
  onLog: (log: Omit<LogEntry, 'id' | 'timestamp'>) => void
): Promise<any> {
  // Get input data from upstream nodes
  const inputData = getNodeInputData(node.id, context);

  onLog({
    level: 'info',
    message: `Output node received data`,
    data: { inputData },
  });

  return inputData;
}

function getNodeInputData(nodeId: string, context: ExecutionContext): any {
  // For now, we'll return the first upstream node's output
  // In a more sophisticated implementation, we might want to handle multiple inputs
  const upstreamOutputs = Object.values(context.nodeOutputs);
  return upstreamOutputs.length > 0 ? upstreamOutputs[0] : null;
} 