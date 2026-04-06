/**
 * Orders Management JavaScript Module
 * Handles all order-related functionality with modern practices
 */

class OrderManager {
    constructor() {
        this.API_BASE_URL = '/marketplace/api/orders/';
        this.REQUEST_TIMEOUT = 5000;
        this.currentOrder = null;
        this.filters = {
            status: '',
            is_returned: '',
            search: '',
            days: ''
        };
        this.init();
    }

    /**
     * Initialize the order manager
     */
    init() {
        this.bindEvents();
        this.loadOrders();
    }

    /**
     * Bind all event listeners
     */
    bindEvents() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupFilterListeners();
            this.setupModalListeners();
            this.setupOrderFormListener();
            this.setupUpdateFormListener();
        });
    }

    /**
     * Setup filter event listeners
     */
    setupFilterListeners() {
        const filterElements = [
            'statusFilter',
            'returnFilter', 
            'searchInput',
            'dateFilter'
        ];

        filterElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                const event = element.tagName === 'INPUT' ? 'input' : 'change';
                element.addEventListener(event, this.debounce(() => {
                    this.updateFilters();
                    this.loadOrders(1);
                }, 300));
            }
        });
    }

    /**
     * Setup modal event listeners
     */
    setupModalListeners() {
        const addOrderModal = document.getElementById('addOrderModal');
        if (addOrderModal) {
            addOrderModal.addEventListener('show.bs.modal', () => {
                this.initializeDatePicker();
                this.resetForm('addOrderForm');
            });
        }

        const updateOrderModal = document.getElementById('updateOrderModal');
        if (updateOrderModal) {
            updateOrderModal.addEventListener('show.bs.modal', () => {
                this.initializeDatePicker();
            });
        }
    }

    /**
     * Update filters object from UI
     */
    updateFilters() {
        this.filters = {
            status: this.getElementValue('statusFilter'),
            is_returned: this.getElementValue('returnFilter'),
            search: this.getElementValue('searchInput'),
            days: this.getElementValue('dateFilter')
        };
    }

    /**
     * Load orders with error handling and timeout
     */
    async loadOrders(page = 1) {
        try {
            const url = this.buildApiUrl(page);
            const data = await this.makeRequest(url);
            
            if (data) {
                this.displayOrders(data.results || data || []);
                this.setupPagination(data.count, page);
            }
        } catch (error) {
            this.handleLoadError(error);
        }
    }

    /**
     * Build API URL with filters
     */
    buildApiUrl(page) {
        const params = new URLSearchParams({ page });
        
        Object.entries(this.filters).forEach(([key, value]) => {
            if (value) params.append(key, value);
        });

        return `${this.API_BASE_URL}my_orders/?${params}`;
    }

    /**
     * Make HTTP request with timeout and abort controller
     */
    async makeRequest(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.REQUEST_TIMEOUT);
        
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCsrfToken(),
                    ...options.headers
                },
                ...options
            });
            
            clearTimeout(timeoutId);
            const data = await response.json();
            
            if (!response.ok) {
                const parsedError = this.extractErrorMessage(data);
                throw new Error(parsedError || `HTTP ${response.status}: ${response.statusText}`);
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
     * Display orders or show appropriate message
     */
    displayOrders(orders) {
        const container = document.getElementById('ordersList');
        if (!container) return;

        if (!orders?.length) {
            this.showMessage({
                type: 'empty',
                title: 'No Orders Found',
                message: 'You do not have any orders yet.',
                actionLabel: 'Create Your First Order',
                action: () => this.openModal('addOrderModal')
            });
            return;
        }

        container.innerHTML = orders.map(order => this.generateOrderCard(order)).join('');
    }

    /**
     * Generate HTML for order card
     */
    generateOrderCard(order) {
        const statusColor = this.getStatusColor(order.status);
        const returnBadge = order.is_returned ? 
            '<span class="badge bg-danger ms-2">Returned</span>' : '';

        return `
            <div class="card mb-3 shadow border-0 order-card" 
                 style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border: 2px solid #00FFFF !important;">
                <div class="card-body">
                    <div class="row align-items-center">
                        ${this.generateOrderInfo(order)}
                        ${this.generateOrderActions(order.id)}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Generate order information columns
     */
    generateOrderInfo(order) {
        return `
            <div class="col-md-2">
                <small style="color: #888;">Order Number</small>
                <h6 style="color: #00FFFF;">${order.order_number || '#' + order.id}</h6>
                <small style="color: #888;">${this.formatDate(order.order_date)}</small>
            </div>
            <div class="col-md-2">
                <small style="color: #888;">Customer</small>
                <h6 style="color: #FFFFFF;">${order.customer_email}</h6>
            </div>
            <div class="col-md-2">
                <small style="color: #888;">Amount</small>
                <h6 style="color: #00FF00;">$${parseFloat(order.order_amount).toFixed(2)}</h6>
            </div>
            <div class="col-md-2">
                <small style="color: #888;">Status</small>
                <h6>
                    <span class="badge" style="background-color: ${this.getStatusColor(order.status)};">
                        ${order.status.toUpperCase()}
                    </span>
                    ${order.is_returned ? '<span class="badge bg-danger ms-2">Returned</span>' : ''}
                </h6>
            </div>
            <div class="col-md-2">
                <small style="color: #888;">Delivery</small>
                <h6 style="color: #00FFFF;">${order.delivery_days || 'N/A'} days</h6>
            </div>
        `;
    }

    /**
     * Generate order action buttons
     */
    generateOrderActions(orderId) {
        return `
            <div class="col-md-2 text-end">
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-info" 
                            onclick="orderManager.updateOrderStatus(${orderId})" 
                            title="Update Status">
                        <i class="bi bi-pencil-square"></i>
                    </button>
                    <button class="btn btn-sm" 
                            style="background: linear-gradient(135deg, #00FFFF 0%, #00CED1 100%); color: #000; font-weight: bold;"
                            onclick="orderManager.viewOrderDetail(${orderId})" 
                            title="View Details">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" 
                            onclick="orderManager.deleteOrder(${orderId})" 
                            title="Delete Order">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Show message in orders container
     */
    showMessage({ type = 'info', title, message, actionLabel, action }) {
        const container = document.getElementById('ordersList');
        if (!container) return;

        const config = this.getMessageConfig(type);
        const actionButton = action && actionLabel ? 
            `<button class="btn btn-lg mt-3" 
                     style="background: linear-gradient(135deg, #00FF00 0%, #00CED1 100%); color: #000; font-weight: bold;"
                     onclick="${action.name || 'orderManager.handleAction'}()">
                <i class="${config.actionIcon}"></i> ${actionLabel}
            </button>` : '';

        container.innerHTML = `
            <div class="card shadow border-0" 
                 style="background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); border: 2px solid ${config.borderColor} !important;">
                <div class="card-body text-center py-5">
                    <i class="${config.icon}" style="font-size: 4rem; color: ${config.iconColor};"></i>
                    <h4 class="mt-3" style="color: ${config.titleColor};">${title}</h4>
                    <p style="color: #888;">${message}</p>
                    ${actionButton}
                </div>
            </div>
        `;

        this.hidePagination();
        
        // Store action for later execution
        if (action && typeof action === 'function') {
            window.orderManager.handleAction = action;
        }
    }

    /**
     * Get message configuration based on type
     */
    getMessageConfig(type) {
        const configs = {
            empty: {
                icon: 'bi-inbox',
                borderColor: '#00FFFF',
                iconColor: '#888',
                titleColor: '#00FFFF',
                actionIcon: 'bi-plus-circle'
            },
            error: {
                icon: 'bi-exclamation-circle',
                borderColor: '#FF6B6B',
                iconColor: '#FF6B6B',
                titleColor: '#FF6B6B',
                actionIcon: 'bi-arrow-clockwise'
            },
            timeout: {
                icon: 'bi-clock',
                borderColor: '#FF6B6B',
                iconColor: '#FF6B6B',
                titleColor: '#FF6B6B',
                actionIcon: 'bi-arrow-clockwise'
            }
        };
        return configs[type] || configs.error;
    }

    /**
     * Handle load errors
     */
    handleLoadError(error) {
        const isTimeout = error.message.includes('timeout');
        this.showMessage({
            type: isTimeout ? 'timeout' : 'error',
            title: isTimeout ? 'Request Timeout' : 'Error Loading Orders',
            message: error.message,
            actionLabel: 'Retry',
            action: () => this.loadOrders(1)
        });
    }

    /**
     * Create new order
     */
    async createOrder(formData) {
        try {
            const data = await this.makeRequest(this.API_BASE_URL, {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            
            this.showAlert('Order created successfully!', 'success');
            this.closeModal('addOrderModal');
            this.loadOrders(1);
            
        } catch (error) {
            this.showFormError('addOrderForm', error.message);
        }
    }

    /**
     * Update order status
     */
    async updateOrderStatus(orderId) {
        try {
            const order = await this.makeRequest(`${this.API_BASE_URL}${orderId}/`);
            this.currentOrder = order;
            this.populateUpdateForm(order);
            setTimeout(() => {
                this.openModal('updateOrderModal');
            }, 100);
        } catch (error) {
            console.error('Error loading order:', error);
            this.showAlert('Failed to load order details: ' + error.message, 'danger');
        }
    }

    /**
     * Delete order with confirmation
     */
    async deleteOrder(orderId) {
        if (!confirm('Are you sure you want to delete this order? This action cannot be undone.')) {
            return;
        }

        try {
            await this.makeRequest(`${this.API_BASE_URL}${orderId}/`, {
                method: 'DELETE'
            });
            
            this.showAlert('Order deleted successfully!', 'success');
            // Ensure orders are refreshed
            await this.loadOrders(1);
            
        } catch (error) {
            this.showAlert('Failed to delete order: ' + error.message, 'danger');
        }
    }

    // Utility methods
    getStatusColor(status) {
        const colors = {
            pending: '#6c757d',
            processing: '#0d6efd',
            shipped: '#fd7e14',
            delivered: '#198754',
            cancelled: '#dc3545',
            returned: '#6f42c1'
        };
        return colors[status] || colors.pending;
    }

    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString();
    }

    getElementValue(id) {
        const element = document.getElementById(id);
        return element ? element.value.trim() : '';
    }

    getCsrfToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            new bootstrap.Modal(modal).show();
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            bootstrap.Modal.getInstance(modal)?.hide();
        }
    }

    resetForm(formId) {
        const form = document.getElementById(formId);
        if (form) {
            form.reset();
            // Clear any error messages
            const errorDiv = form.querySelector('.alert-danger');
            if (errorDiv) {
                errorDiv.classList.add('d-none');
            }
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const toastId = type === 'error' ? 'errorToast' : 'successToast';
        const messageId = type === 'error' ? 'errorToastMessage' : 'successToastMessage';
        
        const toast = document.getElementById(toastId);
        const messageElement = document.getElementById(messageId);
        
        if (toast && messageElement) {
            messageElement.textContent = message;
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
        }
    }

    showAlert(message, type = 'info') {
        this.showToast(message, type);
    }

    showFormError(formId, message) {
        const form = document.getElementById(formId);
        const errorDiv = form?.querySelector('.alert-danger');
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('d-none');
        } else {
            this.showToast(message, 'error');
        }
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short', 
            day: 'numeric'
        });
    }

    /**
     * Format datetime for display
     */
    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        return new Date(dateString).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Format datetime for datetime-local input
     */
    formatDateTimeLocal(dateString) {
        if (!dateString) return '';
        return new Date(dateString).toISOString().slice(0, 16);
    }

    setupPagination(totalCount, currentPage) {
        const paginationNav = document.getElementById('paginationNav');
        const paginationList = document.getElementById('paginationList');
        
        if (!paginationNav || !paginationList) return;

        const itemsPerPage = 20;
        const totalPages = Math.ceil(totalCount / itemsPerPage);
        
        if (totalPages <= 1) {
            this.hidePagination();
            return;
        }

        paginationList.innerHTML = '';
        
        // Previous button
        const prevItem = this.createPaginationItem(
            currentPage - 1, 
            'Previous', 
            currentPage === 1
        );
        paginationList.appendChild(prevItem);

        // Page numbers
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        for (let page = startPage; page <= endPage; page++) {
            const pageItem = this.createPaginationItem(
                page, 
                page.toString(), 
                false, 
                page === currentPage
            );
            paginationList.appendChild(pageItem);
        }

        // Next button
        const nextItem = this.createPaginationItem(
            currentPage + 1, 
            'Next', 
            currentPage === totalPages
        );
        paginationList.appendChild(nextItem);

        paginationNav.classList.remove('d-none');
    }

    /**
     * Create pagination item
     */
    createPaginationItem(page, text, disabled = false, active = false) {
        const li = document.createElement('li');
        li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`;
        
        const a = document.createElement('a');
        a.className = 'page-link';
        a.href = '#';
        a.textContent = text;
        
        if (!disabled && !active) {
            a.addEventListener('click', (e) => {
                e.preventDefault();
                this.loadOrders(page);
            });
        }
        
        li.appendChild(a);
        return li;
    }

    hidePagination() {
        const paginationNav = document.getElementById('paginationNav');
        if (paginationNav) {
            paginationNav.classList.add('d-none');
        }
    }

    initializeDatePicker() {
        const dateInputs = document.querySelectorAll('input[type="datetime-local"]');
        dateInputs.forEach(input => {
            if (!input.value) {
                input.value = new Date().toISOString().slice(0, 16);
            }
        });
    }

    /**
     * Setup order creation form listener
     */
    setupOrderFormListener() {
        const form = document.getElementById('addOrderForm');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.submitOrderForm();
            });
        }
    }

    /**
     * Setup order update form listener  
     */
    setupUpdateFormListener() {
        const form = document.getElementById('updateOrderForm');
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                await this.submitUpdateForm();
            });
        }
    }

    /**
     * Submit order creation form
     */
    async submitOrderForm() {
        const form = document.getElementById('addOrderForm');
        const formData = new FormData(form);
        
        const orderData = {
            customer_email: formData.get('customer_email'),
            order_amount: parseFloat(formData.get('order_amount')),
            order_date: formData.get('order_date'),
            delivery_date: formData.get('delivery_date') || null,
            status: formData.get('status'),
            is_returned: formData.get('is_returned') === 'true'
        };

        await this.createOrder(orderData);
    }

    /**
     * Submit order update form
     */
    async submitUpdateForm() {
        const orderId = document.getElementById('updateOrderId').value;
        const form = document.getElementById('updateOrderForm');
        const formData = new FormData(form);
        
        const updateData = {
            status: formData.get('status')
        };

        // Status-specific fields expected by backend serializer.
        if (updateData.status === 'shipped') {
            const existingShippedDate = this.currentOrder?.shipped_date;
            updateData.shipped_date = existingShippedDate || new Date().toISOString();
        }

        // Add delivery date if status is delivered
        if (updateData.status === 'delivered') {
            const deliveryDate = formData.get('delivery_date');
            if (!deliveryDate) {
                this.showFormError('updateOrderForm', 'Delivery date is required when status is delivered');
                return;
            }
            updateData.delivered_date = deliveryDate;
        }

        try {
            await this.makeRequest(`${this.API_BASE_URL}${orderId}/`, {
                method: 'PATCH',
                body: JSON.stringify(updateData)
            });
            
            this.showToast('Order updated successfully!', 'success');
            this.closeModal('updateOrderModal');
            this.loadOrders(1);
            
        } catch (error) {
            this.showFormError('updateOrderForm', error.message);
        }
    }

    /**
     * Validate form before submission
     */
    validateForm(form) {
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

    /**
     * View order details in modal
     */
    async viewOrderDetail(orderId) {
        try {
            const order = await this.makeRequest(`${this.API_BASE_URL}${orderId}/`);
            this.displayOrderDetails(order);
            setTimeout(() => {
                this.openModal('orderDetailModal');
            }, 100);
        } catch (error) {
            console.error('Error loading order details:', error);
            this.showToast('Failed to load order details: ' + error.message, 'error');
        }
    }

    /**
     * Display order details in modal
     */
    displayOrderDetails(order) {
        const content = document.getElementById('orderDetailContent');
        if (!content) return;

        const statusColor = this.getStatusColor(order.status);
        const returnBadge = order.is_returned ? 
            '<span class="badge bg-danger">Returned</span>' : 
            '<span class="badge bg-success">Not Returned</span>';

        content.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <h6 class="text-muted">Order Information</h6>
                    <table class="table table-borderless">
                        <tr>
                            <td><strong>Order Number:</strong></td>
                            <td class="text-primary">${order.order_number || '#' + order.id}</td>
                        </tr>
                        <tr>
                            <td><strong>Customer Email:</strong></td>
                            <td>${order.customer_email}</td>
                        </tr>
                        <tr>
                            <td><strong>Order Amount:</strong></td>
                            <td class="text-success">$${parseFloat(order.order_amount).toFixed(2)}</td>
                        </tr>
                        <tr>
                            <td><strong>Order Date:</strong></td>
                            <td>${this.formatDateTime(order.order_date)}</td>
                        </tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-muted">Status & Delivery</h6>
                    <table class="table table-borderless">
                        <tr>
                            <td><strong>Status:</strong></td>
                            <td>
                                <span class="badge" style="background-color: ${statusColor};">
                                    ${order.status.toUpperCase()}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td><strong>Return Status:</strong></td>
                            <td>${returnBadge}</td>
                        </tr>
                        <tr>
                            <td><strong>Delivery Date:</strong></td>
                            <td>${order.delivered_date ? this.formatDateTime(order.delivered_date) : 'Not set'}</td>
                        </tr>
                        <tr>
                            <td><strong>Delivery Days:</strong></td>
                            <td class="text-info">${order.delivery_days || 'N/A'} days</td>
                        </tr>
                    </table>
                </div>
            </div>
        `;
    }

    /**
     * Populate update form with order data
     */
    populateUpdateForm(order) {
        if (!order || typeof order !== 'object') {
            console.error('Invalid order object:', order);
            throw new Error('Order data is invalid');
        }
        
        document.getElementById('updateOrderId').value = order.id || '';
        document.getElementById('updateOrderStatus').value = order.status || '';
        
        // Set is_returned safely, defaulting to false if undefined
        const isReturned = order.is_returned !== undefined ? order.is_returned : false;
        document.getElementById('updateIsReturned').value = isReturned.toString();
        
        // Handle delivery date visibility
        const deliveryContainer = document.getElementById('updateDeliveryDateContainer');
        const deliveryInput = document.getElementById('updateDeliveryDate');
        
        if (order.status === 'delivered') {
            deliveryContainer.style.display = 'block';
            deliveryInput.required = true;
            if (order.delivered_date) {
                deliveryInput.value = this.formatDateTimeLocal(order.delivered_date);
            }
        } else {
            deliveryContainer.style.display = 'none';
            deliveryInput.required = false;
        }
    }

    /**
     * Extract readable API error message from DRF error responses.
     */
    extractErrorMessage(data) {
        if (!data) return '';
        if (typeof data === 'string') return data;
        if (data.detail) return data.detail;

        const firstKey = Object.keys(data)[0];
        if (!firstKey) return '';

        const value = data[firstKey];
        if (Array.isArray(value) && value.length) {
            return `${firstKey}: ${value[0]}`;
        }

        if (typeof value === 'string') {
            return `${firstKey}: ${value}`;
        }

        return 'Request failed. Please check your input and try again.';
    }

    /**
     * Apply filters and reload orders
     */
    applyFilters() {
        this.updateFilters();
        this.loadOrders(1);
    }

    /**
     * Clear all filters and reload orders
     */
    clearFilters() {
        document.getElementById('statusFilter').value = '';
        document.getElementById('returnFilter').value = '';
        document.getElementById('searchInput').value = '';
        document.getElementById('dateFilter').value = '';
        this.filters = { status: '', is_returned: '', search: '', days: '' };
        this.loadOrders(1);
    }
}

// Initialize the order manager
const orderManager = new OrderManager();

// Export for global access
window.orderManager = orderManager;
