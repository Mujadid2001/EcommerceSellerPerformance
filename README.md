# ECommerce Seller Performance System

A commercial-style Django 6 application for evaluating and monitoring e-commerce seller performance using weighted scoring, automated status assignment, AI-powered insights, audit logging, and reporting.

## What This Project Is

This project is a seller performance intelligence platform for a marketplace environment.

Primary usage intent: this site is built for sellers to use personally, so each seller can track their own performance, understand score changes, and take action to improve results.

It combines:
- Seller and order performance tracking
- Weighted score calculation (0-100)
- Automatic status assignment (active, under review, suspended)
- **🤖 AI-POWERED INSIGHTS** ← Featured Feature
  - Predictive alerts for performance decline
  - Automated recommendations for improvement
  - Trend analysis and anomaly detection
  - Health score calculation
  - Risk factor identification
- Authentication with role-based access
- Admin dashboard for import/export and monitoring
- Audit trail for security/compliance events
- Celery task automation for periodic jobs

The codebase is built as a Django monolith with modular apps:
- `apps.authentication`: custom user model, auth APIs, verification flow
- `apps.performance`: sellers/orders/feedback, scoring, dashboards, APIs
- `apps.ai_insights`: AI insight models, analysis service, predictive alerts
- `apps.audit_trail`: centralized audit events and request-level logging
- `apps.core`: shared serializer validation primitives

## How It Works

## 🤖 AI Features (Main Highlight)

The system includes advanced **AI-powered performance analysis** that helps sellers understand and improve their business:

### What the AI Does:

1. **Predictive Alerts** 🚨
   - Detects when your performance is trending downward
   - Alerts you before your status changes (e.g., before moving to "Under Review")
   - Helps you take corrective action early

2. **Trend Analysis** 📊
   - Analyzes historical order data patterns
   - Identifies seasonal trends and growth opportunities
   - Detects anomalies in delivery speed or return rates

3. **Smart Recommendations** 💡
   - Provides actionable suggestions based on your metrics
   - Examples: "Improve delivery speed on XYZ category" or "Reduce return rate by focusing on quality"
   - Ranked by impact and feasibility

4. **Health Score** 🏥
   - AI calculates your overall business health (0-100)
   - Breaks down which factors are helping or hurting
   - Shows risk factors to address

5. **Performance Predictions** 🔮
   - Forecasts where your score will be next month
   - Predicts which products/categories need attention

### Where to Find AI Insights:

- **Dashboard** → Top section shows AI predictions and recommendations
- **Dashboard** → Live health score and risk factors
- **Reports** → Detailed AI analysis on your seller report
- **Alerts** → Notifications when AI detects issues

### How AI Improves Over Time:

- Analyzes 30-60 days of historical data for accuracy
- Runs daily background analysis
- Continuously refines predictions as more data is added
- Results are cached for fast dashboard loading

---

## 1) Core Domain Model

Main entities:
- User (`authentication.User`): custom email-based auth model with role (`admin`, `user`, `seller`)
- Seller (`performance.Seller`): profile + cached performance metrics + status
- Order (`performance.Order`): order data used to compute delivery/sales/returns metrics
- CustomerFeedback (`performance.CustomerFeedback`): ratings that affect seller score
- PerformanceInsight / PredictiveAlert (`ai_insights`): generated analysis artifacts
- AuditEvent (`audit_trail`): security and business audit logs

## 2) Performance Scoring Pipeline

The scoring logic is in `apps.performance.services.performance_service.PerformanceCalculationService`.

Weighted components:
- Sales volume: 30%
- Delivery speed: 25%
- Customer rating: 30%
- Return behavior: 15%

Output:
- Final score between 0.00 and 100.00
- Seller metric snapshot is cached on `Seller`
- Score breakdown retained in service output for transparency/debugging

## 3) Status Assignment

`apps.performance.services.status_service.StatusAssignmentService` maps score to status:
- Active: score >= 70
- Under Review: 40 <= score < 70
- Suspended: score < 40

Status changes update `status_updated_at` and can be triggered in bulk.

## 4) AI Insights Layer

`apps.ai_insights.services.ai_service.AIInsightService` performs:
- Trend analysis
- Anomaly detection
- Prediction logic
- Recommendation generation
- Risk factor identification

Results are cached and then persisted into insight/alert records.

## 5) API + Web Routing

Top-level routes in `ECommerceSeller/urls.py`:
- `/` home page
- `/marketplace/` performance web + API endpoints
- `/auth/` auth web + API endpoints
- `/admin-dashboard/` custom operations dashboard
- `/api/schema/`, `/api/docs/` API schema and Swagger UI

Performance app exposes:
- Seller APIs (`/marketplace/api/sellers/...`)
- Order APIs (`/marketplace/api/orders/...`)
- Feedback APIs (`/marketplace/api/feedback/...`)
- Seller dashboards and reports

Authentication app exposes:
- Register/login/logout/verify/resend verification APIs
- User self and admin management APIs

## 6) Background Jobs (Celery)

Defined scheduled jobs include:
- Hourly AI analysis batch
- Daily seller performance recalculation
- Daily performance report generation
- Hourly verification token cleanup

Important local-dev behavior:
- `.env.example` defaults Celery to eager mode (`CELERY_TASK_ALWAYS_EAGER=True`)
- In eager mode, tasks execute immediately in-process without Redis/worker

## 7) Security, Observability, and Compliance

