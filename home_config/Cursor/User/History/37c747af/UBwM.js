class SIEMReporter {
  constructor(config = {}) {
    this.config = {
      endpoint: config.endpoint || 'https://127.0.0.1:8080/events',
      apiKey: config.apiKey || '',
      timeout: config.timeout || 5000,
      retryAttempts: config.retryAttempts || 3,
      batchSize: config.batchSize || 10,
      batchTimeout: config.batchTimeout || 30000,
      enabled: config.enabled !== false
    };
    
    this.eventQueue = [];
    this.batchTimer = null;
    this.isOnline = navigator.onLine;
    
    this.setupNetworkListeners();
    this.setupBatchProcessor();
  }

  setupNetworkListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.processBatch();
    });
    
    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  setupBatchProcessor() {
    this.batchTimer = setInterval(() => {
      if (this.eventQueue.length > 0) {
        this.processBatch();
      }
    }, this.config.batchTimeout);
  }

  async reportPIIDetection(eventData) {
    if (!this.config.enabled) {
      console.log('SIEM reporting disabled');
      return;
    }

    const siemEvent = this.formatSIEMEvent(eventData);
    
    this.eventQueue.push(siemEvent);
    
    if (this.eventQueue.length >= this.config.batchSize) {
      await this.processBatch();
    }
  }

  formatSIEMEvent(eventData) {
    const timestamp = new Date().toISOString();
    const userAgent = navigator.userAgent;
    const sessionId = this.getSessionId();
    
    return {
      timestamp,
      event_type: 'pii_detection',
      severity: this.mapSeverity(eventData.sensitivity.level),
      source: {
        extension_id: chrome?.runtime?.id || 'unknown',
        user_agent: userAgent,
        session_id: sessionId,
        url: eventData.url,
        domain: eventData.domain,
        page_title: eventData.pageTitle
      },
      detection: {
        ai_website_confidence: eventData.aiDetection.confidence,
        ai_detection_method: eventData.aiDetection.method,
        pii_types: eventData.piiDetections.map(d => d.type),
        pii_count: eventData.piiDetections.length,
        sensitivity_level: eventData.sensitivity.level,
        sensitivity_score: eventData.sensitivity.score,
        input_field_info: {
          selector: eventData.inputInfo.selector,
          placeholder: eventData.inputInfo.placeholder,
          element_type: eventData.inputInfo.type
        }
      },
      action: {
        transformation_applied: eventData.transformationApplied,
        user_notified: eventData.userNotified,
        input_blocked: eventData.inputBlocked
      },
      risk_assessment: {
        overall_risk: this.calculateOverallRisk(eventData),
        ai_platform_risk: this.assessAIPlatformRisk(eventData.domain),
        data_classification: this.classifyData(eventData.piiDetections)
      }
    };
  }

  mapSeverity(sensitivityLevel) {
    const severityMap = {
      'HIGH': 'high',
      'MEDIUM': 'medium', 
      'LOW': 'low'
    };
    return severityMap[sensitivityLevel] || 'low';
  }

  calculateOverallRisk(eventData) {
    let riskScore = 0;
    
    riskScore += eventData.aiDetection.confidence * 30;
    riskScore += eventData.sensitivity.score * 40;
    riskScore += eventData.piiDetections.length * 10;
    
    const highRiskDomains = ['openai.com', 'chat.openai.com', 'claude.ai'];
    if (highRiskDomains.includes(eventData.domain)) {
      riskScore += 20;
    }
    
    if (riskScore >= 80) return 'CRITICAL';
    if (riskScore >= 60) return 'HIGH';
    if (riskScore >= 40) return 'MEDIUM';
    return 'LOW';
  }

  assessAIPlatformRisk(domain) {
    const platformRisks = {
      'openai.com': 'HIGH',
      'chat.openai.com': 'HIGH',
      'claude.ai': 'HIGH',
      'anthropic.com': 'HIGH',
      'bard.google.com': 'MEDIUM',
      'copilot.microsoft.com': 'MEDIUM',
      'character.ai': 'MEDIUM'
    };
    
    return platformRisks[domain] || 'LOW';
  }

  classifyData(piiDetections) {
    const classifications = new Set();
    
    for (const detection of piiDetections) {
      switch (detection.type) {
        case 'SSN':
        case 'CREDIT_CARD':
        case 'MEDICAL_RECORD':
          classifications.add('HIGHLY_SENSITIVE');
          break;
        case 'EMAIL':
        case 'PHONE':
        case 'PASSPORT':
          classifications.add('PERSONALLY_IDENTIFIABLE');
          break;
        case 'IP_ADDRESS':
        case 'DRIVERS_LICENSE':
          classifications.add('IDENTIFIABLE');
          break;
        default:
          classifications.add('GENERAL');
      }
    }
    
    return Array.from(classifications);
  }

  async processBatch() {
    if (this.eventQueue.length === 0 || !this.isOnline) {
      return;
    }

    const batch = this.eventQueue.splice(0, this.config.batchSize);
    
    try {
      await this.sendToSIEM(batch);
      console.log(`Successfully sent ${batch.length} events to SIEM`);
    } catch (error) {
      console.error('Failed to send events to SIEM:', error);
      this.eventQueue.unshift(...batch);
    }
  }

  async sendToSIEM(events, attempt = 1) {
    if (!this.config.endpoint || !this.config.apiKey) {
      throw new Error('SIEM endpoint or API key not configured');
    }

    const payload = {
      events,
      metadata: {
        source: 'ai-pii-protection-extension',
        version: '1.0.0',
        timestamp: new Date().toISOString()
      }
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      const response = await fetch(this.config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
          'X-Source': 'ai-pii-protection-extension'
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      return result;

    } catch (error) {
      clearTimeout(timeoutId);
      
      if (attempt < this.config.retryAttempts) {
        console.warn(`SIEM request failed (attempt ${attempt}), retrying...`);
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        return this.sendToSIEM(events, attempt + 1);
      }
      
      throw error;
    }
  }

  getSessionId() {
    let sessionId = sessionStorage.getItem('pii-protection-session-id');
    if (!sessionId) {
      sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
      sessionStorage.setItem('pii-protection-session-id', sessionId);
    }
    return sessionId;
  }

  updateConfig(newConfig) {
    this.config = { ...this.config, ...newConfig };
  }

  getQueueStatus() {
    return {
      queueLength: this.eventQueue.length,
      isOnline: this.isOnline,
      enabled: this.config.enabled
    };
  }

  clearQueue() {
    this.eventQueue = [];
  }

  destroy() {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    this.processBatch();
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = SIEMReporter;
}