from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, fields
import logging

from dnssec_validator import DNSSECValidator

app = Flask(__name__)
CORS(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
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
validation_result_model = api.model('ValidationResult', {
    'domain': fields.String(required=True, description='The domain that was validated'),
    'status': fields.String(required=True, description='Validation status', enum=['valid', 'invalid', 'error']),
    'validation_time': fields.String(required=True, description='ISO timestamp of validation'),
    'chain_of_trust': fields.List(fields.Raw, description='Chain of trust validation details'),
    'records': fields.Raw(description='DNSSEC records found'),
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
    @ns.marshal_with(validation_result_model, code=200)
    @ns.marshal_with(error_model, code=500)
    @ns.response(200, 'Success - Domain validation completed')
    @ns.response(400, 'Bad Request - Invalid domain format')
    @ns.response(429, 'Too Many Requests - Rate limit exceeded')
    @ns.response(500, 'Internal Server Error - Validation failed')
    @limiter.limit("10 per minute")
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

# Traditional Flask routes for web interface
@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/<string:domain>')
def check_domain_direct(domain):
    """Direct access like /bondit.dk - render page with pre-filled domain"""
    return render_template('index.html', domain=domain)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
