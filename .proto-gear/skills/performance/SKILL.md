# Performance Optimization Skill

**Category**: Development Skill
**Difficulty**: Intermediate to Advanced
**Prerequisites**: Profiling tools, performance monitoring
**Estimated Time**: Variable (1 hour - 1 day depending on scope)

---

## Overview

Performance optimization is the systematic process of identifying and resolving performance bottlenecks in your application. This skill covers profiling, analysis, optimization techniques, and validation.

**Key Principles**:
- **Measure First**: Always profile before optimizing
- **Focus on Bottlenecks**: Optimize the slowest parts first (80/20 rule)
- **Validate Changes**: Measure impact of each optimization
- **Don't Premature Optimize**: Optimize when needed, not "just in case"
- **Consider Trade-offs**: Performance vs. maintainability vs. complexity

---

## When to Use This Skill

**Use performance optimization when**:
- ✅ Application response time is too slow
- ✅ Database queries are taking too long
- ✅ Memory usage is growing unbounded
- ✅ Frontend bundle size is too large
- ✅ API endpoints exceed SLA targets
- ✅ Users complain about slowness
- ✅ Preparing for production launch
- ✅ Scaling issues appear

**Don't optimize when**:
- ❌ Code is not yet working correctly
- ❌ No performance issues reported
- ❌ No measurements taken yet
- ❌ Time would be better spent on features

---

## Performance Optimization Workflow

### Step 1: Measure Current Performance

**Establish Baseline**:
```bash
# Backend (example with Python)
python -m cProfile -o profile.stats your_app.py
python -m pstats profile.stats

# Frontend (example with Lighthouse)
lighthouse https://yourapp.com --output=json --output-path=./report.json

# Database
EXPLAIN ANALYZE SELECT ...;

# Load testing
ab -n 1000 -c 10 http://yourapp.com/api/endpoint
```

**Metrics to Track**:
- **Response Time**: 95th percentile, median, max
- **Throughput**: Requests per second
- **Resource Usage**: CPU, memory, disk I/O
- **Database**: Query time, connections, slow queries
- **Frontend**: Time to First Byte, First Contentful Paint, Time to Interactive

**Document Baseline**:
```
Current Performance ({{DATE}}):
- API Response Time (p95): XXXms
- Page Load Time: XXXms
- Database Query Time: XXXms
- Memory Usage: XXX MB
- Bundle Size: XXX KB
```

### Step 2: Identify Bottlenecks

**Profiling Techniques**:

**Backend Profiling**:
```python
# Python example
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 slowest functions
```

**Frontend Profiling**:
- Chrome DevTools Performance tab
- React DevTools Profiler
- Bundle analyzer (webpack-bundle-analyzer)

**Database Profiling**:
```sql
-- PostgreSQL
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT * FROM users WHERE email = 'test@example.com';

-- Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;
```

**Look for**:
- Functions with high cumulative time
- N+1 query problems
- Large data transfers
- Unnecessary computations
- Memory allocations in loops
- Missing indexes
- Large bundle imports

### Step 3: Prioritize Optimizations

**Use Impact vs. Effort Matrix**:

```
High Impact, Low Effort (DO FIRST):
- Add database indexes
- Cache expensive computations
- Lazy load large modules
- Compress assets

High Impact, High Effort:
- Rewrite algorithm
- Refactor architecture
- Add caching layer
- Optimize database schema

Low Impact, Low Effort (IF TIME):
- Minor code tweaks
- Remove console.logs

Low Impact, High Effort (SKIP):
- Micro-optimizations
- Premature abstractions
```

### Step 4: Apply Optimization Techniques

#### Backend Optimizations

**1. Database Optimization**:
```sql
-- Add indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_posts_user_id_created ON posts(user_id, created_at DESC);

-- Use proper JOINs instead of N+1 queries
SELECT users.*, posts.*
FROM users
LEFT JOIN posts ON posts.user_id = users.id
WHERE users.active = true;

-- Add connection pooling
DATABASE_POOL_SIZE=20
```

