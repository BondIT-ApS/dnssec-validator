from flask import Flask, jsonify, render_template, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api, Resource, fields
from flask_talisman import Talisman
import logging
import os
import time
import psutil
from datetime import datetime, timezone

from dnssec_validator import DNSSECValidator
from models import RequestLog
import db_init

# Initialize database based on environment variables before creating Flask app
# Check if any database management environment variables are set
db_recreate = os.getenv('INFLUX_DB_RECREATE', 'false').lower() == 'true'
db_truncate = os.getenv('INFLUX_DB_TRUNCATE', 'false').lower() == 'true'

# Run database initialization regardless of how the app is started (direct Python or Gunicorn)
if db_recreate or db_truncate:
    print("🗄️  Database management operations requested...")
    import sys
    if not db_init.initialize_database():
        print("❌ Failed to initialize database. Exiting.")
        sys.exit(1)

app = Flask(__name__)

# Track application startup time for uptime calculation
app_start_time = time.time()

# Security enhancements
CORS(app, origins=os.getenv('CORS_ORIGINS', 'http://localhost:8080').split(','))
Talisman(
    app,
    force_https=os.getenv('FLASK_ENV') == 'production',
    strict_transport_security=True,
    content_security_policy={
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net",
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

# Configure logging with environment variable support
def setup_logging():
    """Configure logging based on environment variables"""
    # Get log level from environment variable (default to INFO)
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Map string log levels to logging constants
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,  # Alternative spelling
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # Validate and get numeric level
    numeric_level = level_map.get(log_level, logging.INFO)
    if log_level not in level_map:
        print(f"Warning: Invalid LOG_LEVEL '{log_level}', defaulting to INFO")
        numeric_level = logging.INFO
    
    # Check if structured logging (JSON) is enabled
    structured_logging = os.getenv('LOG_FORMAT', 'standard').lower() == 'json'
    
    # Configure log format
    if structured_logging:
        # JSON structured logging format
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s", "lineno": %(lineno)d}'
        )
    else:
        # Standard logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if not structured_logging else None
    )
    
    # Configure file logging if enabled
    log_file = os.getenv('LOG_FILE')
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            
            # Add file handler to root logger
            root_logger = logging.getLogger()
            root_logger.addHandler(file_handler)
            
            print(f"Logging to file enabled: {log_file}")
        except Exception as e:
            print(f"Warning: Could not set up file logging to {log_file}: {e}")
    
    # If structured logging is enabled, reconfigure console handler
    if structured_logging:
        root_logger = logging.getLogger()
        # Remove default handler and add custom one
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
                root_logger.removeHandler(handler)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    return numeric_level, structured_logging

# Set up logging
log_level, is_structured = setup_logging()
logger = logging.getLogger(__name__)

# Log startup information with current configuration
logger.info(f"DNSSEC Validator starting with log level: {logging.getLevelName(log_level)}")
logger.debug(f"Structured logging enabled: {is_structured}")
logger.debug(f"Log file: {os.getenv('LOG_FILE', 'None - console only')}")