Implemented controls include:
- Security middleware (request ID + security headers)
- CSRF/CORS configuration
- Auth and permission checks
- Audit trail middleware with event classification
- Rotating log files (`logs/django.log`, `logs/audit.log`)
- Throttling in DRF settings

## Project Structure (High-Level)

```text
EcommerceSellerPerformance/
  ECommerceSeller/
    manage.py
    ECommerceSeller/
      settings.py
      urls.py
      celery.py
    apps/
      authentication/
      performance/
      ai_insights/
      audit_trail/
      core/
  requirements.txt
  .env.example
```

## How To Run This Project

## Prerequisites

- Python 3.11+ recommended
- pip
- (Optional for non-eager Celery) Redis

## 1) Clone and Enter Project

```powershell
git clone <your-repo-url>
cd EcommerceSellerPerformance
```

## 2) Create and Activate Virtual Environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 3) Install Dependencies

```powershell
pip install -r requirements.txt
```

## 4) Configure Environment Variables

Copy the template and edit values:

```powershell
Copy-Item .env.example .env
```

Minimum local values are already present for development (SQLite + eager Celery), but confirm:
- `DEBUG=True`
- `SECRET_KEY=...`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `CELERY_TASK_ALWAYS_EAGER=True` for simple local mode

If email verification should not block local testing, set:
- `EMAIL_VERIFICATION_REQUIRED=False`

## 5) Run Database Migrations

```powershell
cd ECommerceSeller
python manage.py migrate
```

## 6) Create an Admin User

```powershell
python manage.py createsuperuser
```

## 7) Start Development Server

```powershell
python manage.py runserver
```

Open:
- Home: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/
- API docs: http://127.0.0.1:8000/api/docs/
- Marketplace module: http://127.0.0.1:8000/marketplace/

## Optional: Run Celery in Full Async Mode

Use this only if you set non-eager Celery values in `.env`.

1. Configure:
- `CELERY_TASK_ALWAYS_EAGER=False`
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`

2. Start worker (from `ECommerceSeller/`):

```powershell
celery -A ECommerceSeller worker -l info
```

3. Start beat scheduler (separate terminal):

```powershell
celery -A ECommerceSeller beat -l info
```

## Running Tests

From `ECommerceSeller/`:

```powershell
python manage.py test
```

You can also run targeted app tests:

```powershell
python manage.py test apps.authentication
python manage.py test apps.performance
```

## Typical Request Flow

1. User authenticates through auth endpoints.
2. Seller/order/feedback data is created via web views or API.
3. Performance service computes weighted score from aggregated metrics.
4. Status service updates seller status by threshold.
5. AI service analyzes trend/risk and writes insights/alerts.
6. Audit middleware logs important security/business events.
7. Scheduled jobs keep insights, scores, and cleanup tasks up to date.

## How Users Can Use This System and Get Benefits

This platform is primarily designed for sellers' personal use, with additional capabilities for marketplace admin and operations teams.

## 1) Marketplace Admin / Operations Team

How they use it:
- Log in through admin or authenticated web/API endpoints.
- Onboard and manage sellers.
- Monitor seller score, status, delivery trend, and return behavior.
- Trigger recalculation endpoints or scheduled batch jobs.
- Review AI insights and predictive alerts for at-risk sellers.
- Export reports for weekly/monthly operational review.

Benefits:
- Faster detection of poor-performing sellers before customer impact grows.
- Standardized and transparent evaluation using weighted scoring.
- Reduced manual reporting effort through automated report tasks.
- Better compliance and traceability using audit trail logs.

## 2) Seller Users

How they use it:
- Log in and access seller dashboard.
- Review own performance score and status changes.
- Track key drivers: order delivery speed, customer ratings, return rate, sales volume.
- Check AI-generated recommendations and alerts.
- Download/report performance summaries to plan improvements.

Benefits:
- Clear visibility into what affects their score.
- Early warning signals for declining performance.
- Actionable recommendations to improve delivery, quality, and customer satisfaction.
- Higher chance of staying in active status and growing sales reputation.

## 3) Product / Data / Management Stakeholders

How they use it:
- Use API docs (`/api/docs/`) and schema (`/api/schema/`) to integrate dashboards.
- Pull seller, order, and feedback data through REST endpoints.
- Analyze trends across time for strategic decisions.

Benefits:
- Unified data model for marketplace performance KPIs.
- Easier integration with BI tools and analytics workflows.
- Better decision-making using both historical metrics and predictive insight signals.

## 4) Typical Practical Workflow for a New Team

1. Admin creates users and seller profiles.
2. Operations imports or records orders and feedback.
3. System computes scores and assigns seller status automatically.
4. AI insight service generates trend warnings and recommendations.
5. Team reviews dashboard and alerts, then takes corrective actions.
6. Reports are exported for business review and compliance records.

In short, users get value by moving from reactive monitoring to proactive seller performance management.

## Notes for Production Hardening

- Replace SQLite with PostgreSQL.
- Set `DEBUG=False` and strict `ALLOWED_HOSTS`.
- Use a real SMTP provider and verified sender.
- Enable HTTPS and secure proxy headers at the edge.
- Run Celery with Redis/RabbitMQ (non-eager).
- Add monitoring, backup, and secret management.

## Current Version

- Django settings indicate project versioning aligned with API docs `1.0.0`.
- API schema uses drf-spectacular.
