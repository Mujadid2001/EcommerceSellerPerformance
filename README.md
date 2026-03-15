# ECommerce Seller Performance System

A comprehensive Django-based e-commerce seller performance management system with AI-powered insights, audit logging, and advanced analytics.

## Features

✨ **Core Features:**
- User Authentication with Email Verification
- Seller Performance Tracking & Scoring
- Order Management & Analytics
- Customer Feedback & Ratings
- AI-Powered Performance Insights
- Comprehensive Audit Trail Logging
- Real-time Dashboard & Reports
- Multi-user Support (Admin, Users, Sellers)

## System Architecture

### Database Models

- **Users**: Authentication & Authorization with role-based access
- **Sellers**: Seller profiles with performance metrics
- **Orders**: Order tracking and status management
- **Customer Feedback**: Ratings and reviews
- **AI Insights**: AI-generated performance recommendations
- **Audit Events**: Comprehensive system activity logging

### Key Apps

1. **authentication**: User management, email verification, login/logout
2. **performance**: Seller performance metrics and order management
3. **ai_insights**: AI-powered performance analysis and recommendations
4. **audit_trail**: Complete audit logging of all system activities

## Quick Start

### Prerequisites

- Python 3.9+
- pip
- Virtual Environment

### Installation

1. **Clone the repository:**
   ```bash
   cd EcommerceSellerPerformance
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy and configure `.env` file:**
   ```bash
   cp .env.example .env
   ```

5. **Configure email settings in `.env`:**
   ```env
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   EMAIL_VERIFICATION_REQUIRED=True
   ```
   
   See [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) for detailed instructions.

6. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   ```

8. **Populate sample data (optional):**
   ```bash
   python manage.py populate_data
   ```

9. **Start development server:**
   ```bash
   python manage.py runserver 8000
   ```

   Access at: http://127.0.0.1:8000

## Email Configuration

### Quick Setup for Gmail

1. Enable 2-Factor Authentication
2. Generate App Password at https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```env
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   ```

### Email Verification

- **EMAIL_VERIFICATION_REQUIRED=True** (Recommended):
  - Users must verify email before login
  - More secure
  
- **EMAIL_VERIFICATION_REQUIRED=False** (Development only):
  - Users can login without email verification
  - Not recommended for production

For detailed setup, see [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)

## Environment Configuration

### Required Environment Variables

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_VERIFICATION_REQUIRED=True
```

All available environment variables are documented in `.env.example`

## Project Structure

```
EcommerceSellerPerformance/
├── ECommerceSeller/              # Main Django project
│   ├── apps/
│   │   ├── authentication/       # User auth & verification
│   │   ├── performance/          # Seller performance tracking
│   │   ├── ai_insights/          # AI analysis & insights
│   │   └── audit_trail/          # Activity logging
│   ├── settings.py               # Django settings
│   └── urls.py                   # URL routing
├── .env                          # Environment variables (not in git)
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── EMAIL_SETUP_GUIDE.md          # Email configuration guide
└── README.md                     # This file
```

## Database Schema

### Key Tables

- `auth_user`: User accounts
- `performance_seller`: Seller profiles
- `performance_order`: Orders
- `performance_customerfeedback`: Ratings
- `ai_insights_performanceinsight`: AI insights
- `audit_trail_auditevent`: Audit logs

## Admin Panel

Access Django admin at: http://127.0.0.1:8000/admin

- Username: (your superuser email)
- Password: (your superuser password)

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user
- `POST /api/auth/verify-email/` - Verify email with token
- `POST /api/auth/resend-verification/` - Resend verification email

### Performance
- `GET/POST /api/sellers/` - Seller management
- `GET/POST /api/orders/` - Order management
- `GET/POST /api/feedback/` - Customer feedback

### Insights
- `GET /api/insights/` - AI-generated insights

### Audit
- `GET /api/audit/` - Audit trail logs (admin only)

## Data Population

Populate database with sample data:

```bash
python manage.py populate_data \
  --users 10 \
  --orders 50 \
  --insights 30 \
  --audit-events 100
```

This creates:
- 10 sellers
- 50 orders with various statuses
- 30 AI insights
- 100 audit events
- 3 regular users
- 1 admin user

## Troubleshooting

### Email Not Sending
1. Check `.env` EMAIL settings
2. Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
3. Run: `python manage.py shell` and test send_mail
4. Check Django logs in `logs/` directory

### Database Errors
```bash
# Reset database completely
python manage.py flush
python manage.py migrate
python manage.py createsuperuser
```

### Permission Issues
- Ensure user role is correct (admin, user, seller)
- Check audit logs for permission denied events

## Security Considerations

⚠️ **Important:**
- Never commit `.env` file (already in .gitignore)
- Never use DEBUG=True in production
- Use HTTPS in production
- Rotate security keys regularly
- Use strong passwords and App Passwords for email

## Development

### Running Tests
```bash
python manage.py test
```

### Code Quality
```bash
python manage.py check
```

### Generate Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Production Deployment

1. Set `DEBUG=False` in `.env`
2. Update `ALLOWED_HOSTS` with your domain
3. Use a production database (PostgreSQL)
4. Use a production email service
5. Configure HTTPS
6. Use a WSGI server (Gunicorn, uWSGI)
7. Set strong `SECRET_KEY`

## Documentation

- [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) - Email configuration details
- [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md) - Quick setup steps
- [Django Documentation](https://docs.djangoproject.com/) - Django reference

## Key Technologies

- **Django 6.0.1** - Web framework
- **Django REST Framework** - API framework
- **SQLite** - Development database
- **Celery** - Task queue (optional)
- **Redis** - Caching (optional)

## Support

For issues or questions:
1. Check the documentation files
2. Review EMAIL_SETUP_GUIDE.md for email issues
3. Check logs in `logs/` directory
4. Review Django admin for system state

## License

Proprietary - All rights reserved

## Version

Version 1.0.0 - March 2026
