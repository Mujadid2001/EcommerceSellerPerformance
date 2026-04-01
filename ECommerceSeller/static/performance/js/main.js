// Main JavaScript for Performance App

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Animate cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(function(entry) {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    const cards = document.querySelectorAll('.card');
    cards.forEach(function(card) {
        observer.observe(card);
    });

    // Format large numbers
    function formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    // Update score displays with animation
    const scoreElements = document.querySelectorAll('.performance-score, .metric-value');
    scoreElements.forEach(function(element) {
        const targetValue = parseFloat(element.textContent);
        if (!isNaN(targetValue)) {
            animateValue(element, 0, targetValue, 1000);
        }
    });

    function animateValue(element, start, end, duration) {
        const range = end - start;
        const increment = range / (duration / 16);
        let current = start;
        
        const timer = setInterval(function() {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            
            if (element.textContent.includes('$')) {
                element.textContent = '$' + current.toFixed(2);
            } else if (element.textContent.includes('.')) {
                element.textContent = current.toFixed(2);
            } else {
                element.textContent = Math.floor(current);
            }
        }, 16);
    }

    // API Helper Functions
    window.PerformanceAPI = {
        baseURL: '/api/',

        async getSellers(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${this.baseURL}sellers/?${queryString}`);
            return await response.json();
        },

        async getSellerDetail(id) {
            const response = await fetch(`${this.baseURL}sellers/${id}/`);
            return await response.json();
        },

        async getSellerMetrics(id) {
            const response = await fetch(`${this.baseURL}sellers/${id}/metrics/`);
            return await response.json();
        },

        async getSellerScoreBreakdown(id) {
            const response = await fetch(`${this.baseURL}sellers/${id}/score_breakdown/`);
            return await response.json();
        },

        async getOrders(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${this.baseURL}orders/?${queryString}`);
            return await response.json();
        },

        async getFeedback(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${this.baseURL}feedback/?${queryString}`);
            return await response.json();
        }
    };

    // Search functionality
    const searchInput = document.querySelector('#searchInput');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                performSearch(e.target.value);
            }, 500);
        });
    }

    function performSearch(query) {
        if (query.length < 2) return;
        
        // Implement search logic here
        console.log('Searching for:', query);
    }

    // Filter functionality
    const filterButtons = document.querySelectorAll('[data-filter]');
    filterButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const filter = this.dataset.filter;
            applyFilter(filter);
        });
    });

    function applyFilter(filter) {
        // Implement filter logic here
        console.log('Applying filter:', filter);
    }

    // Chart initialization (if needed)
    window.initPerformanceChart = function(elementId, data) {
        // Add chart library integration here (e.g., Chart.js)
        console.log('Chart data:', data);
    };

    
});
