document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('dnssec-form');
    const domainInput = document.getElementById('domain-input');
    const resultsContainer = document.getElementById('results-container');

    // Normalize domain input on blur (when field loses focus)
    domainInput.addEventListener('blur', function() {
        const normalizedDomain = domainInput.value
            .trim()                    // Remove leading/trailing spaces
            .replace(/\s+/g, '')       // Remove all internal spaces
            .toLowerCase();            // Convert to lowercase
        domainInput.value = normalizedDomain;
    });
    
    // Optional: Real-time normalization while typing (commented out by default)
    // Uncomment the following lines if you want immediate normalization while typing
    // domainInput.addEventListener('input', function() {
    //     const cursorPosition = domainInput.selectionStart;
    //     const normalizedDomain = domainInput.value.toLowerCase();
    //     domainInput.value = normalizedDomain;
    //     domainInput.setSelectionRange(cursorPosition, cursorPosition);
    // });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const domain = domainInput.value
            .trim()                    // Remove leading/trailing spaces
            .replace(/\s+/g, '')       // Remove all internal spaces
            .toLowerCase();            // Convert to lowercase
        if (domain) {
            // Ensure input field shows the final normalized domain
            domainInput.value = domain;
            validateDomain(domain);
        }
    });

    function escapeHTML(str) {
        // Handle non-string values by converting to string first
        if (str === null || str === undefined) {
            return '';
        }
        // Convert to string if it's not already a string
        const stringValue = String(str);
        return stringValue.replace(/[&<>"']/g, function (m) {
            switch (m) {
                case '&': return '&amp;';
                case '<': return '&lt;';
                case '>': return '&gt;';
                case '"': return '&quot;';
                case "'": return '&#39;';
                default: return m;
            }
        });
    }

    function validateDomain(domain) {
        resultsContainer.innerHTML = '<p>Validating DNSSEC for ' + escapeHTML(domain) + '...</p>';
        
        fetch('/api/validate/' + encodeURIComponent(domain), {
                headers: {
                    'X-Client': 'webapp'
                }
            })
            .then(response => response.json())
            .then(data => displayResults(data))
            .catch(error => {
                resultsContainer.innerHTML = '<p>Error: ' + escapeHTML(error.message) + '</p>';
            });
    }

    function displayResults(data) {
        let html = '<h2>Validation Results for ' + escapeHTML(data.domain) + '</h2>';
        
        // Status with appropriate styling  
        let statusClass = 'status-' + escapeHTML(data.status);
        html += '<p><strong>Status:</strong> <span class="' + statusClass + '">' + escapeHTML(data.status.toUpperCase()) + '</span></p>';
        html += '<p><strong>Validation Time:</strong> ' + escapeHTML(new Date(data.validation_time).toLocaleString()) + '</p>';

        if (data.chain_of_trust && data.chain_of_trust.length > 0) {
            html += '<h3>Chain of Trust</h3>';
            data.chain_of_trust.forEach(function(zone) {
                html += '<div class="chain-item">';
                html += '<strong>' + escapeHTML(zone.zone) + '</strong> - <span class="status-' + escapeHTML(zone.status) + '">' + escapeHTML(zone.status) + '</span>';
                if (zone.algorithm) {
                    html += '<br><small>Algorithm: ' + escapeHTML(zone.algorithm) + ', Key Tag: ' + escapeHTML(zone.key_tag) + '</small>';
                }
                if (zone.error) {
                    html += '<br><small class="status-error">Error: ' + escapeHTML(zone.error) + '</small>';
                }
                html += '</div>';
            });
        }

        // Show DNSKEY records if available
        if (data.records && data.records.dnskey && data.records.dnskey.length > 0) {
            html += '<h3>DNSKEY Records</h3>';
            data.records.dnskey.forEach(function(key) {
                html += '<div class="chain-item">';
                html += '<strong>Zone:</strong> ' + escapeHTML(key.zone) + '<br>';
                html += '<strong>Algorithm:</strong> ' + escapeHTML(key.algorithm) + '<br>';
                html += '<strong>Key Tag:</strong> ' + escapeHTML(key.key_tag) + '<br>';
                html += '<strong>Flags:</strong> ' + escapeHTML(key.flags);
                html += '</div>';
            });
        }

        // Show TLSA summary if available and feature is enabled
        if (data.tlsa_summary && window.SHOW_TLSA_DANE === true) {
            html += '<h3>🔒 TLSA/DANE Validation</h3>';
            html += '<div class="chain-item">';
            html += '<p><strong>Status:</strong> ' + escapeHTML(data.tlsa_summary.status) + '</p>';
            html += '<p><strong>TLSA Records Found:</strong> ' + escapeHTML(data.tlsa_summary.records_found) + '</p>';
            html += '<p><strong>DANE Status:</strong> ' + escapeHTML(data.tlsa_summary.dane_status) + '</p>';
            html += '<p style="margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; font-style: italic;">' + escapeHTML(data.tlsa_summary.message) + '</p>';
            html += '</div>';
        }

        if (data.errors && data.errors.length > 0) {
            html += '<h3>Errors</h3>';
            data.errors.forEach(function(error) {
                html += '<div class="error-item">' + escapeHTML(error) + '</div>';
            });
        }
        
        // Add detailed analysis link
        html += '<div style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; text-align: center;"><p style="margin: 0 0 10px 0; color: #6c757d;">Want more technical details?</p><a href="/' + encodeURIComponent(data.domain) + '/detailed" style="padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; font-weight: 500;">🔍 View Detailed Analysis</a></div>';

        resultsContainer.innerHTML = html;
    }
});
