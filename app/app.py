from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, fields
from flask_talisman import Talisman
import logging
import os
from datetime import datetime, timezone

from dnssec_validator import DNSSECValidator

app = Flask(__name__)

# Security enhancements
CORS(app, origins=os.getenv('CORS_ORIGINS', 'http://localhost:8080').split(','))
Talisman(
    app,
    force_https=os.getenv('FLASK_ENV') == 'production',
    strict_transport_security=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'"
    }
)

# Rate limiting configuration from environment variables
def get_rate_limits():
    return {
        'global_day': os.getenv('RATE_LIMIT_GLOBAL_DAY', '200'),
        'global_hour': os.getenv('RATE_LIMIT_GLOBAL_HOUR', '50'), 
        'api_minute': os.getenv('RATE_LIMIT_API_MINUTE', '10'),
        'api_hour': os.getenv('RATE_LIMIT_API_HOUR', '100'),
        'web_minute': os.getenv('RATE_LIMIT_WEB_MINUTE', '20'),
        'web_hour': os.getenv('RATE_LIMIT_WEB_HOUR', '200')
    }

rate_limits = get_rate_limits()

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[f"{rate_limits['global_day']} per day", f"{rate_limits['global_hour']} per hour"]
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask-RESTX
api = Api(
    app,
    version='1.0',
    title='DNSSEC Validator API',
    description='A comprehensive DNSSEC validation service that checks domain security',
    doc='/api/docs/',
    prefix='/api'
)

def sanitize_error(error):
    """Sanitize error messages for API responses to prevent information disclosure"""
    # Log the full error for debugging
    logger.error(f"API Error: {str(error)}", exc_info=True)
    
    # Return generic message to client
    return "An error occurred while processing your request"

# Define API models for documentation
dnskey_record_model = api.model('DNSKEYRecord', {
    'zone': fields.String(required=True, description='The zone this key belongs to'),
    'flags': fields.Integer(required=True, description='DNSKEY flags'),
    'protocol': fields.Integer(required=True, description='Protocol (always 3 for DNSSEC)'),
    'algorithm': fields.Integer(required=True, description='Cryptographic algorithm'),
    'key_tag': fields.Integer(required=True, description='Key identifier')
})

ds_record_model = api.model('DSRecord', {
    'zone': fields.String(required=True, description='The zone this DS record belongs to'),
    'key_tag': fields.Integer(required=True, description='Key tag of the DNSKEY'),
    'algorithm': fields.Integer(required=True, description='Cryptographic algorithm'),
    'digest_type': fields.Integer(required=True, description='Digest algorithm')
})

rrsig_record_model = api.model('RRSIGRecord', {
    'type_covered': fields.String(required=True, description='Record type covered by this signature'),
    'algorithm': fields.Integer(required=True, description='Cryptographic algorithm'),
    'labels': fields.Integer(required=True, description='Number of labels in the signed name'),
    'original_ttl': fields.Integer(required=True, description='Original TTL of the signed RRset'),
    'expiration': fields.Integer(required=True, description='Signature expiration time'),
    'inception': fields.Integer(required=True, description='Signature inception time'),
    'key_tag': fields.Integer(required=True, description='Key tag of the signing key'),
    'signer': fields.String(required=True, description='Name of the signing zone')
})

records_model = api.model('DNSSECRecords', {
    'dnskey': fields.List(fields.Nested(dnskey_record_model), description='DNSKEY records'),
    'ds': fields.List(fields.Nested(ds_record_model), description='DS records'),
    'rrsig': fields.List(fields.Nested(rrsig_record_model), description='RRSIG records')
})

chain_of_trust_model = api.model('ChainOfTrust', {
    'zone': fields.String(required=True, description='Zone name'),
    'status': fields.String(required=True, description='Validation status for this zone'),
    'algorithm': fields.Integer(description='Cryptographic algorithm used'),
    'key_tag': fields.Integer(description='Key tag of the zone key'),
    'error': fields.String(description='Error message if validation failed')
})