# Request logging functionality
def get_client_ip():
    """Get the real client IP address considering proxies"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or 'unknown'

def should_log_request():
    """Determine if request should be logged (skip health checks, static files)"""
    # Skip health check endpoints
    if request.path.startswith('/health'):
        return False
    # Skip static files
    if request.path.startswith('/static'):
        return False
    # Skip API docs
    if request.path.startswith('/api/docs') or request.path == '/swaggerui':
        return False
    return True

@app.after_request
def log_request(response):
    """Log request after completion if logging is enabled"""
    if not should_log_request():
        return response
    
    # Check if logging is enabled
    if os.getenv('REQUEST_LOGGING_ENABLED', 'true').lower() != 'true':
        return response
    
    try:
        # Determine source (api vs webapp)
        source = 'api' if request.path.startswith('/api/') else 'webapp'
        
        # We do NOT log plain web page views; only log API requests
        if source != 'api':
            return response
        
        # Determine if this is an internal request (analytics, stats, etc.)
        internal_paths = [
            '/api/analytics/',
            '/health',
            '/api/docs',
        ]
        is_internal = any(request.path.startswith(path) for path in internal_paths)
        if is_internal:
            # Don't log internal analytics/health/api-docs calls
            return response
        
        # Extract domain from request for validate endpoint
        domain = 'unknown'
        request_type = 'unknown'
        if request.path.startswith('/api/validate/'):
            candidate = request.path.replace('/api/validate/', '')
            # Handle /detailed suffix for detailed analysis endpoints
            if candidate.endswith('/detailed'):
                candidate = candidate[:-9]  # Remove '/detailed' suffix
                request_type = 'detailed'
            else:
                request_type = 'basic'
            
            # Only accept if it looks like a domain (simple regex)
            import re
            if re.match(r'^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', candidate):
                domain = candidate
        
        # Identify client: webapp vs external (explicit header only)
        client = 'webapp' if request.headers.get('X-Client', '').lower() == 'webapp' else 'external'
        
        # Get DNSSEC status from response if available
        dnssec_status = 'unknown'
        if hasattr(g, 'dnssec_status'):
            dnssec_status = g.dnssec_status
        elif response.status_code == 200:
            # Try to parse status from response JSON
            try:
                if response.is_json:
                    data = response.get_json()
                    if isinstance(data, dict) and 'status' in data:
                        dnssec_status = data['status']
            except:
                pass
        elif response.status_code >= 400:
            dnssec_status = 'error'
        
        # Log the API request
        from models import influx_logger
        influx_logger.log_request(
            ip_address=get_client_ip(),
            domain=domain,
            http_status=response.status_code,
            dnssec_status=dnssec_status,
            source=source,
            user_agent=request.headers.get('User-Agent', ''),
            internal=False,
            client=client,
            request_type=request_type,
        )
        
    except Exception as e:
        logger.warning(f"Failed to log request: {e}")
    
    return response

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

tlsa_summary_model = api.model('TLSASummary', {
    'status': fields.String(required=True, description='TLSA validation status', enum=['valid', 'invalid', 'no_records', 'cert_unavailable', 'error']),
    'records_found': fields.Integer(required=True, description='Number of TLSA records found'),
    'dane_status': fields.String(required=True, description='DANE validation status'),
    'message': fields.String(required=True, description='User-friendly status message')
})

validation_result_model = api.model('ValidationResult', {
    'domain': fields.String(required=True, description='The domain that was validated'),
    'status': fields.String(required=True, description='Validation status', enum=['valid', 'invalid', 'insecure', 'error']),
    'validation_time': fields.String(required=True, description='ISO timestamp of validation'),
    'chain_of_trust': fields.List(fields.Nested(chain_of_trust_model), description='Chain of trust validation details'),
    'records': fields.Nested(records_model, description='DNSSEC records found'),
    'tlsa_summary': fields.Nested(tlsa_summary_model, description='TLSA/DANE validation summary'),
    'errors': fields.List(fields.String, description='Any errors encountered during validation')
})

error_model = api.model('ErrorResponse', {
    'domain': fields.String(required=True, description='The domain that caused the error'),
    'status': fields.String(required=True, description='Error status', enum=['error']),
    'errors': fields.List(fields.String, description='List of error messages')
})

# Define namespaces
ns_validate = api.namespace('validate', description='DNSSEC validation operations')
ns_analytics = api.namespace('analytics', description='Analytics and statistics operations')

# Analytics API models
analytics_overview_model = api.model('AnalyticsOverview', {
    'total_requests': fields.Integer(description='Total requests in time period'),
    'api_requests': fields.Integer(description='API requests in time period'),
    'web_requests': fields.Integer(description='Web requests in time period'),
    'validation_ratio': fields.Raw(description='DNSSEC validation success ratio'),
    'top_domains': fields.List(fields.Raw, description='Most validated domains')
})

hourly_data_model = api.model('HourlyData', {
    'timestamp': fields.String(description='Hour timestamp'),
    'requests': fields.Integer(description='Number of requests in this hour')
})

timeseries_model = api.model('TimeSeriesData', {
    'data': fields.List(fields.Nested(hourly_data_model), description='Hourly request data'),
    'period': fields.String(description='Time period covered'),
    'total': fields.Integer(description='Total requests in period')
})

# DNSSEC Validation endpoints
@ns_validate.route('/<path:domain>')
@ns_validate.param('domain', 'The domain name or URL to validate (e.g., bondit.dk or https://bondit.dk)')
class DNSSECValidation(Resource):
    @ns_validate.doc('validate_domain')
    @ns_validate.expect()
    @ns_validate.response(200, 'Success - Domain validation completed', validation_result_model)
    @ns_validate.response(400, 'Bad Request - Invalid domain format')
    @ns_validate.response(429, 'Too Many Requests - Rate limit exceeded')
    @ns_validate.response(500, 'Internal Server Error - Validation failed')
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self, domain):
        """
        Validate DNSSEC configuration for a domain
        
        This endpoint performs comprehensive DNSSEC validation including:
        - Chain of trust verification
        - DNSKEY record validation
        - DS record verification
        - RRSIG signature checking
        - TLSA/DANE validation (RFC 6698)
        
        Returns detailed validation results including status, trust chain,
        TLSA validation summary, and all relevant DNSSEC records found.
        """
        try:
            # Import domain utilities for URL parsing
            from domain_utils import extract_domain_from_input, is_valid_domain_format
            
            # Log original input for debugging
            original_input = domain
            logger.debug(f"API received input: {original_input}")
            
            # Extract domain from URL or validate direct domain input
            extracted_domain = extract_domain_from_input(domain)
            
            if not extracted_domain or not is_valid_domain_format(extracted_domain):
                return {
                    'domain': original_input,
                    'status': 'error',
                    'errors': [f'Invalid domain format or unable to extract domain from: {original_input}']
                }, 400
                
            # Use the extracted domain for validation
            domain = extracted_domain
            logger.debug(f"Extracted domain for validation: {domain}")
            
            logger.debug(f"Starting DNSSEC validation for domain: {domain}")
            validator = DNSSECValidator(domain)
            result = validator.validate()
            logger.info(f"DNSSEC validation completed for {domain} with status: {result.get('status', 'unknown')}")
            return result, 200
            
        except Exception as e:
            logger.error(f"DNSSEC validation failed for domain {domain}: {str(e)}", exc_info=True)
            return {
                'domain': domain,
                'status': 'error',
                'errors': [sanitize_error(e)]
            }, 500

@ns_validate.route('/<path:domain>/detailed')
@ns_validate.param('domain', 'The domain name or URL to analyze in detail (e.g., bondit.dk or https://bondit.dk)')
class DNSSECDetailedValidation(Resource):
    @ns_validate.doc('validate_domain_detailed')
    @ns_validate.expect()
    @ns_validate.response(200, 'Success - Detailed domain analysis completed')
    @ns_validate.response(400, 'Bad Request - Invalid domain format')
    @ns_validate.response(429, 'Too Many Requests - Rate limit exceeded')
    @ns_validate.response(500, 'Internal Server Error - Analysis failed')
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self, domain):
        """
        Perform detailed DNSSEC analysis for a domain
        
        This endpoint performs comprehensive DNSSEC analysis including:
        - All features from basic validation
        - Raw DNS query responses (dig-style output)
        - Algorithm strength analysis
        - Signature validity periods
        - Key strength assessment
        - Troubleshooting recommendations
        - Security best practice suggestions
        - Query timing information
        
        Returns extensive technical details for debugging and analysis.
        """
        try:
            # Import domain utilities for URL parsing
            from domain_utils import extract_domain_from_input, is_valid_domain_format
            
            # Log original input for debugging
            original_input = domain
            logger.debug(f"API detailed received input: {original_input}")
            
            # Extract domain from URL or validate direct domain input
            extracted_domain = extract_domain_from_input(domain)
            
            if not extracted_domain or not is_valid_domain_format(extracted_domain):
                return {
                    'domain': original_input,
                    'status': 'error',
                    'errors': [f'Invalid domain format or unable to extract domain from: {original_input}']
                }, 400
                
            # Use the extracted domain for validation
            domain = extracted_domain
            logger.debug(f"Extracted domain for detailed validation: {domain}")
            
            logger.debug(f"Starting detailed DNSSEC analysis for domain: {domain}")
            validator = DNSSECValidator(domain)
            result = validator.validate_detailed()
            logger.info(f"Detailed DNSSEC analysis completed for {domain} with status: {result.get('status', 'unknown')}")
            return result, 200
            
        except Exception as e:
            logger.error(f"Detailed DNSSEC analysis failed for domain {domain}: {str(e)}", exc_info=True)
            return {
                'domain': domain,
                'status': 'error',
                'errors': [sanitize_error(e)]
            }, 500

# Analytics endpoints
@ns_analytics.route('/overview')
class AnalyticsOverview(Resource):
    @ns_analytics.doc('get_analytics_overview')
    @ns_analytics.param('period', 'Time period: 1h, 24h, 7d, 30d', _in='query', default='24h')
    @ns_analytics.response(200, 'Success - Analytics overview data', analytics_overview_model)
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self):
        """
        Get analytics overview data
        
        Returns comprehensive analytics including request counts,
        validation ratios, and top domains for the specified period.
        """
        try:
            period = request.args.get('period', '24h')
            
            # Parse period
            if period == '1h':
                hours = 1
                days = None
            elif period == '24h':
                hours = 24
                days = None
            elif period == '7d':
                hours = None
                days = 7
            elif period == '30d':
                hours = None
                days = 30
            else:
                return {'error': 'Invalid period. Use: 1h, 24h, 7d, 30d'}, 400
            
            logger.debug(f"Analytics overview requested for period: {period} (hours={hours}, days={days})")
            # Get analytics data (API validations only; exclude internal endpoints)
            # Get breakdown by client (external vs webapp)
            breakdown_list = RequestLog.get_source_breakdown(days=days, hours=hours)
            breakdown = {'external': 0, 'webapp': 0}
            for client, count in breakdown_list:
                if client not in breakdown:
                    breakdown[client] = 0
                breakdown[client] += count
            
            external_cnt = breakdown.get('external', 0)
            internal_cnt = breakdown.get('webapp', 0)
            total_requests = external_cnt + internal_cnt
            api_requests = external_cnt  # External API callers
            web_requests = internal_cnt  # Internal = webapp using API
            
            validation_ratio = RequestLog.get_external_validation_ratio(days=days, hours=hours)
            top_domains = RequestLog.get_external_top_domains(limit=10, days=days, hours=hours)
            
            return {
                'total_requests': total_requests,
                'api_requests': api_requests,
                'web_requests': web_requests,
                'validation_ratio': validation_ratio,
                'top_domains': top_domains
            }, 200
            
        except Exception as e:
            logger.error(f"Analytics overview error: {str(e)}", exc_info=True)
            return {'error': 'Failed to fetch analytics data'}, 500

@ns_analytics.route('/timeseries')
class AnalyticsTimeSeries(Resource):
    @ns_analytics.doc('get_timeseries_data')
    @ns_analytics.param('period', 'Time period: 1h, 24h, 7d, 30d', _in='query', default='24h')
    @ns_analytics.response(200, 'Success - Time series data', timeseries_model)
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self):
        """
        Get time series analytics data
        
        Returns hourly request counts for charting over the specified period.
        """
        try:
            period = request.args.get('period', '24h')
            
            # Parse period
            if period == '1h':
                hours = 1
            elif period == '24h':
                hours = 24
            elif period == '7d':
                hours = 168  # 7 * 24
            elif period == '30d':
                hours = 720  # 30 * 24
            else:
                return {'error': 'Invalid period. Use: 1h, 24h, 7d, 30d'}, 400
            
            # Choose window size
            if period == '1h':
                window = '5m'
            elif period == '24h':
                window = '15m'
            else:
                window = '1h'
            
            # Get hourly data (external requests only for stats dashboard, API only)
            hourly_data = RequestLog.get_external_hourly_requests(hours=hours, window_every=window)
            
            # Format data for chart
            chart_data = [{
                'timestamp': timestamp,
                'requests': count
            } for timestamp, count in hourly_data]
            
            total_requests = sum(count for _, count in hourly_data)
            
            return {
                'data': chart_data,
                'period': period,
                'total': total_requests
            }, 200
            
        except Exception as e:
            logger.error(f"Analytics timeseries error: {str(e)}", exc_info=True)
            return {'error': 'Failed to fetch time series data'}, 500

@ns_analytics.route('/sources')
class AnalyticsSources(Resource):
    @ns_analytics.doc('get_source_breakdown')
    @ns_analytics.param('period', 'Time period: 1h, 24h, 7d, 30d', _in='query', default='7d')
    @ns_analytics.response(200, 'Success - Source breakdown data')
    @limiter.limit(f"{rate_limits['api_minute']} per minute; {rate_limits['api_hour']} per hour")
    def get(self):
        """
        Get breakdown of API callers: external vs webapp (API only)
        """
        try:
            period = request.args.get('period', '7d')
            if period == '1h':
                hours, days = 1, None
            elif period == '24h':
                hours, days = 24, None
            elif period == '7d':
                hours, days = None, 7
            elif period == '30d':
                hours, days = None, 30
            else:
                return {'error': 'Invalid period. Use: 1h, 24h, 7d, 30d'}, 400
            
            source_data = RequestLog.get_source_breakdown(days=days, hours=hours)
            
            # Format for chart
            breakdown = { 'external': 0, 'webapp': 0 }
            for client, count in source_data:
                key = client or 'external'
                if key not in breakdown:
                    breakdown[key] = 0
                breakdown[key] += count
            
            return breakdown, 200
            
        except Exception as e:
            logger.error(f"Analytics sources error: {str(e)}", exc_info=True)
            return {'error': 'Failed to fetch source breakdown'}, 500

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

# Health check helper functions
def get_uptime():
    """Calculate application uptime in a human-readable format"""
    uptime_seconds = int(time.time() - app_start_time)
    
    days = uptime_seconds // 86400
    hours = (uptime_seconds % 86400) // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m {seconds}s"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def check_dns_resolver():
    """Test DNS resolution capability"""
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.resolve('example.com', 'A')
        return 'ok'
    except Exception as e:
        logger.warning(f"DNS resolver check failed: {str(e)}")
        return 'error'

def check_memory_usage():
    """Check memory usage and return status"""
    try:
        memory_percent = psutil.virtual_memory().percent
        threshold = int(os.getenv('HEALTH_CHECK_MEMORY_THRESHOLD', '90'))
        
        if memory_percent < threshold:
            return 'ok'
        else:
            return 'warning'
    except Exception as e:
        logger.warning(f"Memory check failed: {str(e)}")
        return 'error'

# Health check endpoints (exempt from rate limiting)
@app.route('/health')
@limiter.exempt
def health_check():
    """Dedicated health check endpoint with detailed information"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'version': '1.0.0',
            'checks': {},
            'uptime': get_uptime()
        }
        
        # Check if detailed health checks are enabled
        health_enabled = os.getenv('HEALTH_CHECK_ENABLED', 'true').lower() == 'true'
        
        if health_enabled:
            # Test DNS resolution capability if enabled
            if os.getenv('HEALTH_CHECK_DNS_TEST', 'true').lower() == 'true':
                dns_status = check_dns_resolver()
                health_status['checks']['dns_resolver'] = dns_status
                if dns_status == 'error':
                    health_status['status'] = 'degraded'
            
            # Check memory usage
            memory_status = check_memory_usage()
            health_status['checks']['memory_usage'] = memory_status
            if memory_status in ['warning', 'error']:
                health_status['status'] = 'degraded' if health_status['status'] == 'healthy' else health_status['status']
        
        # Application is running if we got this far
        health_status['checks']['application'] = 'ok'
        
        # Determine HTTP status code
        status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': 'Health check system failure'
        }), 503

