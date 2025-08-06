document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('dnssec-form');
    const domainInput = document.getElementById('domain-input');
    const resultsContainer = document.getElementById('results-container');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const domain = domainInput.value.trim();
        if (domain) {
            validateDomain(domain);
        }
    });

    function escapeHTML(str) {
        return str.replace(/[&<>"']/g, function (m) {
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
        
        fetch('/api/validate/' + encodeURIComponent(domain))
            .then(response => response.json())
            .then(data => displayResults(data))
            .catch(error => {
                resultsContainer.innerHTML = '<p>Error: ' + error.message + '</p>';
            });
    }

    function displayResults(data) {
        let html = '<h2>Validation Results for ' + data.domain + '</h2>';
        
        // Status with appropriate styling
        let statusClass = 'status-' + data.status;
        html += '<p><strong>Status:</strong> <span class="' + statusClass + '">' + data.status.toUpperCase() + '</span></p>';
        html += '<p><strong>Validation Time:</strong> ' + new Date(data.validation_time).toLocaleString() + '</p>';

        if (data.chain_of_trust && data.chain_of_trust.length > 0) {
            html += '<h3>Chain of Trust</h3>';
            data.chain_of_trust.forEach(function(zone) {
                html += '<div class="chain-item">';
                html += '<strong>' + zone.zone + '</strong> - <span class="status-' + zone.status + '">' + zone.status + '</span>';
                if (zone.algorithm) {
                    html += '<br><small>Algorithm: ' + zone.algorithm + ', Key Tag: ' + zone.key_tag + '</small>';
                }
                if (zone.error) {
                    html += '<br><small class="status-error">Error: ' + zone.error + '</small>';
                }
                html += '</div>';
            });
        }

        // Show DNSKEY records if available
        if (data.records && data.records.dnskey && data.records.dnskey.length > 0) {
            html += '<h3>DNSKEY Records</h3>';
            data.records.dnskey.forEach(function(key) {
                html += '<div class="chain-item">';
                html += '<strong>Zone:</strong> ' + key.zone + '<br>';
                html += '<strong>Algorithm:</strong> ' + key.algorithm + '<br>';
                html += '<strong>Key Tag:</strong> ' + key.key_tag + '<br>';
                html += '<strong>Flags:</strong> ' + key.flags;
                html += '</div>';
            });
        }

        if (data.errors && data.errors.length > 0) {
            html += '<h3>Errors</h3>';
            data.errors.forEach(function(error) {
                html += '<div class="error-item">' + error + '</div>';
            });
        }

        resultsContainer.innerHTML = html;
    }
});
