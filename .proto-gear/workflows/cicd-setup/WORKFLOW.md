# CI/CD Setup Workflow

**Capability Type**: Workflow
**Category**: DevOps
**Complexity**: Intermediate to Advanced
**Estimated Time**: 2-6 hours (depends on complexity)

## Overview

The CI/CD Setup workflow provides a systematic approach to implementing Continuous Integration and Continuous Deployment pipelines. This workflow helps teams automate testing, building, and deployment processes, enabling faster and more reliable software delivery.

## When to Use This Workflow

Use this workflow when you need to:

- **New Project Setup**: Establish CI/CD from the start
- **Legacy Modernization**: Add automation to existing projects
- **Improve Deployment**: Replace manual deployments with automation
- **Increase Confidence**: Automated testing before deployment
- **Faster Feedback**: Quick validation of code changes
- **Team Scaling**: Enable multiple developers to work efficiently
- **Quality Gates**: Enforce quality standards before production

## Prerequisites

- **Version Control**: Git repository (GitHub, GitLab, Bitbucket, etc.)
- **Test Suite**: Existing automated tests
- **Deployment Target**: Server, cloud platform, or hosting service
- **Access Credentials**: Repository permissions, deployment keys
- **Deployment Strategy**: Understanding of how application should be deployed

## Workflow Steps

### Phase 1: Planning and Requirements

**Step 1.1: Define CI/CD Goals**

```markdown
## CI/CD Goals and Requirements

### Continuous Integration Goals
- [ ] Run tests on every push
- [ ] Run tests on pull requests
- [ ] Enforce code quality checks (linting, formatting)
- [ ] Build artifacts for each commit
- [ ] Verify build succeeds across platforms
- [ ] Enforce coverage thresholds (70%+)
- [ ] Scan for security vulnerabilities
- [ ] Run performance tests

### Continuous Deployment Goals
- [ ] Deploy to staging automatically on main branch
- [ ] Deploy to production on release tags
- [ ] Blue-green deployment for zero downtime
- [ ] Automated rollback on failures
- [ ] Environment-specific configurations
- [ ] Database migration automation
- [ ] Health checks after deployment

### Quality Gates
- [ ] All tests must pass (100%)
- [ ] Code coverage >= 70%
- [ ] No critical security vulnerabilities
- [ ] Linting passes
- [ ] Build succeeds
- [ ] Performance benchmarks within thresholds
```

**Step 1.2: Choose CI/CD Platform**

**GitHub Actions**: Best for GitHub-hosted projects, free for public repos
**GitLab CI**: Integrated with GitLab, powerful pipeline features
**CircleCI**: Fast builds, good Docker support
**Travis CI**: Traditional choice, good documentation
**Jenkins**: Self-hosted, highly customizable
**Azure Pipelines**: Best for Microsoft stack
**AWS CodePipeline**: Best for AWS infrastructure

**Decision Factors**:
- Where is code hosted?
- Team familiarity
- Budget constraints (free tier availability)
- Required integrations
- Deployment targets (AWS, Azure, GCP, etc.)

**Step 1.3: Identify Environments**

```markdown
## Environments

### Development
- **Purpose**: Local development and testing
- **Deployment**: Not automated (local only)
- **Data**: Mock or minimal test data

### Staging
- **Purpose**: Pre-production testing
- **Deployment**: Auto-deploy on main/develop branch
- **Data**: Copy of production data (sanitized)
- **URL**: https://staging.example.com

### Production
- **Purpose**: Live application for users
- **Deployment**: Auto-deploy on release tags (v*)
- **Data**: Real user data
- **URL**: https://example.com
```

### Phase 2: Set Up Continuous Integration

**Step 2.1: GitHub Actions - Basic CI**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        node-version: [16.x, 18.x, 20.x]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run tests
        run: npm test

      - name: Run build
        run: npm run build

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unittests
          fail_ci_if_error: true
```

**Step 2.2: GitHub Actions - Advanced CI with Quality Gates**

```yaml
name: CI with Quality Gates

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  NODE_VERSION: '18.x'
  COVERAGE_THRESHOLD: 70