@app.route('/health/simple')
@limiter.exempt
def health_simple():
    """Simple health check for basic monitoring"""
    return 'healthy', 200

# Traditional Flask routes for web interface
@app.route('/')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def index():
    """Serve the main web interface"""
    logger.debug("Main web interface accessed")
    show_tlsa_dane = os.getenv('SHOW_VALIDATION_TLSA_DANE', 'false').lower() == 'true'
    return render_template('index.html', show_tlsa_dane=show_tlsa_dane)

@app.route('/stats')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def stats_dashboard():
    """Serve the analytics dashboard"""
    logger.info("Analytics dashboard accessed")
    return render_template('stats.html')

@app.route('/<string:domain>')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def check_domain_direct(domain):
    """Direct access like /bondit.dk - render page with pre-filled domain"""
    logger.info(f"Direct domain access: {domain}")
    show_tlsa_dane = os.getenv('SHOW_VALIDATION_TLSA_DANE', 'false').lower() == 'true'
    return render_template('index.html', domain=domain, show_tlsa_dane=show_tlsa_dane)

@app.route('/<string:domain>/detailed')
@limiter.limit(f"{rate_limits['web_minute']} per minute; {rate_limits['web_hour']} per hour")
def check_domain_detailed(domain):
    """Detailed DNSSEC analysis page like /bondit.dk/detailed"""
    logger.info(f"Detailed domain analysis access: {domain}")
    show_tlsa_dane = os.getenv('SHOW_VALIDATION_TLSA_DANE', 'false').lower() == 'true'
    return render_template('detailed.html', domain=domain, show_tlsa_dane=show_tlsa_dane)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
