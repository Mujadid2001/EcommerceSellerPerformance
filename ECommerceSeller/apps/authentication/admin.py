"""
Admin configuration for authentication models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from apps.authentication.models import User, LoginLog, EmailVerificationToken


class PendingTeacherFilter(admin.SimpleListFilter):
    """Custom filter to show pending teacher approvals."""
    title = 'Teacher Approval Status'
    parameter_name = 'teacher_approval'
    
    def lookups(self, request, model_admin):
        return (
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'pending':
            return queryset.filter(role=User.Role.TEACHER, is_approved=False)
        if self.value() == 'approved':
            return queryset.filter(role=User.Role.TEACHER, is_approved=True)
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = (
        'email', 'get_full_name', 'role', 'is_active', 'is_verified',
        'approval_status', 'verify_action', 'created_at'
    )
    list_filter = (
        PendingTeacherFilter,
        'role', 
        'is_active', 
        'is_verified', 
        'is_approved', 
        'created_at'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    # Custom filter to show pending teachers
    list_display_links = ('email', 'get_full_name')
    
    def approval_status(self, obj):
        """Display approval status with color coding."""
        if obj.role == User.Role.TEACHER:
            if obj.is_approved:
                return format_html(
                    '<span style="color: green; font-weight: bold;">✓ Approved</span>'
                )
            else:
                return format_html(
                    '<span style="color: orange; font-weight: bold;">⏳ Pending</span>'
                )
        return format_html('<span style="color: gray;">N/A</span>')
    approval_status.short_description = 'Approval Status'
    
    def verify_action(self, obj):
        """Display individual verify button for pending teachers."""
        if obj.role == User.Role.TEACHER and not obj.is_approved:
            return format_html(
                '<a class="button default" href="{}?ids={}" '
                'style="display: inline-block; background-color: #417690; color: white !important; '
                'padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 13px; '
                'font-weight: 500; text-align: center; white-space: nowrap; cursor: pointer; '
                'transition: background-color 0.3s ease; min-width: 90px;" '
                'onmouseover="this.style.backgroundColor=\'#2e5266\';" '
                'onmouseout="this.style.backgroundColor=\'#417690\';" '
                'onclick="return confirm(\'Approve this teacher account?\');">'
                '✓ Verify Now</a>',
                reverse('admin:approve_teacher_individual'),
                obj.id
            )
        elif obj.role == User.Role.TEACHER and obj.is_approved:
            return format_html('<span style="color: green; font-weight: 500;">✓ Verified</span>')
        return '-'
    verify_action.short_description = 'Quick Action'
    
    def get_queryset(self, request):
        """Customize queryset to show pending teachers first."""
        qs = super().get_queryset(request)
        # Sort to show pending teachers at the top
        return qs.order_by('is_approved', '-created_at')
    
    def changelist_view(self, request, extra_context=None):
        """Add pending teacher count to the changelist."""
        extra_context = extra_context or {}
        pending_count = User.objects.filter(
            role=User.Role.TEACHER,
            is_approved=False
        ).count()
        extra_context['pending_teachers_count'] = pending_count
        return super().changelist_view(request, extra_context=extra_context)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': (
                'first_name', 'last_name', 'phone', 'profile_picture'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'role',
                'is_verified', 'is_approved'
            )
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone')
        }),
        ('Permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_approved')
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'last_login')
    
    actions = ['approve_teachers', 'reject_teachers']
    
    def get_urls(self):
        """Add custom URL for individual teacher approval."""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'approve-teacher/',
                self.admin_site.admin_view(self.approve_teacher_individual),
                name='approve_teacher_individual',
            ),
        ]
        return custom_urls + urls
    
    def approve_teacher_individual(self, request):
        """Approve a single teacher account."""
        from django.http import HttpResponseRedirect
        from django.contrib import messages
        from apps.authentication.email_utils import send_teacher_approval_email
        
        teacher_id = request.GET.get('ids')
        if teacher_id:
            try:
                teacher = User.objects.get(id=teacher_id, role=User.Role.TEACHER)
                teacher.is_approved = True
                teacher.save()
                
                # Send approval email
                email_sent = send_teacher_approval_email(teacher, approved_by=request.user)
                
                if email_sent:
                    messages.success(
                        request,
                        f'Teacher {teacher.email} has been approved and notified via email.'
                    )
                else:
                    messages.warning(
                        request,
                        f'Teacher {teacher.email} has been approved but email notification failed.'
                    )
            except User.DoesNotExist:
                messages.error(request, 'Teacher not found.')
        
        return HttpResponseRedirect(reverse('admin:authentication_user_changelist'))
    
    def approve_teachers(self, request, queryset):
        """Approve selected teacher accounts."""
        from apps.authentication.email_utils import send_teacher_approval_email
        from django.contrib import messages
        
        teachers = queryset.filter(role=User.Role.TEACHER, is_approved=False)
        
        if not teachers.exists():
            messages.warning(request, 'No pending teacher accounts selected.')
            return
        
        count = 0
        email_count = 0
        failed_emails = []
        
        for teacher in teachers:
            teacher.is_approved = True
            teacher.save()
            count += 1
            
            # Send approval email
            if send_teacher_approval_email(teacher, approved_by=request.user):
                email_count += 1
            else:
                failed_emails.append(teacher.email)
        
        # Success message
        messages.success(
            request, 
            f'✓ Successfully approved {count} teacher account(s). {email_count} notification email(s) sent.'
        )
        
        # Warning for failed emails
        if failed_emails:
            messages.warning(
                request,
                f'⚠ Email notification failed for: {", ".join(failed_emails)}'
            )
    
    approve_teachers.short_description = '✓ Approve selected teacher accounts and send emails'
    
    def reject_teachers(self, request, queryset):
        """Delete selected pending teacher accounts."""
        from django.contrib import messages
        
        teachers = queryset.filter(role=User.Role.TEACHER, is_approved=False)
        
        if not teachers.exists():
            messages.warning(request, 'No pending teacher accounts selected.')
            return
        
        count = teachers.count()
        teacher_emails = list(teachers.values_list('email', flat=True))
        teachers.delete()
        
        messages.success(
            request, 
            f'✗ Rejected and deleted {count} teacher account(s): {", ".join(teacher_emails)}'
        )
    
    reject_teachers.short_description = '✗ Reject and delete selected teacher accounts'


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """Admin interface for LoginLog model."""
    
    list_display = (
        'user', 'ip_address', 'success', 'failure_reason', 'timestamp'
    )
    list_filter = ('success', 'timestamp')
    search_fields = ('user__email', 'ip_address')
    readonly_fields = ('user', 'ip_address', 'user_agent', 'success',
                      'failure_reason', 'timestamp')
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        """Prevent manual addition of logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow superusers to delete logs (needed for cascade deletes)."""
        return request.user.is_superuser


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Admin interface for EmailVerificationToken model."""
    
    list_display = (
        'user', 'token', 'is_used', 'is_expired_status', 'created_at', 'expires_at'
    )
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('user', 'token', 'created_at', 'expires_at', 'is_used')
    ordering = ('-created_at',)
    
    def is_expired_status(self, obj):
        """Display expiration status."""
        return obj.is_expired()
    is_expired_status.short_description = 'Is Expired'
    is_expired_status.boolean = True
    
    def has_add_permission(self, request):
        """Prevent manual addition of tokens."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Allow deletion of old tokens."""
        return True
