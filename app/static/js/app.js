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

    function validateDomain(domain) {
        resultsContainer.innerHTML = '<p>Validating DNSSEC for ' + domain + '...</p>';
        
        fetch('/api/validate/' + encodeURIComponent(domain))
            .then(response => response.json())
            .then(data => displayResults(data))
            .catch(error => {
                resultsContainer.innerHTML = '<p>Error: ' + error.message + '</p>';
            });
    }

    function displayResults(data) {
        let html = '<h2>Validation Results for ' + data.domain + '</h2>';
        html += '<p><strong>Status:</strong> ' + data.status + '</p>';
        html += '<p><strong>Validation Time:</strong> ' + data.validation_time + '</p>';

        if (data.chain_of_trust && data.chain_of_trust.length > 0) {
            html += '<h3>Chain of Trust</h3><ul>';
            data.chain_of_trust.forEach(function(zone) {
                html += '<li>' + zone.zone + ' - ' + zone.status;
                if (zone.algorithm) {
                    html += ' (Algorithm: ' + zone.algorithm + ', Key Tag: ' + zone.key_tag + ')';
                }
                html += '</li>';
            });
            html += '</ul>';
        }

        if (data.errors && data.errors.length > 0) {
            html += '<h3>Errors</h3><ul>';
            data.errors.forEach(function(error) {
                html += '<li>' + error + '</li>';
            });
            html += '</ul>';
        }

        resultsContainer.innerHTML = html;
    }
});
