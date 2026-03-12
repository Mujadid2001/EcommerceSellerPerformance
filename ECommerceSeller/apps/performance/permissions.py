"""
Optimized Permissions for Performance app following industry standards
"""
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist


class BaseCustomPermission(BasePermission):
    """
    Base permission class with common functionality
    """
    
    def has_permission(self, request, view):
        """Check basic permission requirements"""
        return request.user and request.user.is_authenticated
    
    def get_object_owner(self, obj):
        """Override to define how to get object owner"""
        raise NotImplementedError("Subclasses must implement get_object_owner")
    
    def has_object_permission(self, request, view, obj):
        """Check object-level permissions"""
        if not self.has_permission(request, view):
            return False
        
        return self.check_object_ownership(request.user, obj)
    
    def check_object_ownership(self, user, obj):
        """Check if user owns the object"""
        try:
            owner = self.get_object_owner(obj)
            return user == owner
        except (AttributeError, ObjectDoesNotExist):
            return False


class IsSellerOwner(BaseCustomPermission):
    """
    Permission to check if user owns the seller profile
    """
    
    message = "You can only access your own seller profile."
    
    def has_permission(self, request, view):
        """Check if user has seller profile"""
        if not super().has_permission(request, view):
            return False
        
        # Check if user has seller profile for create/list actions
        if view.action in ['create', 'list']:
            return hasattr(request.user, 'seller_profile')
        
        return True
    
    def get_object_owner(self, obj):
        """Get seller profile owner"""
        return obj.user
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the seller profile"""
        return self.check_object_ownership(request.user, obj)


class IsOrderOwner(BaseCustomPermission):
    """
    Permission to check if user owns the order through their seller profile
    """
    
    message = "You can only access orders from your seller profile."
    
    def has_permission(self, request, view):
        """Check if user has seller profile for order operations"""
        if not super().has_permission(request, view):
            return False
        
        # Require seller profile for all order operations
        return hasattr(request.user, 'seller_profile')
    
    def get_object_owner(self, obj):
        """Get order owner through seller"""
        return obj.seller.user
    
    def has_object_permission(self, request, view, obj):
        """Check if user owns the order"""
        return self.check_object_ownership(request.user, obj)


class IsFeedbackOwner(BaseCustomPermission):
    """
    Permission to check if user can access feedback for their orders
    """
    
    message = "You can only access feedback for your orders."
    
    def has_permission(self, request, view):
        """Check if user has seller profile"""
        if not super().has_permission(request, view):
            return False
        
        return hasattr(request.user, 'seller_profile')
    
    def get_object_owner(self, obj):
        """Get feedback owner through order seller"""
        return obj.order.seller.user
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access the feedback"""
        return self.check_object_ownership(request.user, obj)


class IsAdminOrOwner(BaseCustomPermission):
    """
    Permission for admin users or object owners
    """
    
    message = "You must be an admin or the owner of this object."
    
    def has_permission(self, request, view):
        """Allow admin users or authenticated users"""
        if not super().has_permission(request, view):
            return False
        
        return request.user.is_staff or request.user.is_superuser
    
    def get_object_owner(self, obj):
        """Override in subclasses based on object type"""
        if hasattr(obj, 'user'):
            return obj.user
        elif hasattr(obj, 'seller') and hasattr(obj.seller, 'user'):
            return obj.seller.user
        else:
            raise NotImplementedError("Cannot determine object owner")
    
    def has_object_permission(self, request, view, obj):
        """Allow admin users or owners"""
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        return self.check_object_ownership(request.user, obj)


class ReadOnlyOrOwner(BaseCustomPermission):
    """
    Permission for read-only access to all, write access to owners only
    """
    
    message = "You can only modify objects you own."
    
    def has_permission(self, request, view):
        """Allow all authenticated users for read operations"""
        if not super().has_permission(request, view):
            return False
        
        # Allow read operations for all authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Require ownership for write operations
        return True  # Object-level check will handle ownership
    
    def get_object_owner(self, obj):
        """Override based on object type"""
        if hasattr(obj, 'user'):
            return obj.user
        elif hasattr(obj, 'seller') and hasattr(obj.seller, 'user'):
            return obj.seller.user
        else:
            raise NotImplementedError("Cannot determine object owner")
    
    def has_object_permission(self, request, view, obj):
        """Allow read to all, write to owners only"""
        # Allow read operations
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Check ownership for write operations
        return self.check_object_ownership(request.user, obj)