**2. Caching**:
```python
# In-memory caching
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(param):
    # ... expensive work
    return result

# Redis caching
import redis
cache = redis.Redis()

def get_user(user_id):
    cached = cache.get(f"user:{user_id}")
    if cached:
        return json.loads(cached)

    user = db.query(User).get(user_id)
    cache.setex(f"user:{user_id}", 3600, json.dumps(user))
    return user
```

**3. Async/Parallel Processing**:
```python
# Use async for I/O-bound tasks
import asyncio

async def fetch_multiple_apis():
    results = await asyncio.gather(
        fetch_api_1(),
        fetch_api_2(),
        fetch_api_3()
    )
    return results

# Use multiprocessing for CPU-bound tasks
from multiprocessing import Pool

with Pool(processes=4) as pool:
    results = pool.map(cpu_intensive_function, data_list)
```

#### Frontend Optimizations

**1. Code Splitting**:
```javascript
// React lazy loading
import React, { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <HeavyComponent />
    </Suspense>
  );
}
```

**2. Memoization**:
```javascript
// React useMemo
import { useMemo } from 'react';

function ExpensiveComponent({ data }) {
  const processedData = useMemo(() => {
    return data.map(item => expensiveTransform(item));
  }, [data]);

  return <div>{processedData}</div>;
}

// React.memo for component memoization
const MemoizedComponent = React.memo(MyComponent);
```

**3. Bundle Optimization**:
```javascript
// webpack.config.js
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10
        }
      }
    }
  }
};
```

**4. Asset Optimization**:
```bash
# Image optimization
imagemin src/images/* --out-dir=dist/images

# Compression
# Enable gzip/brotli in server config

# Use modern image formats
<picture>
  <source srcset="image.avif" type="image/avif">
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="fallback">
</picture>
```

#### Algorithm Optimizations

**1. Time Complexity**:
```python
# Bad: O(n²)
for i in range(len(items)):
    for j in range(len(items)):
        if items[i] == items[j]:
            duplicates.append(items[i])

# Good: O(n)
seen = set()
duplicates = []
for item in items:
    if item in seen:
        duplicates.append(item)
    seen.add(item)
```

**2. Data Structures**:
```python
# Use appropriate data structures
# Bad: Linear search in list
if user_id in user_list:  # O(n)

# Good: Hash lookup in set/dict
if user_id in user_set:  # O(1)
```

### Step 5: Validate Improvements

**Re-run Measurements**:
```bash
# Run same benchmarks as Step 1
# Compare before/after metrics
```

**Document Results**:
```
Performance Improvement ({{DATE}}):

API Response Time (p95):
- Before: 450ms
- After: 120ms
- Improvement: 73% faster ✅

Page Load Time:
- Before: 3.2s
- After: 1.1s
- Improvement: 66% faster ✅

Memory Usage:
- Before: 512 MB
- After: 256 MB
- Reduction: 50% ✅

Changes Made:
1. Added database index on users.email
2. Implemented Redis caching for user queries
3. Lazy loaded admin dashboard components
4. Optimized image assets (WebP format)
```

### Step 6: Monitor Ongoing Performance

**Set Up Monitoring**:
- Application Performance Monitoring (APM): New Relic, DataDog, Sentry
- Real User Monitoring (RUM): Track actual user experience
- Synthetic Monitoring: Automated performance tests
- Alerts: Notify when performance degrades

**Performance Budget**:
```
Performance Budget:
- API p95 < 200ms
- Page Load < 2s
- Bundle Size < 200 KB
- Lighthouse Score > 90
```

---

## Common Performance Patterns

### Pattern 1: Database N+1 Queries

**Problem**:
```python
# Bad: N+1 queries (1 for users + N for each user's posts)
users = User.query.all()
for user in users:
    posts = user.posts  # Triggers separate query per user!
```

**Solution**:
```python
# Good: Single query with JOIN
users = User.query.options(joinedload(User.posts)).all()
```

### Pattern 2: Unnecessary Renders

**Problem**:
```javascript
// Bad: Component re-renders on every parent update
function ExpensiveList({ items }) {
  return items.map(item => <Item key={item.id} data={item} />);
}
```

**Solution**:
```javascript
// Good: Memoized to prevent unnecessary renders
const ExpensiveList = React.memo(({ items }) => {
  return items.map(item => <Item key={item.id} data={item} />);
});
```

