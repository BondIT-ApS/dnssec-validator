/**
 * GDPR-Compliant Cookie Consent Manager
 * Handles user consent for Google Analytics tracking
 */

class CookieConsent {
    constructor() {
        this.consentKey = 'dnssec_analytics_consent';
        this.init();
    }

    init() {
        // Check if user has already made a choice
        const consent = this.getConsent();
        
        if (consent === null) {
            // No choice made yet, show banner
            this.showBanner();
        } else if (consent === true) {
            // User accepted, enable analytics
            this.enableAnalytics();
        }
        // If consent === false, do nothing (analytics stays disabled)
    }

    getConsent() {
        const value = localStorage.getItem(this.consentKey);
        if (value === null) return null;
        return value === 'true';
    }

    setConsent(accepted) {
        localStorage.setItem(this.consentKey, accepted.toString());
        if (accepted) {
            this.enableAnalytics();
        }
        this.hideBanner();
    }

    enableAnalytics() {
        // Trigger analytics initialization
        if (window.initializeAnalytics) {
            window.initializeAnalytics();
        }
    }

    showBanner() {
        const banner = document.createElement('div');
        banner.id = 'cookie-consent-banner';
        banner.innerHTML = `
            <div class="cookie-consent-content">
                <div class="cookie-consent-text">
                    <strong>🍪 Cookie Notice</strong>
                    <p>We use Google Analytics to understand how visitors use our DNSSEC validator. 
                    This helps us improve the service. You can accept or decline tracking.</p>
                </div>
                <div class="cookie-consent-actions">
                    <button id="cookie-accept" class="cookie-btn cookie-accept">Accept</button>
                    <button id="cookie-decline" class="cookie-btn cookie-decline">Decline</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(banner);

        // Add event listeners
        document.getElementById('cookie-accept').addEventListener('click', () => {
            this.setConsent(true);
        });

        document.getElementById('cookie-decline').addEventListener('click', () => {
            this.setConsent(false);
        });

        // Show banner with animation
        setTimeout(() => {
            banner.classList.add('show');
        }, 100);
    }

    hideBanner() {
        const banner = document.getElementById('cookie-consent-banner');
        if (banner) {
            banner.classList.remove('show');
            setTimeout(() => {
                banner.remove();
            }, 300);
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new CookieConsent();
    });
} else {
    new CookieConsent();
}
