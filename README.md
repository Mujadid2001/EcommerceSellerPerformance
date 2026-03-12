# E-Commerce Seller Performance Evaluation System

Production-ready Django application for automated seller performance evaluation.

## Quick Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run migrations
cd ECommerceSeller
python manage.py makemigrations
python manage.py migrate

# 3. Setup system (creates superuser + optional sample data)
python manage.py setup_system --seed-data

# 4. Run server
python manage.py runserver
```

## Access Points

- **Homepage**: http://127.0.0.1:8000/
- **Admin Panel**: http://127.0.0.1:8000/admin/
- **API Root**: http://127.0.0.1:8000/api/
- **Seller Dashboard**: http://127.0.0.1:8000/dashboard/

## Features

### Frontend (Web UI)
- ✅ Public marketplace with top sellers
- ✅ Seller dashboard with performance metrics
- ✅ Public seller profiles
- ✅ Responsive design with Bootstrap 5
- ✅ Real-time score visualization
- ✅ Order and feedback management

### Backend (REST API)
- ✅ Seller CRUD operations
- ✅ Order management
- ✅ Customer feedback system
- ✅ Performance metrics endpoint
- ✅ Score breakdown analysis
- ✅ Filtering and pagination

### Admin Dashboard
- ✅ Full seller management
- ✅ Performance recalculation
- ✅ Bulk operations
- ✅ Advanced filtering
- ✅ Score visualization

## API Endpoints

### Sellers
- `GET /api/sellers/` - List all sellers
- `GET /api/sellers/{id}/` - Get seller details
- `GET /api/sellers/{id}/metrics/` - Get performance metrics
- `GET /api/sellers/{id}/score_breakdown/` - Get score breakdown
- `GET /api/sellers/my_profile/` - Get current user's profile
- `POST /api/sellers/{id}/recalculate/` - Recalculate performance (admin)

### Orders
- `GET /api/orders/` - List all orders
- `GET /api/orders/{id}/` - Get order details
- `GET /api/orders/my_orders/` - Get current user's orders

### Feedback
- `GET /api/feedback/` - List all feedback
- `GET /api/feedback/{id}/` - Get feedback details
- `GET /api/feedback/my_feedback/` - Get current user's feedback

## Management Commands

```bash
# Evaluate sellers
python manage.py evaluate_sellers --all

# Seed sample data
python manage.py seed_performance_data --sellers=10 --orders=50

# Clear and reseed
python manage.py seed_performance_data --clear --sellers=10

# System setup
python manage.py setup_system --seed-data
```

## Architecture

```
apps/performance/
├── models.py           # Data models
├── views.py            # Web views + API ViewSets
├── serializers.py      # DRF serializers
├── admin.py            # Django admin config
├── signals.py          # Auto-update triggers
├── urls.py             # URL routing
├── managers/           # Custom query managers
├── services/           # Business logic
│   ├── performance_service.py
│   └── status_service.py
├── management/commands/    # CLI commands
├── templates/          # HTML templates
└── static/             # CSS/JS files
```

## Performance Scoring

- **Sales Volume**: 30% weight
- **Delivery Speed**: 25% weight
- **Customer Rating**: 30% weight
- **Returns Penalty**: 15% weight

### Status Assignment
- **Active**: Score ≥ 70
- **Under Review**: Score 40-70
- **Suspended**: Score < 40

## Technology Stack

- Django 6.0.1
- Django REST Framework 3.15.2
- Bootstrap 5.3.0
- SQLite (development) / PostgreSQL (production ready)

## Production Deployment

1. Set `DEBUG = False` in settings
2. Configure `ALLOWED_HOSTS`
3. Use PostgreSQL database
4. Set up static file serving
5. Configure environment variables
6. Schedule periodic evaluations
7. Set up monitoring

## Testing

```bash
python manage.py test apps.performance
```

## License

Proprietary - All rights reserved
