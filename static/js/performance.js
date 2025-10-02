/**
 * Performance Optimization Module for Depanku
 * Handles lazy loading, resource hints, critical CSS, and caching optimizations
 */

class PerformanceOptimizer {
    constructor() {
        this.init();
    }

    init() {
        this.setupLazyLoading();
        this.setupResourceHints();
        this.setupCriticalCSS();
        this.setupCaching();
        this.setupIntersectionObserver();
        this.setupPreload();
    }

    /**
     * Setup lazy loading for images and iframes
     */
    setupLazyLoading() {
        // Lazy load images
        const lazyImages = document.querySelectorAll('img[data-src], img[data-srcset]');
        
        if ('loading' in HTMLImageElement.prototype) {
            // Native lazy loading support
            lazyImages.forEach(img => {
                img.loading = 'lazy';
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                }
                if (img.dataset.srcset) {
                    img.srcset = img.dataset.srcset;
                }
            });
        } else {
            // Fallback for browsers that don't support native lazy loading
            this.setupIntersectionObserverForImages(lazyImages);
        }

        // Lazy load iframes
        const lazyIframes = document.querySelectorAll('iframe[data-src]');
        this.setupIntersectionObserverForIframes(lazyIframes);
    }

    /**
     * Setup Intersection Observer for images fallback
     */
    setupIntersectionObserverForImages(images) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                    }
                    if (img.dataset.srcset) {
                        img.srcset = img.dataset.srcset;
                    }
                    img.removeAttribute('data-src');
                    img.removeAttribute('data-srcset');
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });

        images.forEach(img => imageObserver.observe(img));
    }

    /**
     * Setup Intersection Observer for iframes
     */
    setupIntersectionObserverForIframes(iframes) {
        const iframeObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const iframe = entry.target;
                    iframe.src = iframe.dataset.src;
                    iframe.removeAttribute('data-src');
                    observer.unobserve(iframe);
                }
            });
        }, {
            rootMargin: '200px 0px',
            threshold: 0.01
        });

        iframes.forEach(iframe => iframeObserver.observe(iframe));
    }

    /**
     * Setup resource hints for better performance
     */
    setupResourceHints() {
        // Preconnect to external domains
        const preconnectDomains = [
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com',
            'https://www.google-analytics.com',
            'https://stats.g.doubleclick.net'
        ];

        preconnectDomains.forEach(domain => {
            const link = document.createElement('link');
            link.rel = 'preconnect';
            link.href = domain;
            link.crossOrigin = 'anonymous';
            document.head.appendChild(link);
        });

        // DNS prefetch for domains we'll likely need
        const prefetchDomains = [
            '//www.gstatic.com',
            '//fonts.googleapis.com',
            '//connect.facebook.net',
            '//www.google-analytics.com'
        ];

        prefetchDomains.forEach(domain => {
            const link = document.createElement('link');
            link.rel = 'dns-prefetch';
            link.href = domain;
            document.head.appendChild(link);
        });
    }

    /**
     * Setup critical CSS loading
     */
    setupCriticalCSS() {
        // Remove critical CSS style tag after initial load
        window.addEventListener('load', () => {
            const criticalCSS = document.getElementById('critical-css');
            if (criticalCSS) {
                setTimeout(() => {
                    criticalCSS.remove();
                }, 3000);
            }
        });
    }

    /**
     * Setup caching headers and service worker
     */
    setupCaching() {
        // Register service worker for caching
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/static/js/sw.js')
                    .then(registration => {
                        console.log('ServiceWorker registration successful with scope: ', registration.scope);
                    })
                    .catch(error => {
                        console.log('ServiceWorker registration failed: ', error);
                    });
            });
        }

        // Set up cache-busting for static assets
        this.setupCacheBusting();
    }

    /**
     * Setup cache-busting for static assets
     */
    setupCacheBusting() {
        const timestamp = new Date().getTime();
        const assets = [
            '/static/css/design-system.css',
            '/static/css/design-system-accessibility.css',
            '/static/js/auth.js',
            '/static/js/landing.js'
        ];

        assets.forEach(asset => {
            const link = document.querySelector(`link[href="${asset}"]`);
            if (link) {
                link.href = `${asset}?v=${timestamp}`;
            }
        });
    }

    /**
     * Setup Intersection Observer for general lazy loading
     */
    setupIntersectionObserver() {
        const observerOptions = {
            root: null,
            rootMargin: '50px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // Observe elements that should animate on scroll
        const animatedElements = document.querySelectorAll('.animate-on-scroll');
        animatedElements.forEach(el => observer.observe(el));
    }

    /**
     * Setup preloading for important resources
     */
    setupPreload() {
        // Preload important fonts
        const fontLinks = [
            { href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap', as: 'style' },
            { href: '/static/fonts/inter-regular.woff2', as: 'font', type: 'font/woff2', crossOrigin: 'anonymous' },
            { href: '/static/fonts/inter-semibold.woff2', as: 'font', type: 'font/woff2', crossOrigin: 'anonymous' }
        ];

        fontLinks.forEach(config => {
            const link = document.createElement('link');
            Object.keys(config).forEach(key => {
                link.setAttribute(key, config[key]);
            });
            document.head.appendChild(link);
        });

        // Preload important images above the fold
        const aboveFoldImages = document.querySelectorAll('img[loading="eager"]');
        aboveFoldImages.forEach(img => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'image';
            link.href = img.src;
            document.head.appendChild(link);
        });
    }

    /**
     * Optimize images by converting to WebP when supported
     */
    optimizeImages() {
        if (!this.supportsWebP()) return;

        const images = document.querySelectorAll('img:not([data-webp-optimized])');
        images.forEach(img => {
            const src = img.src;
            if (src && (src.endsWith('.jpg') || src.endsWith('.jpeg') || src.endsWith('.png'))) {
                const webpSrc = src.replace(/\.(jpg|jpeg|png)$/, '.webp');
                img.dataset.src = webpSrc;
                img.dataset.webpOptimized = 'true';
            }
        });
    }

    /**
     * Check if browser supports WebP
     */
    supportsWebP() {
        const canvas = document.createElement('canvas');
        return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
    }

    /**
     * Debounce function for performance optimization
     */
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

    /**
     * Throttle function for performance optimization
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Measure and report performance metrics
     */
    measurePerformance() {
        if ('performance' in window && 'memory' in performance) {
            const memoryInfo = performance.memory;
            const usedJSHeapSize = memoryInfo.usedJSHeapSize / 1048576; // Convert to MB
            const totalJSHeapSize = memoryInfo.totalJSHeapSize / 1048576;
            const jsHeapSizeLimit = memoryInfo.jsHeapSizeLimit / 1048576;

            console.log(`Memory Usage: ${usedJSHeapSize.toFixed(2)}MB / ${totalJSHeapSize.toFixed(2)}MB (Limit: ${jsHeapSizeLimit.toFixed(2)}MB)`);
        }

        // Measure page load time
        if ('performance' in window) {
            const navigation = performance.getEntriesByType('navigation')[0];
            if (navigation) {
                console.log(`Page Load Time: ${navigation.loadEventEnd - navigation.fetchStart}ms`);
            }
        }
    }
}

// Initialize performance optimizations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const optimizer = new PerformanceOptimizer();
    
    // Measure performance after page load
    window.addEventListener('load', () => {
        setTimeout(() => {
            optimizer.measurePerformance();
        }, 1000);
    });

    // Optimize images when supported
    optimizer.optimizeImages();

    // Add performance monitoring
    if ('PerformanceObserver' in window) {
        const observer = new PerformanceObserver((list) => {
            for (const entry of list.getEntries()) {
                if (entry.entryType === 'largest-contentful-paint') {
                    console.log(`LCP: ${entry.startTime}ms`);
                } else if (entry.entryType === 'first-input') {
                    console.log(`FID: ${entry.processingStart - entry.startTime}ms`);
                } else if (entry.entryType === 'layout-shift') {
                    console.log(`CLS: ${entry.value}`);
                }
            }
        });

        observer.observe({ entryTypes: ['largest-contentful-paint', 'first-input', 'layout-shift'] });
    }
});

// Export for use in other modules
window.PerformanceOptimizer = PerformanceOptimizer;