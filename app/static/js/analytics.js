/**
 * Google Analytics 4 Integration
 * Only loads and initializes GA after user consent
 */

window.initializeAnalytics = function() {
    // Check if GA is enabled and tracking ID is provided
    if (!window.GA_ENABLED || !window.GA_TRACKING_ID) {
        console.log('Analytics disabled or tracking ID not configured');
        return;
    }

    // Check if already initialized
    if (window.gtag) {
        console.log('Analytics already initialized');
        return;
    }

    console.log('Initializing Google Analytics...');

    // Load GA4 script
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${window.GA_TRACKING_ID}`;
    document.head.appendChild(script);

    // Initialize gtag
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    window.gtag = gtag;
    
    gtag('js', new Date());
    gtag('config', window.GA_TRACKING_ID, {
        'anonymize_ip': true, // GDPR compliance
        'cookie_flags': 'SameSite=None;Secure'
    });

    console.log('Google Analytics initialized successfully');
};

/**
 * Track custom events
 */
window.trackEvent = function(eventName, eventParams = {}) {
    if (window.gtag) {
        gtag('event', eventName, eventParams);
    }
};

/**
 * Track DNSSEC validation events
 */
window.trackValidation = function(domain, success, validationTime) {
    trackEvent('dnssec_validation', {
        'domain': domain,
        'success': success,
        'validation_time_ms': validationTime,
        'event_category': 'validation'
    });
};

/**
 * Track page views (for single-page app behavior)
 */
window.trackPageView = function(pagePath) {
    if (window.gtag) {
        gtag('config', window.GA_TRACKING_ID, {
            'page_path': pagePath
        });
    }
};