jobs:
  # Job 1: Code Quality
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run Prettier
        run: npm run format:check

      - name: Run TypeScript check
        run: npx tsc --noEmit

  # Job 2: Unit Tests
  test:
    runs-on: ubuntu-latest
    needs: quality

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests with coverage
        run: npm test -- --coverage

      - name: Check coverage threshold
        run: |
          COVERAGE=$(npm test -- --coverage --silent | grep "All files" | awk '{print $10}' | sed 's/%//')
          if (( $(echo "$COVERAGE < $COVERAGE_THRESHOLD" | bc -l) )); then
            echo "Coverage $COVERAGE% is below threshold $COVERAGE_THRESHOLD%"
            exit 1
          fi

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

  # Job 3: Integration Tests
  integration:
    runs-on: ubuntu-latest
    needs: test

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run database migrations
        run: npm run migrate
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379

      - name: Run integration tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test
          REDIS_URL: redis://localhost:6379

  # Job 4: Security Scan
  security:
    runs-on: ubuntu-latest
    needs: quality

    steps:
      - uses: actions/checkout@v3

      - name: Run npm audit
        run: npm audit --audit-level=high

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  # Job 5: Build
  build:
    runs-on: ubuntu-latest
    needs: [test, integration, security]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build

      - name: Upload build artifacts
        uses: actions/upload-artifact@v3
        with:
          name: build-${{ github.sha }}
          path: dist/
          retention-days: 7
```

**Step 2.3: GitLab CI - Basic Pipeline**

Create `.gitlab-ci.yml`:

```yaml
image: node:18

stages:
  - test
  - build
  - deploy

variables:
  NODE_ENV: production

cache:
  paths:
    - node_modules/

before_script:
  - npm ci

test:lint:
  stage: test
  script:
    - npm run lint

test:unit:
  stage: test
  script:
    - npm test -- --coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml

build:
  stage: build
  script:
    - npm run build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week
  only:
    - main
    - develop
```

**Step 2.4: CircleCI Configuration**

Create `.circleci/config.yml`:

```yaml
version: 2.1

orbs:
  node: circleci/node@5.0

jobs:
  test:
    docker:
      - image: cimg/node:18.0
    steps:
      - checkout
      - node/install-packages:
          pkg-manager: npm
      - run:
          name: Run linter
          command: npm run lint
      - run:
          name: Run tests
          command: npm test -- --coverage
      - run:
          name: Upload coverage
          command: bash <(curl -s https://codecov.io/bash)

  build:
    docker:
      - image: cimg/node:18.0
    steps:
      - checkout
      - node/install-packages:
          pkg-manager: npm
      - run:
          name: Build application
          command: npm run build
      - persist_to_workspace:
          root: .
          paths:
            - dist

workflows:
  test-and-build:
    jobs:
      - test
      - build:
          requires:
            - test
```

### Phase 3: Set Up Continuous Deployment

**Step 3.1: Deploy to Staging (GitHub Actions)**

Add to `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ main, develop ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.example.com

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18.x'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build application
        run: npm run build
        env:
          NODE_ENV: production
          API_URL: https://api-staging.example.com

      - name: Deploy to staging (AWS S3 + CloudFront)
        run: |
          aws s3 sync dist/ s3://staging-bucket --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.STAGING_CF_ID }} --paths "/*"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1

      - name: Run smoke tests
        run: |
          sleep 30  # Wait for deployment to propagate
          curl --fail https://staging.example.com/health || exit 1

      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployed to staging: https://staging.example.com'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        if: always()
```

**Step 3.2: Deploy to Production (GitHub Actions)**

Add to `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://example.com

    steps:
      - uses: actions/checkout@v3

      - name: Extract version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18.x'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run tests (final check)
        run: npm test

      - name: Build application
        run: npm run build
        env:
          NODE_ENV: production
          API_URL: https://api.example.com
          VERSION: ${{ steps.version.outputs.VERSION }}

      - name: Deploy to production (AWS S3 + CloudFront)
        run: |
          aws s3 sync dist/ s3://production-bucket --delete
          aws cloudfront create-invalidation --distribution-id ${{ secrets.PROD_CF_ID }} --paths "/*"
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1

      - name: Health check
        run: |
          sleep 60  # Wait for deployment
          curl --fail https://example.com/health || exit 1

      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ steps.version.outputs.VERSION }}
          draft: false
          prerelease: false

      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: '🚀 Deployed v${{ steps.version.outputs.VERSION }} to production'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
        if: always()

      - name: Rollback on failure
        if: failure()
        run: |
          echo "Deployment failed, initiating rollback..."
          # Rollback logic here (e.g., redeploy previous version)
```

**Step 3.3: Deploy to Vercel**

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

**Step 3.4: Deploy to Heroku**

```yaml
name: Deploy to Heroku

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to Heroku
        uses: akhileshns/heroku-deploy@v3.12.12
        with:
          heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
          heroku_app_name: "your-app-name"
          heroku_email: "your-email@example.com"

      - name: Run database migrations
        run: heroku run npm run migrate --app your-app-name
        env:
          HEROKU_API_KEY: ${{ secrets.HEROKU_API_KEY }}
```

**Step 3.5: Deploy with Docker**

```yaml
name: Build and Deploy Docker

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: username/app-name
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Deploy to production
        if: startsWith(github.ref, 'refs/tags/v')
        run: |
          ssh ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} << 'EOF'
            cd /app
            docker-compose pull
            docker-compose up -d
            docker-compose exec app npm run migrate
          EOF
