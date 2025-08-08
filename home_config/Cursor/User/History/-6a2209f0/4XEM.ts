export function interpolateVariables(template: string, nodeOutputs: Record<string, any>): string {
  return template.replace(/\{\{([^}]+)\}\}/g, (match, path) => {
    try {
      // Flatten all node outputs into a single object for easier access
      const allData = Object.values(nodeOutputs).reduce((acc, output, index) => {
        acc[`node${index}`] = output;
        return acc;
      }, {} as Record<string, any>);

      // Add the first node's data as the default 'data' reference
      const firstOutput = Object.values(nodeOutputs)[0];
      if (firstOutput) {
        allData.data = firstOutput;
      }

      const value = getNestedValue(allData, path.trim());
      return value !== undefined ? String(value) : match;
    } catch (error) {
      console.warn(`Failed to interpolate variable: ${path}`, error);
      return match;
    }
  });
}

function getNestedValue(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => {
    if (current && typeof current === 'object' && key in current) {
      return current[key];
    }
    return undefined;
  }, obj);
}

export function validateInterpolation(template: string): { isValid: boolean; variables: string[] } {
  const variables: string[] = [];
  const regex = /\{\{([^}]+)\}\}/g;
  let match;

  while ((match = regex.exec(template)) !== null) {
    variables.push(match[1].trim());
  }

  return {
    isValid: true, // For now, we'll assume all variables are valid
    variables,
  };
} 