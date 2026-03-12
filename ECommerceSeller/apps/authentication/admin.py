"""
Admin configuration for authentication models following Django best practices.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from apps.authentication.models import User, LoginLog, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for User model.
    Follows Django's UserAdmin pattern with customizations for email-based auth.
    """
    
    # List display configuration
    list_display = (
        'email', 'get_full_name_display', 'role_badge', 'is_active', 
        'is_verified', 'is_staff', 'created_at'
    )
    list_filter = (
        'role', 
        'is_active', 
        'is_staff',
        'is_superuser',
        'is_verified', 
        'is_approved', 
        'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    list_display_links = ('email',)
    list_editable = ('is_active',)
    list_per_page = 50
    
    # Fieldsets for add and change forms
    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        (_('Personal Info'), {
            'fields': ('first_name', 'last_name', 'phone', 'profile_picture')
        }),
        (_('Permissions'), {
            'fields': (
                'is_active', 
                'is_staff', 
                'is_superuser',
                'role',
                'is_verified', 
                'is_approved',
                'groups', 
                'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Important Dates'), {
            'fields': ('last_login', 'last_login_at', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Add form fieldsets (for creating new users)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'is_staff', 'is_superuser'),
        }),
        (_('Personal Info'), {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone'),
        }),
    )
    
    # Read-only fields
    readonly_fields = ('created_at', 'updated_at', 'last_login', 'last_login_at', 'date_joined')
    
    # Custom display methods
    @admin.display(description='Full Name')
    def get_full_name_display(self, obj):
        """Display full name or email."""
        return obj.get_full_name()
    
    @admin.display(description='Role')
    def role_badge(self, obj):
        """Display role as colored badge."""
        colors = {
            'admin': '#dc3545',
            'user': '#28a745',
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_role_display_verbose()
        )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related()
    
    # Remove username field from the fieldsets
    def get_fieldsets(self, request, obj=None):
        """Return fieldsets based on whether adding or changing."""
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)
    
    def get_urls(self):
        """Custom admin URLs."""
        urls = super().get_urls()
        return urls
    
    # Admin actions
    @admin.action(description='Verify selected users')
    def verify_users(self, request, queryset):
        """Bulk verify user email addresses."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} user(s) successfully verified.')
    
    @admin.action(description='Approve selected users')
    def approve_users(self, request, queryset):
        """Bulk approve user accounts."""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} user(s) successfully approved.')
    
    @admin.action(description='Deactivate selected users')
    def deactivate_users(self, request, queryset):
        """Bulk deactivate user accounts."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} user(s) successfully deactivated.')
    
    actions = ['verify_users', 'approve_users', 'deactivate_users']


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """
    Admin interface for LoginLog model.
    Read-only audit trail of login attempts.
    """
    
    list_display = (
        'user_email', 'ip_address', 'success_badge', 'failure_reason', 'timestamp'
    )
    list_filter = ('success', 'timestamp')
    search_fields = ('user__email', 'ip_address', 'user_agent')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'success',
                      'failure_reason', 'timestamp')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 100
    
    @admin.display(description='User')
    def user_email(self, obj):
        """Display user email with link."""
        if obj.user:
            url = reverse('admin:authentication_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '-'
    
    @admin.display(description='Status', boolean=True)
    def success_badge(self, obj):
        """Display success status as badge."""
        return obj.success
    
    def has_add_permission(self, request):
        """Prevent manual addition of logs."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return request.user.is_superuser


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for EmailVerificationToken model.
    Manage email verification tokens.
    """
    
    list_display = (
        'user_email', 'token_short', 'created_at', 'expires_at', 
        'is_used', 'is_valid_status'
    )
    list_filter = ('is_used', 'created_at', 'expires_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('user', 'token', 'created_at', 'expires_at', 'is_used')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    @admin.display(description='User')
    def user_email(self, obj):
        """Display user email with link."""
        url = reverse('admin:authentication_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    
    @admin.display(description='Token')
    def token_short(self, obj):
        """Display shortened token."""
        return f"{str(obj.token)[:8]}..."
    
    @admin.display(description='Valid', boolean=True)
    def is_valid_status(self, obj):
        """Display if token is valid."""
        return obj.is_valid()
    
    def has_add_permission(self, request):
        """Prevent manual addition of tokens."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing of tokens."""
        return False