```

### Phase 4: Environment Management

**Step 4.1: Managing Secrets**

**GitHub Secrets**:
- Navigate to: Settings → Secrets and variables → Actions
- Add secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.
- Reference in workflow: `${{ secrets.SECRET_NAME }}`

**Environment-Specific Variables**:

```yaml
# .github/workflows/deploy.yml
jobs:
  deploy:
    environment:
      name: ${{ matrix.environment }}
    strategy:
      matrix:
        environment: [staging, production]
    steps:
      - name: Deploy
        run: echo "Deploying to ${{ matrix.environment }}"
        env:
          API_URL: ${{ secrets.API_URL }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

**Step 4.2: Database Migrations**

```yaml
# Run migrations before deployment
- name: Run database migrations
  run: npm run migrate
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}

# Rollback migrations if deployment fails
- name: Rollback migrations
  if: failure()
  run: npm run migrate:rollback
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

**Step 4.3: Feature Flags**

```yaml
# Deploy with feature flags
- name: Deploy with feature flags
  run: npm run build
  env:
    FEATURE_NEW_DASHBOARD: ${{ secrets.FEATURE_NEW_DASHBOARD }}
    FEATURE_BETA_SEARCH: false
```

### Phase 5: Monitoring and Notifications

**Step 5.1: Slack Notifications**

```yaml
- name: Notify Slack on success
  if: success()
  uses: 8398a7/action-slack@v3
  with:
    status: custom
    custom_payload: |
      {
        text: '✅ Deployment successful',
        attachments: [{
          color: 'good',
          text: `Deployed ${process.env.AS_COMMIT} to production\nBy: ${process.env.AS_AUTHOR}`
        }]
      }
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}

- name: Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: custom
    custom_payload: |
      {
        text: '❌ Deployment failed',
        attachments: [{
          color: 'danger',
          text: `Failed to deploy ${process.env.AS_COMMIT}`
        }]
      }
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

**Step 5.2: Status Badges**

Add to `README.md`:

```markdown
# Project Name

![CI](https://github.com/username/repo/workflows/CI/badge.svg)
![Deploy](https://github.com/username/repo/workflows/Deploy/badge.svg)
[![codecov](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repo)
```

**Step 5.3: Deployment Dashboard**

Use GitHub Environments to track deployments:
- Settings → Environments → New environment
- Configure protection rules
- View deployment history

### Phase 6: Optimization and Best Practices

**Step 6.1: Caching**

```yaml
# Cache npm dependencies
- name: Cache node modules
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-

# Cache build artifacts
- name: Cache build
  uses: actions/cache@v3
  with:
    path: dist/
    key: ${{ runner.os }}-build-${{ github.sha }}
```

**Step 6.2: Parallel Jobs**

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node-version: [16.x, 18.x, 20.x]
    runs-on: ${{ matrix.os }}
    steps:
      # Steps run in parallel across all matrix combinations
```

**Step 6.3: Conditional Execution**

```yaml
# Run only on specific branches
- name: Deploy
  if: github.ref == 'refs/heads/main'
  run: npm run deploy

# Run only on PRs
- name: Preview deployment
  if: github.event_name == 'pull_request'
  run: npm run deploy:preview

# Run only for specific files
- name: Run tests
  if: contains(github.event.head_commit.modified, 'src/')
  run: npm test
```

## Best Practices

1. **Start Simple**: Begin with basic CI, add CD incrementally
2. **Fail Fast**: Run quick checks (lint, unit tests) before slow ones
3. **Secure Secrets**: Never hardcode credentials, use secret management
4. **Idempotent Deployments**: Deployments should produce same result when run multiple times
5. **Automated Rollback**: Have a strategy to rollback failed deployments
6. **Monitor Everything**: Track deployment success rates, durations, failures
7. **Document Processes**: Keep CI/CD documentation up to date
8. **Test Deployments**: Regularly test the deployment process in non-production
9. **Version Everything**: Tag releases, version configurations
10. **Progressive Rollout**: Consider canary or blue-green deployments

## Integration with Other Skills

- **Testing**: CI runs test suite automatically
- **Security Auditing**: Integrate security scans into CI
- **Dependency Management**: Auto-update and test dependencies
- **Documentation**: Generate and deploy docs automatically
- **Performance**: Run performance benchmarks in CI

## Success Metrics

- **Deployment Frequency**: Daily or multiple times per day
- **Lead Time**: <1 hour from commit to production
- **Change Failure Rate**: <15% of deployments cause issues
- **Mean Time to Recovery (MTTR)**: <1 hour to rollback or fix
- **CI Build Time**: <10 minutes for full pipeline
- **Test Success Rate**: >95% of test runs pass
- **Deployment Success Rate**: >98% of deployments succeed

---

**Workflow Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
