/**
 * Family Genealogy System - Frontend Utilities
 *
 * Most utility functions (api, apiGet, apiPost, etc.) are defined inline in base.html
 * because they depend on Jinja2 template rendering.
 *
 * This file contains additional reusable components.
 */

// Date formatting helper
function formatDate(dateStr) {
    if (!dateStr) return '未知';
    return new Date(dateStr).toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Calculate age from birth and death dates
function calculateAge(birthDate, deathDate) {
    if (!birthDate) return null;
    const birth = new Date(birthDate);
    const end = deathDate ? new Date(deathDate) : new Date();
    let age = end.getFullYear() - birth.getFullYear();
    const m = end.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && end.getDate() < birth.getDate())) {
        age--;
    }
    return age;
}

// Debounce utility
function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(el) {
        return new bootstrap.Tooltip(el);
    });
});

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Handle window resize for ECharts
window.addEventListener('resize', function() {
    // ECharts instances auto-resize if they use percentage dimensions
    const charts = document.querySelectorAll('[id$="-chart"]');
    charts.forEach(function(el) {
        const instance = echarts.getInstanceByDom(el);
        if (instance) {
            instance.resize();
        }
    });
});