### Pattern 3: Large Bundle Sizes

**Problem**:
```javascript
// Bad: Import entire library
import _ from 'lodash';
```

**Solution**:
```javascript
// Good: Import only what you need
import debounce from 'lodash/debounce';
```

---

## Performance Checklist

### Backend
- [ ] Database queries optimized (indexes, JOINs)
- [ ] Caching implemented (Redis, in-memory)
- [ ] Connection pooling configured
- [ ] Async processing for I/O-bound tasks
- [ ] Rate limiting to prevent abuse
- [ ] Pagination for large datasets
- [ ] Compression enabled (gzip/brotli)
- [ ] CDN for static assets

### Frontend
- [ ] Code splitting implemented
- [ ] Lazy loading for routes/components
- [ ] Images optimized (WebP, lazy loading)
- [ ] Bundle size < 200KB (gzipped)
- [ ] Memoization for expensive computations
- [ ] Debouncing for user inputs
- [ ] Virtual scrolling for long lists
- [ ] Service worker for offline/caching

### Database
- [ ] Indexes on frequently queried columns
- [ ] Query execution plans analyzed
- [ ] Slow query log reviewed
- [ ] Connection pooling configured
- [ ] Database statistics up to date
- [ ] Denormalization where appropriate
- [ ] Materialized views for complex queries

---

## Tools Reference

### Profiling Tools
- **Python**: cProfile, line_profiler, memory_profiler
- **JavaScript**: Chrome DevTools, React Profiler
- **Database**: EXPLAIN ANALYZE, pg_stat_statements
- **HTTP**: ab (Apache Bench), wrk, hey, Siege

### Monitoring Tools
- **APM**: New Relic, DataDog, Dynatrace, AppDynamics
- **RUM**: Sentry, LogRocket, FullStory
- **Synthetic**: Pingdom, UptimeRobot, StatusCake

### Analysis Tools
- **Bundle**: webpack-bundle-analyzer, source-map-explorer
- **Lighthouse**: Google Lighthouse, WebPageTest
- **Database**: pg_stat_statements, slow query log

---

## Best Practices

1. **Measure Before Optimizing**: Always have data
2. **Optimize the Bottleneck**: Focus on the slowest part (80/20 rule)
3. **One Change at a Time**: Measure impact of each change
4. **Document Changes**: Track what was changed and why
5. **Monitor Continuously**: Set up alerts for performance degradation
6. **Set Budgets**: Define acceptable performance thresholds
7. **Consider Trade-offs**: Performance vs. maintainability vs. complexity
8. **Test Under Load**: Simulate production traffic
9. **Optimize for Real Users**: Focus on metrics that matter to users
10. **Automate Checks**: Add performance tests to CI/CD

---

## Example Performance Optimization Session

```
PROJECT: E-commerce API
DATE: {{DATE}}
GOAL: Reduce API response time from 800ms to < 200ms

Step 1: Measurement
- Profiled /api/products endpoint: 850ms avg, 1200ms p95
- Identified bottleneck: Database query taking 600ms

Step 2: Investigation
- Ran EXPLAIN ANALYZE on slow query
- Found missing index on products.category_id
- N+1 query loading product images

Step 3: Optimization
1. Added index: CREATE INDEX idx_products_category ON products(category_id);
2. Fixed N+1: Added joinedload for images
3. Added Redis caching (5 min TTL)

Step 4: Validation
- Re-ran benchmarks:
  - Before: 850ms avg, 1200ms p95
  - After: 95ms avg, 150ms p95
  - Improvement: 89% faster! ✅

Step 5: Monitoring
- Set up DataDog alert: p95 > 300ms
- Added Lighthouse CI check: Score must be > 85
```

---

## Related Skills

- **Testing**: Ensure optimizations don't break functionality
- **Debugging**: Find root causes of slow performance
- **Code Review**: Review performance impact of changes
- **Refactoring**: Improve code structure for better performance

---

## Next Steps

After applying this skill:
1. Document all performance improvements in changelog
2. Update performance budget if needed
3. Set up continuous monitoring
4. Schedule regular performance audits
5. Share learnings with team

---

*Performance Optimization Skill - Proto Gear v0.10.0*
*Generated: {{DATE}}*
