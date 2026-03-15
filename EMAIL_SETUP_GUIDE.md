# Email & Environment Configuration Guide

## Overview

This guide explains how to set up email configuration and manage environment variables for the ECommerce Seller Performance application.

## Environment File Setup

### Step 1: Create .env File

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual configuration values

### Step 2: Configure Email Settings

#### Option 1: Gmail (Recommended for Development)

1. **Enable 2-Factor Authentication on Gmail:**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification

2. **Generate App Password:**
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Windows Computer" (or your device)
   - Google will generate a 16-character password
   - Copy this password

3. **Update .env file:**
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   DEFAULT_FROM_EMAIL=your-email@gmail.com
   ```

#### Option 2: Microsoft Outlook

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=your-email@outlook.com
```

#### Option 3: Custom SMTP Server

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-mail-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-username
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=your-email@yourdomain.com
```

#### Option 4: Console Backend (Testing/Development)

For testing without sending actual emails:

```env
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

This will print emails to the console instead of sending them.

### Step 3: Email Verification Settings

```env
# Require email verification before login
EMAIL_VERIFICATION_REQUIRED=True

# Email verification token expiration (hours)
EMAIL_VERIFICATION_TIMEOUT_HOURS=24
```

## Email Verification Flow

### When EMAIL_VERIFICATION_REQUIRED=True

1. **User Registration:**
   - User registers with email and password
   - Verification email sent to their inbox
   - User receives: Email with verification link
   - User status: `is_verified = False`

2. **Email Verification:**
   - User clicks verification link in email
   - Verification token validated
   - User account marked as verified
   - User status: `is_verified = True`

3. **Login:**
   - User attempts to login
   - System checks: email verified?
   - If NOT verified: Login rejected with message
   - If verified: Login successful

### When EMAIL_VERIFICATION_REQUIRED=False

- Users can login immediately after registration
- Email verification is optional
- **Not recommended for production**

## Installing Dependencies

Make sure to install python-dotenv:

```bash
pip install python-dotenv
# OR
pip install -r requirements.txt
```

## Security Best Practices

### For Development

```env
DEBUG=True
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_VERIFICATION_REQUIRED=False
```

### For Production

```env
DEBUG=False
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_VERIFICATION_REQUIRED=True
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

## Troubleshooting

### "SMTP Authentication Error"

**Problem:** Email sending fails with authentication error

**Solutions:**
1. Verify EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are correct
2. For Gmail: Use App Password (not regular password)
3. Check if 2FA is enabled on the email account
4. Verify EMAIL_HOST and EMAIL_PORT are correct

### "Connection timeout"

**Problem:** Email sending times out

**Solutions:**
1. Check network connection
2. Verify EMAIL_HOST is correct
3. Verify EMAIL_PORT is correct (usually 587 for TLS)
4. Check firewall isn't blocking the port

### "Certificate verification failed"

**Problem:** SSL/TLS certificate verification fails

**Solutions:**
1. Ensure EMAIL_USE_TLS=True
2. Update SSL certificates on your system
3. Try disabling SSL verification (not recommended):
   ```python
   import ssl
   ssl._create_default_https_context = ssl._create_unverified_context
   ```

### Emails not sending in production

**Check:**
1. EMAIL_VERIFICATION_REQUIRED is set correctly
2. Email credentials are valid
3. Django is not in DEBUG mode
4. Check Django logs for errors
5. Verify DEFAULT_FROM_EMAIL matches EMAIL_HOST_USER

## Testing Email Configuration

### Test Email Sending Programmatically

```python
from django.core.mail import send_mail
from django.conf import settings

send_mail(
    subject='Test Email',
    message='This is a test email from Django',
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=['test@example.com'],
    fail_silently=False,
)
```

### Test via Django Shell

```bash
python manage.py shell
```

```python
from django.core.mail import send_mail
from django.conf import settings

result = send_mail(
    'Test',
    'Test message',
    settings.DEFAULT_FROM_EMAIL,
    ['recipient@example.com'],
    fail_silently=False,
)
print(f"Email sent: {result == 1}")
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | insecure default | Django secret key |
| `DEBUG` | True | Debug mode |
| `ALLOWED_HOSTS` | localhost | Allowed hostnames |
| `EMAIL_BACKEND` | smtp.EmailBackend | Email backend |
| `EMAIL_HOST` | smtp.gmail.com | SMTP server |
| `EMAIL_PORT` | 587 | SMTP port |
| `EMAIL_USE_TLS` | True | Use TLS encryption |
| `EMAIL_HOST_USER` | empty | SMTP username |
| `EMAIL_HOST_PASSWORD` | empty | SMTP password |
| `DEFAULT_FROM_EMAIL` | noreply@ecommerceseller.com | Sender email |
| `EMAIL_VERIFICATION_REQUIRED` | True | Require email verification |
| `EMAIL_VERIFICATION_TIMEOUT_HOURS` | 24 | Token expiration |

## Important Notes

⚠️ **Security Warning:**
- Never commit `.env` file to version control
- `.env` is already in `.gitignore`
- Only `.env.example` should be in version control
- Treat EMAIL_HOST_PASSWORD like a password - keep it secret!

✅ **Best Practices:**
- Use App Passwords for Gmail (not your main password)
- Rotate passwords regularly
- Use strong, unique passwords
- Monitor email logs for suspicious activity
- Test email configuration after setup