class IsSellerActive(BasePermission):
    """
    Permission to check if seller is active
    """
    
    message = "Your seller account is not active."
    
    def has_permission(self, request, view):
        """Check if user is authenticated and has active seller profile"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        try:
            seller = request.user.seller_profile
            return seller.status == 'active'
        except ObjectDoesNotExist:
            return False


class CanManageOrders(BasePermission):
    """
    Permission for order management operations
    """
    
    message = "You don't have permission to manage orders."
    
    def has_permission(self, request, view):
        """Check order management permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has seller profile
        if not hasattr(request.user, 'seller_profile'):
            return False
        
        # Check seller status for write operations
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            seller = request.user.seller_profile
            return seller.status in ['active', 'pending']
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check object-level order management permissions"""
        if not hasattr(request.user, 'seller_profile'):
            return False
        
        # Check if order belongs to user's seller profile
        if obj.seller != request.user.seller_profile:
            return False
        
        # Additional restrictions based on order status
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            # Prevent modifications to certain statuses
            if obj.status in ['cancelled', 'returned']:
                return False
        
        return True


# ==================== PERMISSION MIXINS ====================

class SellerRequiredMixin:
    """
    Mixin to require seller profile for view access
    """
    
    def get_permissions(self):
        """Add seller requirement to permissions"""
        permissions = super().get_permissions()
        permissions.append(IsSellerOwner())
        return permissions


class ActiveSellerRequiredMixin:
    """
    Mixin to require active seller profile
    """
    
    def get_permissions(self):
        """Add active seller requirement to permissions"""
        permissions = super().get_permissions()
        permissions.extend([IsSellerOwner(), IsSellerActive()])
        return permissions


# ==================== PERMISSION UTILITIES ====================

class PermissionUtils:
    """
    Utility class for permission-related operations
    """
    
    @staticmethod
    def check_seller_exists(user):
        """Check if user has seller profile"""
        try:
            return hasattr(user, 'seller_profile') and user.seller_profile is not None
        except ObjectDoesNotExist:
            return False
    
    @staticmethod
    def check_seller_active(user):
        """Check if user has active seller profile"""
        try:
            seller = user.seller_profile
            return seller.status == 'active'
        except ObjectDoesNotExist:
            return False
    
    @staticmethod
    def get_user_seller(user):
        """Get seller profile for user safely"""
        try:
            return user.seller_profile
        except ObjectDoesNotExist:
            return None
    
    @staticmethod
    def check_order_ownership(user, order):
        """Check if user owns the order"""
        try:
            return order.seller == user.seller_profile
        except ObjectDoesNotExist:
            return False
    
    @staticmethod
    def can_modify_order(user, order):
        """Check if user can modify the order"""
        if not PermissionUtils.check_order_ownership(user, order):
            return False
        
        # Check order status restrictions
        restricted_statuses = ['cancelled', 'returned']
        return order.status not in restricted_statuses


# ==================== PERMISSION DECORATORS ====================

def seller_required(view_func):
    """
    Decorator to require seller profile
    """
    def wrapper(request, *args, **kwargs):
        if not PermissionUtils.check_seller_exists(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Seller profile required")
        return view_func(request, *args, **kwargs)
    return wrapper


def active_seller_required(view_func):
    """
    Decorator to require active seller profile
    """
    def wrapper(request, *args, **kwargs):
        if not PermissionUtils.check_seller_active(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Active seller profile required")
        return view_func(request, *args, **kwargs)
    return wrapper


# ==================== EXPORTS ====================

__all__ = [
    'BaseCustomPermission',
    'IsSellerOwner',
    'IsOrderOwner', 
    'IsFeedbackOwner',
    'IsAdminOrOwner',
    'ReadOnlyOrOwner',
    'IsSellerActive',
    'CanManageOrders',
    'SellerRequiredMixin',
    'ActiveSellerRequiredMixin',
    'PermissionUtils',
    'seller_required',
    'active_seller_required'
]