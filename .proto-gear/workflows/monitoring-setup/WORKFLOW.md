# Monitoring Setup Workflow

**Capability Type**: Workflow
**Category**: DevOps
**Complexity**: Intermediate to Advanced
**Estimated Time**: 3-8 hours (depends on scope)

## Overview

The Monitoring Setup workflow provides a systematic approach to implementing observability for applications. This workflow covers logging, metrics, tracing, alerting, and dashboards to help teams understand application health, performance, and user behavior.

## When to Use This Workflow

Use this workflow when you need to:

- **Production Readiness**: Prepare application for production deployment
- **Performance Issues**: Diagnose slow requests or high resource usage
- **Error Tracking**: Catch and fix bugs in production
- **User Behavior**: Understand how users interact with application
- **Capacity Planning**: Track resource usage trends
- **SLA Compliance**: Meet uptime and performance requirements
- **Incident Response**: Quickly identify and resolve issues

## Prerequisites

- **Application Deployed**: Running in at least staging environment
- **Access to Systems**: Permissions to add monitoring tools
- **Budget**: Some monitoring services have costs
- **Team Buy-In**: Agreement on what to monitor and alert on
- **Incident Response Plan**: Process for handling alerts

## Workflow Steps

### Phase 1: Define Monitoring Strategy

**Step 1.1: Identify Key Metrics**

```markdown
## Application Metrics to Track

### Golden Signals (SRE Best Practices)

**Latency**: How long requests take
- API response times (P50, P95, P99)
- Database query times
- External API call duration
- Page load times

**Traffic**: How much demand on the system
- Requests per second
- Active users
- Database connections
- Message queue depth

**Errors**: Rate of failed requests
- HTTP 4xx/5xx errors
- Exception rates
- Failed jobs/tasks
- Validation errors

**Saturation**: How "full" the service is
- CPU usage (%)
- Memory usage (%)
- Disk usage (%)
- Network bandwidth

### Business Metrics
- Sign-ups per day
- Successful purchases
- Feature usage rates
- User engagement metrics
- Revenue metrics

### Custom Metrics
- Background job processing time
- Cache hit/miss ratio
- Search result relevancy
- File upload success rate
```

**Step 1.2: Set Up Observability Pillars**

**Logs**: What happened (events, errors, debug info)
**Metrics**: How much/how many (counters, gauges, histograms)
**Traces**: Request flow across services (distributed tracing)

**Step 1.3: Choose Monitoring Tools**

**All-in-One Solutions**:
- **Datadog**: Comprehensive, expensive, great UX
- **New Relic**: APM focused, good for complex apps
- **Dynatrace**: Enterprise-grade, AI-powered insights

**Open Source Stack**:
- **Prometheus + Grafana**: Metrics and dashboards
- **ELK Stack (Elasticsearch, Logstash, Kibana)**: Log aggregation
- **Jaeger**: Distributed tracing

**Error Tracking**:
- **Sentry**: Best-in-class error tracking
- **Rollbar**: Error monitoring and debugging
- **Bugsnag**: Error monitoring with release tracking

**Uptime Monitoring**:
- **Pingdom**: Simple uptime checks
- **UptimeRobot**: Free uptime monitoring
- **StatusCake**: Uptime and performance monitoring

**Real User Monitoring (RUM)**:
- **Google Analytics**: User behavior
- **Mixpanel**: Product analytics
- **Amplitude**: User behavior analytics

### Phase 2: Implement Logging

**Step 2.1: Structured Logging**

**Node.js (Winston)**:
```javascript
const winston = require('winston');

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: {
    service: 'my-app',
    environment: process.env.NODE_ENV
  },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.simple()
      )
    }),
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error'
    }),
    new winston.transports.File({
      filename: 'logs/combined.log'
    })
  ]
});

// Usage
logger.info('User logged in', {
  userId: user.id,
  email: user.email,
  ip: req.ip
});

logger.error('Payment processing failed', {
  userId: user.id,
  amount: payment.amount,
  error: error.message,
  stack: error.stack
});
```

**Python (structlog)**:
```python
import structlog

logger = structlog.get_logger()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Usage
logger.info("user_login", user_id=user.id, email=user.email)

logger.error(
    "payment_failed",
    user_id=user.id,
    amount=payment.amount,
    error=str(error),
    exc_info=True
)
```

