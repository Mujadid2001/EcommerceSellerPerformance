/**
 * Utility functions for the E-commerce platform
 * Common helpers and constants
 */

// API Configuration
export const API_CONFIG = {
    BASE_URL: '/marketplace/api',
    TIMEOUT: 5000,
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 1000
};

// UI Constants
export const UI_CONSTANTS = {
    DEBOUNCE_DELAY: 300,
    TOAST_DURATION: 5000,
    ANIMATION_DURATION: 300,
    ITEMS_PER_PAGE: 20
};

// Status color mappings
export const STATUS_COLORS = {
    pending: '#6c757d',
    processing: '#0d6efd', 
    shipped: '#fd7e14',
    delivered: '#198754',
    cancelled: '#dc3545',
    returned: '#6f42c1'
};

// Date/Time Utilities
export class DateTimeUtil {
    /**
     * Format date for display
     */
    static formatDate(dateString, options = {}) {
        if (!dateString) return 'N/A';
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        };
        
        return new Date(dateString).toLocaleDateString('en-US', { ...defaultOptions, ...options });
    }

    /**
     * Format datetime for display
     */
    static formatDateTime(dateString, options = {}) {
        if (!dateString) return 'N/A';
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return new Date(dateString).toLocaleString('en-US', { ...defaultOptions, ...options });
    }

    /**
     * Format datetime for datetime-local input
     */
    static formatDateTimeLocal(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toISOString().slice(0, 16);
    }

    /**
     * Get current datetime in ISO format
     */
    static getCurrentDateTime() {
        return new Date().toISOString();
    }

    /**
     * Get current datetime for datetime-local input
     */
    static getCurrentDateTimeLocal() {
        return this.formatDateTimeLocal(this.getCurrentDateTime());
    }

    /**
     * Calculate days between dates
     */
    static daysBetween(startDate, endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const diffTime = Math.abs(end - start);
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    }
}

// HTTP Utilities
export class HttpUtil {
    /**
     * Get CSRF token from DOM
     */
    static getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    /**
     * Create request headers with CSRF token
     */
    static createHeaders(additionalHeaders = {}) {
        return {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCsrfToken(),
            ...additionalHeaders
        };
    }

    /**
     * Make HTTP request with timeout and error handling
     */
    static async makeRequest(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), options.timeout || API_CONFIG.TIMEOUT);

        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: this.createHeaders(options.headers),
                ...options
            });

            clearTimeout(timeoutId);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || data.message || `HTTP ${response.status}: ${response.statusText}`);
            }

            return data;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        }
    }

    /**
     * Build URL with query parameters
     */
    static buildUrl(baseUrl, params = {}) {
        const url = new URL(baseUrl, window.location.origin);
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                url.searchParams.append(key, value);
            }
        });

        return url.toString();
    }
}

// DOM Utilities
export class DOMUtil {
    /**
     * Get element by ID with optional validation
     */
    static getElementById(id, required = false) {
        const element = document.getElementById(id);
        
        if (required && !element) {
            console.warn(`Required element with ID '${id}' not found`);
        }
        
        return element;
    }

    /**
     * Get element value safely
     */
    static getElementValue(id, defaultValue = '') {
        const element = this.getElementById(id);
        return element ? element.value.trim() : defaultValue;
    }

    /**
     * Set element value safely
     */
    static setElementValue(id, value) {
        const element = this.getElementById(id);
        if (element) {
            element.value = value;
        }
    }

    /**
     * Toggle element visibility
     */
    static toggleElementVisibility(id, show) {
        const element = this.getElementById(id);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }

    /**
     * Add/remove CSS classes
     */
    static toggleClass(element, className, condition) {
        if (!element) return;
        
        if (condition) {
            element.classList.add(className);
        } else {
            element.classList.remove(className);
        }
    }

    /**
     * Create element with attributes and content
     */
    static createElement(tag, attributes = {}, content = '') {
        const element = document.createElement(tag);
        
        Object.entries(attributes).forEach(([key, value]) => {
            if (key === 'className') {
                element.className = value;
            } else if (key === 'innerHTML') {
                element.innerHTML = value;
            } else {
                element.setAttribute(key, value);
            }
        });
        
        if (content) {
            element.textContent = content;
        }
        
        return element;
    }
}

