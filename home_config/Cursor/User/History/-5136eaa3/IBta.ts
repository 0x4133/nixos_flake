import type { SafeEvalContext } from '../types';
import * as fp from 'lodash/fp';

export function safeEval(expression: string, data: any): any {
  // Create a safe context with only allowed globals and functions
  const context: SafeEvalContext = {
    _: fp,
    data,
    Math,
    JSON,
    Array,
    Object,
    String,
    Number,
    Boolean,
    Date,
    RegExp,
  };

  // Create a function with the safe context
  const safeFunction = new Function(
    ...Object.keys(context),
    `"use strict"; return (${expression});`
  );

  try {
    return safeFunction(...Object.values(context));
  } catch (error) {
    throw new Error(`Expression evaluation failed: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export function validateExpression(expression: string): { isValid: boolean; error?: string } {
  try {
    // Basic syntax validation
    new Function(`"use strict"; return (${expression});`);
    return { isValid: true };
  } catch (error) {
    return {
      isValid: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

// Example expressions that work with the safe eval:
// Examples:
// - `_.map(data, item => item.name)`
// - `_.filter(data, item => item.active)`
// - `_.get(data, 'user.name', 'Unknown')`
// - `data.map(item => ({ ...item, processed: true }))`
// - `JSON.stringify(data, null, 2)`
// - `Math.max(...data.map(item => item.value))` 