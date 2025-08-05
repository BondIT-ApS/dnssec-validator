from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from dnssec_validator import DNSSECValidator

app = Flask(__name__)
CORS(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<string:domain>')
def check_domain_direct(domain):
    # Direct access like /bondit.dk - render page with pre-filled domain
    return render_template('index.html', domain=domain)

@app.route('/api/validate/<string:domain>', methods=['GET'])
@limiter.limit("10 per minute")
def validate_domain(domain):
    try:
        validator = DNSSECValidator(domain)
        result = validator.validate()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'domain': domain,
            'status': 'error',
            'errors': [str(e)]
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