**Step 2.2: Log Aggregation**

**Datadog**:
```javascript
// Install: npm install dd-trace winston-transport-datadog
const winston = require('winston');
const DatadogWinston = require('winston-transport-datadog');

const logger = winston.createLogger({
  transports: [
    new DatadogWinston({
      apiKey: process.env.DD_API_KEY,
      hostname: process.env.HOSTNAME,
      service: 'my-app',
      ddsource: 'nodejs',
      ddtags: `env:${process.env.NODE_ENV}`
    })
  ]
});
```

**AWS CloudWatch**:
```javascript
const winston = require('winston');
const WinstonCloudWatch = require('winston-cloudwatch');

logger.add(new WinstonCloudWatch({
  logGroupName: '/aws/app/my-app',
  logStreamName: `${process.env.NODE_ENV}-${Date.now()}`,
  awsRegion: 'us-east-1',
  jsonMessage: true
}));
```

**ELK Stack (Elasticsearch)**:
```javascript
const { Client } = require('@elastic/elasticsearch');
const client = new Client({ node: 'http://localhost:9200' });

// Send logs to Elasticsearch
await client.index({
  index: 'app-logs',
  document: {
    '@timestamp': new Date(),
    level: 'info',
    message: 'User logged in',
    userId: user.id,
    service: 'my-app'
  }
});
```

### Phase 3: Implement Application Performance Monitoring (APM)

**Step 3.1: Datadog APM**

```javascript
// Initialize at the very top of app entry point
require('dd-trace').init({
  hostname: process.env.DD_AGENT_HOST || 'localhost',
  service: 'my-app',
  env: process.env.NODE_ENV,
  version: process.env.APP_VERSION,
  logInjection: true,
  analytics: true
});

const express = require('express');
const app = express();

// Automatic instrumentation for Express, PostgreSQL, Redis, etc.
app.get('/api/users/:id', async (req, res) => {
  // This request is automatically traced
  const user = await db.query('SELECT * FROM users WHERE id = $1', [req.params.id]);
  res.json(user);
});
```

**Step 3.2: New Relic APM**

```javascript
// Install: npm install newrelic
// Create newrelic.js in project root
'use strict';

exports.config = {
  app_name: ['My Application'],
  license_key: process.env.NEW_RELIC_LICENSE_KEY,
  logging: {
    level: 'info'
  },
  distributed_tracing: {
    enabled: true
  }
};

// Require at top of app.js
require('newrelic');
const express = require('express');
// ... rest of app
```

**Step 3.3: Open Telemetry (Vendor-Agnostic)**

```javascript
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { JaegerExporter } = require('@opentelemetry/exporter-jaeger');

const sdk = new NodeSDK({
  traceExporter: new JaegerExporter({
    endpoint: 'http://localhost:14268/api/traces',
  }),
  instrumentations: [getNodeAutoInstrumentations()]
});

sdk.start();
```

### Phase 4: Implement Error Tracking

**Step 4.1: Sentry Setup**

**JavaScript/Node.js**:
```javascript
const Sentry = require('@sentry/node');
const Tracing = require('@sentry/tracing');

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.APP_VERSION,
  tracesSampleRate: 0.1,  // 10% of transactions
  integrations: [
    new Sentry.Integrations.Http({ tracing: true }),
    new Tracing.Integrations.Express({ app }),
  ],
  beforeSend(event, hint) {
    // Filter out certain errors
    if (event.exception) {
      const error = hint.originalException;
      if (error && error.message && error.message.includes('Network Error')) {
        return null;  // Don't send to Sentry
      }
    }
    return event;
  }
});

// Express middleware
app.use(Sentry.Handlers.requestHandler());
app.use(Sentry.Handlers.tracingHandler());

// Your routes here

// Error handler (must be after all routes)
app.use(Sentry.Handlers.errorHandler());

// Manual error capture
try {
  processPayment(payment);
} catch (error) {
  Sentry.captureException(error, {
    user: { id: user.id, email: user.email },
    tags: { payment_method: payment.method },
    extra: { payment_amount: payment.amount }
  });
  throw error;
}
```

