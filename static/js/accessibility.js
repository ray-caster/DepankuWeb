/**
 * Accessibility Module for Depanku Application
 * Enhances keyboard navigation, screen reader support, and overall accessibility
 */

class AccessibilityManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupKeyboardNavigation();
        this.setupScreenReaderAnnouncements();
        this.setupFocusManagement();
        this.setupSkipLinks();
        this.setupHighContrastMode();
        this.setupReducedMotion();
        this.setupScreenReaderFriendlyMessages();
        this.setupAccessibleTooltips();
        this.setupLiveRegions();
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup enhanced keyboard navigation
     */
    setupKeyboardNavigation() {
        // Handle Tab key navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-user');
                this.removeKeyboardIndicator();
            }
        });

        // Handle Escape key for closing modals and menus
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeOpenModals();
                this.closeOpenMenus();
            }
        });

        // Handle Enter and Space for interactive elements
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                const activeElement = document.activeElement;
                if (activeElement && !activeElement.isContentEditable) {
                    e.preventDefault();
                    this.handleInteractiveKeydown(activeElement, e.key);
                }
            }
        });

        // Enhance focus styles
        this.enhanceFocusStyles();
    }

    /**
     * Setup screen reader announcements
     */
    setupScreenReaderAnnouncements() {
        this.announcementRegion = document.createElement('div');
        this.announcementRegion.setAttribute('role', 'status');
        this.announcementRegion.setAttribute('aria-live', 'polite');
        this.announcementRegion.setAttribute('aria-atomic', 'true');
        this.announcementRegion.className = 'sr-only';
        this.announcementRegion.style.position = 'absolute';
        this.announcementRegion.style.width = '1px';
        this.announcementRegion.style.height = '1px';
        this.announcementRegion.style.padding = '0';
        this.announcementRegion.style.margin = '-1px';
        this.announcementRegion.style.overflow = 'hidden';
        this.announcementRegion.style.clip = 'rect(0, 0, 0, 0)';
        this.announcementRegion.style.whiteSpace = 'nowrap';
        this.announcementRegion.style.border = '0';
        document.body.appendChild(this.announcementRegion);
    }

    /**
     * Announce messages to screen readers
     */
    announceToScreenReader(message, priority = 'polite') {
        const region = document.createElement('div');
        region.setAttribute('role', 'status');
        region.setAttribute('aria-live', priority);
        region.setAttribute('aria-atomic', 'true');
        region.className = 'sr-only';
        region.textContent = message;
        
        document.body.appendChild(region);
        
        // Remove after announcement
        setTimeout(() => {
            region.remove();
        }, 1000);
    }

    /**
     * Setup focus management
     */
    setupFocusManagement() {
        // Trap focus in modals
        const modals = document.querySelectorAll('[role="dialog"]');
        modals.forEach(modal => {
            modal.addEventListener('keydown', (e) => {
                if (e.key === 'Tab') {
                    this.trapFocus(modal, e);
                }
            });
        });

        // Restore focus when closing modals
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-close-modal]')) {
                const modal = e.target.closest('[role="dialog"]');
                if (modal) {
                    const trigger = document.querySelector(`[data-modal="${modal.id}"]`);
                    if (trigger) {
                        trigger.focus();
                    }
                }
            }
        });
    }

    /**
     * Trap focus within an element
     */
    trapFocus(element, event) {
        const focusableElements = element.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
            if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement.focus();
            }
        } else {
            if (document.activeElement === lastElement) {
                event.preventDefault();
                firstElement.focus();
            }
        }
    }

    /**
     * Setup skip links
     */
    setupSkipLinks() {
        const skipLinks = document.querySelectorAll('.skip-link');
        skipLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const target = document.getElementById(targetId);
                if (target) {
                    target.setAttribute('tabindex', '-1');
                    target.focus();
                    // Remove tabindex after focus
                    setTimeout(() => {
                        target.removeAttribute('tabindex');
                    }, 1000);
                }
            });
        });
    }

    /**
     * Setup high contrast mode
     */
    setupHighContrastMode() {
        const highContrastToggle = document.getElementById('high-contrast-toggle');
        if (highContrastToggle) {
            highContrastToggle.addEventListener('click', () => {
                document.body.classList.toggle('high-contrast');
                const isHighContrast = document.body.classList.contains('high-contrast');
                localStorage.setItem('highContrastMode', isHighContrast);
                this.announceToScreenReader(
                    isHighContrast ? 'High contrast mode enabled' : 'High contrast mode disabled'
                );
            });
        }

        // Restore saved preference
        const savedPreference = localStorage.getItem('highContrastMode');
        if (savedPreference === 'true') {
            document.body.classList.add('high-contrast');
        }
    }

    /**
     * Setup reduced motion preference
     */
    setupReducedMotion() {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (prefersReducedMotion.matches) {
            document.body.classList.add('reduce-motion');
        }

        prefersReducedMotion.addEventListener('change', (e) => {
            if (e.matches) {
                document.body.classList.add('reduce-motion');
            } else {
                document.body.classList.remove('reduce-motion');
            }
        });
    }

    /**
     * Setup screen reader friendly messages
     */
    setupScreenReaderFriendlyMessages() {
        // Enhance error messages
        const errorMessages = document.querySelectorAll('.alert-danger, .error-message');
        errorMessages.forEach(error => {
            error.setAttribute('role', 'alert');
            error.setAttribute('aria-live', 'assertive');
        });

        // Enhance success messages
        const successMessages = document.querySelectorAll('.alert-success');
        successMessages.forEach(success => {
            success.setAttribute('role', 'status');
            success.setAttribute('aria-live', 'polite');
        });
    }

    /**
     * Setup accessible tooltips
     */
    setupAccessibleTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(tooltip => {
            const tooltipText = tooltip.getAttribute('data-tooltip');
            
            // Create tooltip element
            const tooltipElement = document.createElement('div');
            tooltipElement.className = 'tooltip';
            tooltipElement.setAttribute('role', 'tooltip');
            tooltipElement.id = `tooltip-${tooltip.id || Math.random().toString(36).substr(2, 9)}`;
            tooltipElement.textContent = tooltipText;
            
            // Add tooltip to DOM
            document.body.appendChild(tooltipElement);
            
            // Position tooltip
            tooltip.addEventListener('mouseenter', () => {
                this.positionTooltip(tooltip, tooltipElement);
                tooltipElement.classList.add('show');
            });
            
            tooltip.addEventListener('mouseleave', () => {
                tooltipElement.classList.remove('show');
            });
            
            // Keyboard accessibility
            tooltip.addEventListener('focus', () => {
                this.positionTooltip(tooltip, tooltipElement);
                tooltipElement.classList.add('show');
            });
            
            tooltip.addEventListener('blur', () => {
                tooltipElement.classList.remove('show');
            });
            
            // Associate tooltip with element
            tooltip.setAttribute('aria-describedby', tooltipElement.id);
        });
    }

    /**
     * Position tooltip relative to element
     */
    positionTooltip(element, tooltip) {
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.bottom + 5}px`;
        tooltip.style.left = `${rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2)}px`;
    }

    /**
     * Setup live regions for dynamic content
     */
    setupLiveRegions() {
        // Create live region for dynamic content updates
        this.liveRegion = document.createElement('div');
        this.liveRegion.setAttribute('role', 'status');
        this.liveRegion.setAttribute('aria-live', 'polite');
        this.liveRegion.setAttribute('aria-atomic', 'true');
        this.liveRegion.className = 'sr-only';
        document.body.appendChild(this.liveRegion);
    }

    /**
     * Update live region content
     */
    updateLiveRegion(message) {
        this.liveRegion.textContent = message;
        // Clear after announcement
        setTimeout(() => {
            this.liveRegion.textContent = '';
        }, 1000);
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        // Ctrl/Cmd + K for search
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('input[type="search"], input[placeholder*="Search"]');
                if (searchInput) {
                    searchInput.focus();
                    this.announceToScreenReader('Search focused');
                }
            }
        });

        // Ctrl/Cmd + / for help
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                const helpButton = document.querySelector('[data-help]');
                if (helpButton) {
                    helpButton.click();
                    this.announceToScreenReader('Help opened');
                }
            }
        });

        // Alt + S for skip to main content
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                const skipLink = document.querySelector('.skip-link');
                if (skipLink) {
                    skipLink.click();
                }
            }
        });
    }

    /**
     * Enhance focus styles
     */
    enhanceFocusStyles() {
        const style = document.createElement('style');
        style.textContent = `
            *:focus {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
            }
            
            *:focus:not(:focus-visible) {
                outline: none;
            }
            
            *:focus-visible {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
            }
            
            .keyboard-user *:focus {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Handle interactive element keydown
     */
    handleInteractiveKeydown(element, key) {
        if (element.tagName === 'BUTTON' || element.getAttribute('role') === 'button') {
            element.click();
        } else if (element.tagName === 'A') {
            element.click();
        } else if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            // For form elements, let the browser handle it
            return;
        }
    }

    /**
     * Close all open modals
     */
    closeOpenModals() {
        const openModals = document.querySelectorAll('[role="dialog"][style*="display: block"], [role="dialog"][style*="display: flex"]');
        openModals.forEach(modal => {
            const closeButton = modal.querySelector('[data-close-modal]');
            if (closeButton) {
                closeButton.click();
            }
        });
    }

    /**
     * Close all open menus
     */
    closeOpenMenus() {
        const openMenus = document.querySelectorAll('.menu[style*="display: block"], .menu[style*="display: flex"]');
        openMenus.forEach(menu => {
            const toggleButton = menu.previousElementSibling;
            if (toggleButton && toggleButton.classList.contains('mobile-menu-toggle')) {
                toggleButton.click();
            }
        });
    }

    /**
     * Remove keyboard indicator after timeout
     */
    removeKeyboardIndicator() {
        clearTimeout(this.keyboardTimeout);
        this.keyboardTimeout = setTimeout(() => {
            document.body.classList.remove('keyboard-user');
        }, 5000);
    }

    /**
     * Announce page changes for single page applications
     */
    announcePageChange(pageTitle) {
        const message = `Navigated to ${pageTitle}`;
        this.announceToScreenReader(message, 'assertive');
    }

    /**
     * Announce form validation errors
     */
    announceFormErrors(errors) {
        const errorList = errors.map(error => error.message).join(', ');
        this.announceToScreenReader(`Form errors: ${errorList}`, 'assertive');
    }

    /**
     * Announce loading states
     */
    announceLoading(message = 'Loading content') {
        this.announceToScreenReader(message, 'polite');
    }

    /**
     * Announce completion states
     */
    announceCompletion(message = 'Content loaded successfully') {
        this.announceToScreenReader(message, 'polite');
    }
}

// Initialize accessibility when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const accessibilityManager = new AccessibilityManager();
    
    // Make it globally available
    window.AccessibilityManager = AccessibilityManager;
    window.accessibilityManager = accessibilityManager;
    
    // Announce page load
    accessibilityManager.announceToScreenReader('Page loaded successfully');
});

// Export for use in other modules
window.AccessibilityManager = AccessibilityManager;