// Form Utilities
export class FormUtil {
    /**
     * Get form data as object
     */
    static getFormData(formElement) {
        const formData = new FormData(formElement);
        const data = {};
        
        for (const [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        return data;
    }

    /**
     * Reset form and clear errors
     */
    static resetForm(formId) {
        const form = DOMUtil.getElementById(formId);
        if (form) {
            form.reset();
            this.clearFormErrors(form);
        }
    }

    /**
     * Clear form error messages
     */
    static clearFormErrors(form) {
        const errorElements = form.querySelectorAll('.alert-danger, .is-invalid');
        errorElements.forEach(element => {
            if (element.classList.contains('alert-danger')) {
                element.classList.add('d-none');
            } else {
                element.classList.remove('is-invalid');
            }
        });
    }

    /**
     * Show form error message
     */
    static showFormError(formId, message) {
        const form = DOMUtil.getElementById(formId);
        const errorDiv = form?.querySelector('.alert-danger');
        
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('d-none');
        }
    }

    /**
     * Validate required fields
     */
    static validateRequiredFields(form) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        return isValid;
    }
}

// Toast/Notification Utilities
export class NotificationUtil {
    /**
     * Show toast notification
     */
    static showToast(message, type = 'info') {
        const toastId = type === 'error' ? 'errorToast' : 'successToast';
        const messageId = type === 'error' ? 'errorToastMessage' : 'successToastMessage';
        
        const toast = DOMUtil.getElementById(toastId);
        const messageElement = DOMUtil.getElementById(messageId);
        
        if (toast && messageElement) {
            messageElement.textContent = message;
            const bsToast = new bootstrap.Toast(toast, {
                delay: UI_CONSTANTS.TOAST_DURATION
            });
            bsToast.show();
        }
    }

    /**
     * Show success notification
     */
    static showSuccess(message) {
        this.showToast(message, 'success');
    }

    /**
     * Show error notification
     */
    static showError(message) {
        this.showToast(message, 'error');
    }
}

// Modal Utilities
export class ModalUtil {
    /**
     * Open Bootstrap modal
     */
    static openModal(modalId) {
        const modal = DOMUtil.getElementById(modalId);
        if (modal) {
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        }
    }

    /**
     * Close Bootstrap modal
     */
    static closeModal(modalId) {
        const modal = DOMUtil.getElementById(modalId);
        if (modal) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        }
    }

    /**
     * Setup modal events
     */
    static setupModalEvents(modalId, events = {}) {
        const modal = DOMUtil.getElementById(modalId);
        if (!modal) return;

        Object.entries(events).forEach(([event, handler]) => {
            modal.addEventListener(event, handler);
        });
    }
}

// Debounce utility
export function debounce(func, wait, immediate = false) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };
        
        const callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        
        if (callNow) func(...args);
    };
}

// Throttle utility
export function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Number formatting utilities
export class NumberUtil {
    /**
     * Format currency
     */
    static formatCurrency(amount, currency = 'USD') {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency
        }).format(amount);
    }

    /**
     * Parse float safely
     */
    static parseFloat(value, defaultValue = 0) {
        const parsed = parseFloat(value);
        return isNaN(parsed) ? defaultValue : parsed;
    }

    /**
     * Format percentage
     */
    static formatPercentage(value, decimals = 1) {
        return `${(value * 100).toFixed(decimals)}%`;
    }
}

// String utilities
export class StringUtil {
    /**
     * Capitalize first letter
     */
    static capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Truncate string with ellipsis
     */
    static truncate(str, length, suffix = '...') {
        return str.length > length ? str.substring(0, length) + suffix : str;
    }

    /**
     * Escape HTML
     */
    static escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export all utilities as default
export default {
    API_CONFIG,
    UI_CONSTANTS,
    STATUS_COLORS,
    DateTimeUtil,
    HttpUtil,
    DOMUtil,
    FormUtil,
    NotificationUtil,
    ModalUtil,
    NumberUtil,
    StringUtil,
    debounce,
    throttle
};