**Python**:
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.environ['SENTRY_DSN'],
    environment=os.environ.get('ENVIRONMENT', 'development'),
    release=os.environ.get('APP_VERSION'),
    traces_sample_rate=0.1,
    integrations=[FlaskIntegration()]
)

# Manual capture
try:
    process_payment(payment)
except Exception as error:
    sentry_sdk.capture_exception(
        error,
        user={'id': user.id, 'email': user.email},
        tags={'payment_method': payment.method},
        extra={'amount': payment.amount}
    )
    raise
```

### Phase 5: Implement Metrics Collection

**Step 5.1: Prometheus Metrics**

```javascript
const client = require('prom-client');

// Create a Registry
const register = new client.Registry();

// Add default metrics
client.collectDefaultMetrics({ register });

// Custom metrics
const httpRequestDuration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Duration of HTTP requests in seconds',
  labelNames: ['method', 'route', 'status_code'],
  buckets: [0.1, 0.5, 1, 2, 5]
});

const activeUsers = new client.Gauge({
  name: 'active_users',
  help: 'Number of active users'
});

const purchaseCounter = new client.Counter({
  name: 'purchases_total',
  help: 'Total number of purchases',
  labelNames: ['payment_method']
});

register.registerMetric(httpRequestDuration);
register.registerMetric(activeUsers);
register.registerMetric(purchaseCounter);

// Middleware to track request duration
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const duration = (Date.now() - start) / 1000;
    httpRequestDuration
      .labels(req.method, req.route?.path || req.path, res.statusCode)
      .observe(duration);
  });
  next();
});