validation_result_model = api.model('ValidationResult', {
    'domain': fields.String(required=True, description='The domain that was validated'),
    'status': fields.String(required=True, description='Validation status', enum=['valid', 'invalid', 'error']),
    'validation_time': fields.String(required=True, description='ISO timestamp of validation'),
    'chain_of_trust': fields.List(fields.Nested(chain_of_trust_model), description='Chain of trust validation details'),
    'records': fields.Nested(records_model, description='DNSSEC records found'),
    'errors': fields.List(fields.String, description='Any errors encountered during validation')
})

error_model = api.model('ErrorResponse', {
    'domain': fields.String(required=True, description='The domain that caused the error'),
    'status': fields.String(required=True, description='Error status', enum=['error']),
    'errors': fields.List(fields.String, description='List of error messages')
})

# Define namespace
ns = api.namespace('validate', description='DNSSEC validation operations')

@ns.route('/<string:domain>')
@ns.param('domain', 'The domain name to validate (e.g., bondit.dk)')
class DNSSECValidation(Resource):
    @ns.doc('validate_domain')
    @ns.expect()
    @ns.response(200, 'Success - Domain validation completed', validation_result_model)
    @ns.response(400, 'Bad Request - Invalid domain format')
    @ns.response(429, 'Too Many Requests - Rate limit exceeded')
    @ns.response(500, 'Internal Server Error - Validation failed')
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self, domain):
        """
        Validate DNSSEC configuration for a domain
        
        This endpoint performs comprehensive DNSSEC validation including:
        - Chain of trust verification
        - DNSKEY record validation
        - DS record verification
        - RRSIG signature checking
        
        Returns detailed validation results including status, trust chain,
        and all relevant DNSSEC records found.
        """
        try:
            # Basic domain validation
            if not domain or len(domain) > 253:
                return {
                    'domain': domain,
                    'status': 'error',
                    'errors': ['Invalid domain format']
                }, 400
            
            validator = DNSSECValidator(domain)
            result = validator.validate()
            return result, 200
            
        except Exception as e:
            return {
                'domain': domain,
                'status': 'error',
                'errors': [sanitize_error(e)]
            }, 500

# Custom error handlers for rate limiting
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors with user-friendly responses"""
    
    # Calculate retry after time
    retry_after = getattr(e, 'retry_after', 60)
    reset_time = datetime.now(timezone.utc)
    if retry_after:
        reset_time = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if retry_after > 60:
            reset_time = reset_time.replace(minute=0) 
        reset_time = reset_time.timestamp() + retry_after
    
    # Add rate limiting headers
    def add_rate_limit_headers(response):
        response.headers['Retry-After'] = str(int(retry_after))
        response.headers['X-RateLimit-Reset'] = str(int(reset_time))
        return response
    
    if request.path.startswith('/api/'):
        # API JSON response
        response = jsonify({
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'API rate limit exceeded',
                'details': {
                    'limit': str(e.description),
                    'retry_after': int(retry_after),
                    'reset_time': datetime.fromtimestamp(reset_time, tz=timezone.utc).isoformat()
                }
            }
        })
        response.status_code = 429
        return add_rate_limit_headers(response)
    else:
        # Web interface friendly error page
        response = render_template('rate_limit.html', 
                                 limit=str(e.description),
                                 retry_after=int(retry_after),
                                 reset_time=datetime.fromtimestamp(reset_time, tz=timezone.utc).strftime('%H:%M:%S UTC'))
        response = app.make_response(response)
        response.status_code = 429
        return add_rate_limit_headers(response)

# Traditional Flask routes for web interface
@app.route('/')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/<string:domain>')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def check_domain_direct(domain):
    """Direct access like /bondit.dk - render page with pre-filled domain"""
    return render_template('index.html', domain=domain)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