// Expose metrics endpoint
app.get('/metrics', async (req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// Track business metrics
app.post('/api/purchase', async (req, res) => {
  await processPurchase(req.body);
  purchaseCounter.labels(req.body.paymentMethod).inc();
  res.json({ success: true });
});
```

**Step 5.2: StatsD Metrics**

```javascript
const StatsD = require('hot-shots');
const statsd = new StatsD({
  host: 'statsd.example.com',
  port: 8125,
  prefix: 'myapp.',
  globalTags: { env: process.env.NODE_ENV }
});

// Increment counter
statsd.increment('page_views');

// Timing
statsd.timing('database.query', 250);  // 250ms

// Gauge
statsd.gauge('active_users', 1337);

// Histogram
statsd.histogram('file_upload_size', fileSize);

// Set
statsd.set('unique_visitors', userId);
```

### Phase 6: Set Up Alerting

**Step 6.1: Define Alert Rules**

```markdown
## Alert Rules

### Critical (Page immediately)
- **Service Down**: HTTP health check fails for 2 minutes
- **Error Rate Spike**: Error rate > 5% for 5 minutes
- **Database Down**: Cannot connect to database
- **Payment Processing Failed**: >10 failed payments in 5 minutes
- **Disk Almost Full**: Disk usage > 90%

### Warning (Notify, don't page)
- **High Latency**: P95 response time > 2s for 10 minutes
- **High Memory**: Memory usage > 80% for 15 minutes
- **SSL Certificate Expiring**: < 7 days until expiration
- **Error Rate Elevated**: Error rate > 1% for 10 minutes
- **Low Throughput**: Traffic drops > 50% from baseline

### Info (Logging only)
- **Deployment Started**: New version being deployed
- **Scaling Event**: Auto-scaler added/removed instances
- **Scheduled Job Completed**: Nightly backup finished
```

**Step 6.2: PagerDuty Integration**

```javascript
const { Event } = require('@pagerduty/pdjs');

async function sendAlert(severity, message, details) {
  const event = {
    routing_key: process.env.PAGERDUTY_ROUTING_KEY,
    event_action: 'trigger',
    payload: {
      summary: message,
      severity: severity,  // critical, error, warning, info
      source: 'my-app',
      custom_details: details
    }
  };

  await Event.send(event);
}

// Usage
if (errorRate > 0.05) {
  await sendAlert('critical', 'High error rate detected', {
    error_rate: errorRate,
    time_window: '5m',
    threshold: 0.05
  });
}
```

**Step 6.3: Slack Alerts**

```javascript
const { WebClient } = require('@slack/web-api');
const slack = new WebClient(process.env.SLACK_TOKEN);

async function sendSlackAlert(channel, message, severity) {
  const color = {
    critical: 'danger',
    warning: 'warning',
    info: 'good'
  }[severity];

  await slack.chat.postMessage({
    channel: channel,
    attachments: [{
      color: color,
      title: `[${severity.toUpperCase()}] Alert`,
      text: message,
      footer: 'Monitoring System',
      ts: Math.floor(Date.now() / 1000)
    }]
  });
}
```

**Step 6.4: Prometheus AlertManager**

Create `alertmanager.yml`:
```yaml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  group_by: ['alertname', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'slack'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty'

receivers:
  - name: 'slack'
    slack_configs:
      - channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

Create `prometheus_rules.yml`:
```yaml
groups:
  - name: example
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} (threshold: 0.05)"

      - alert: HighLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds_bucket) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High P95 latency"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"

      - alert: ServiceDown
        expr: up{job="my-app"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.instance }} of job {{ $labels.job }} is down"
```

### Phase 7: Create Dashboards

**Step 7.1: Grafana Dashboard**

Create dashboard JSON or use Grafana UI:
```json
{
  "dashboard": {
    "title": "Application Overview",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(http_requests_total[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }],
        "type": "graph"
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }],
        "type": "graph"
      },
      {
        "title": "Active Users",
        "targets": [{
          "expr": "active_users"
        }],
        "type": "stat"
      }
    ]
  }
}
```

**Step 7.2: Datadog Dashboard**

```javascript
// Use Datadog UI or API
const datadog = require('@datadog/datadog-api-client');
const api = new datadog.v1.DashboardsApi();

const dashboard = {
  title: 'Application Monitoring',
  description: 'Overview of application health',
  widgets: [
    {
      definition: {
        type: 'timeseries',
        requests: [{
          q: 'avg:system.cpu.user{*}'
        }],
        title: 'CPU Usage'
      }
    }
  ],
  layout_type: 'ordered'
};

await api.createDashboard({ body: dashboard });
```

### Phase 8: Implement Health Checks

**Step 8.1: Basic Health Endpoint**

```javascript
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    version: process.env.APP_VERSION
  });
});
```

**Step 8.2: Detailed Health Checks**

```javascript
app.get('/health/detailed', async (req, res) => {
  const checks = {
    database: await checkDatabase(),
    redis: await checkRedis(),
    external_api: await checkExternalAPI(),
    disk_space: await checkDiskSpace()
  };

  const allHealthy = Object.values(checks).every(c => c.healthy);
  const status = allHealthy ? 'healthy' : 'unhealthy';

  res.status(allHealthy ? 200 : 503).json({
    status,
    timestamp: new Date().toISOString(),
    checks
  });
});

async function checkDatabase() {
  try {
    await db.query('SELECT 1');
    return { healthy: true, responseTime: 5 };
  } catch (error) {
    return { healthy: false, error: error.message };
  }
}
```

## Best Practices

1. **Start with Golden Signals**: Focus on latency, traffic, errors, saturation
2. **Alert on Symptoms**: Alert on user-impacting issues, not just technical metrics
3. **Reduce Alert Fatigue**: Only page for critical issues requiring immediate action
4. **Use Structured Logging**: JSON logs are easier to search and analyze
5. **Add Context**: Include user ID, request ID, trace ID in logs
6. **Monitor the Monitors**: Ensure monitoring system itself is reliable
7. **Test Alerts**: Regularly test that alerts fire correctly
8. **Document Runbooks**: Each alert should have resolution steps
9. **Set SLOs**: Define Service Level Objectives and track them
10. **Regular Review**: Weekly review of alerts, metrics, and incidents

## Integration with Other Skills

- **Performance Optimization**: Use metrics to identify bottlenecks
- **Security Auditing**: Monitor for security events
- **Dependency Management**: Track dependency health and versions
- **Testing**: Monitor test execution times and flakiness

## Success Metrics

- **Mean Time to Detection (MTTD)**: <5 minutes to detect issues
- **Mean Time to Resolution (MTTR)**: <1 hour to resolve incidents
- **Alert Precision**: >80% of alerts require action
- **Dashboard Usage**: Team checks dashboards daily
- **Log Coverage**: >95% of critical operations logged
- **Uptime**: >99.9% (3 nines) or better
- **False Positive Rate**: <20% of alerts

---

**Workflow Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
