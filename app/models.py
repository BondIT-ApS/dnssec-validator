from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import os

db = SQLAlchemy()

class RequestLog(db.Model):
    """Model for logging all requests to the DNSSEC validator"""
    __tablename__ = 'request_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # Support IPv6
    domain = db.Column(db.String(255), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    http_status = db.Column(db.Integer, nullable=False)
    dnssec_status = db.Column(db.String(10), nullable=False)  # valid, invalid, error
    source = db.Column(db.String(10), nullable=False)  # api, webapp
    user_agent = db.Column(db.String(500))  # Optional for analytics
    
    def __repr__(self):
        return f'<RequestLog {self.domain} from {self.ip_address} at {self.timestamp}>'
    
    @classmethod
    def log_request(cls, ip_address, domain, http_status, dnssec_status, source, user_agent=None):
        """Log a request to the database"""
        try:
            log_entry = cls(
                ip_address=ip_address,
                domain=domain,
                http_status=http_status,
                dnssec_status=dnssec_status,
                source=source,
                user_agent=user_agent
            )
            db.session.add(log_entry)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error logging request: {e}")
            return False
    
    @classmethod
    def cleanup_old_logs(cls, days=None):
        """Remove logs older than specified days (default from env)"""
        if days is None:
            days = int(os.getenv('LOG_RETENTION_DAYS', '90'))
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            deleted = cls.query.filter(cls.timestamp < cutoff_date).delete()
            db.session.commit()
            return deleted
        except Exception as e:
            db.session.rollback()
            print(f"Error cleaning up logs: {e}")
            return 0
    
    # Analytics methods for issue #43
    @classmethod
    def get_requests_count(cls, hours=None, days=None, source=None):
        """Get request count for specified time period"""
        query = cls.query
        
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(cls.timestamp >= since)
        elif days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(cls.timestamp >= since)
        
        if source:
            query = query.filter(cls.source == source)
        
        return query.count()
    
    @classmethod
    def get_top_domains(cls, limit=20, days=None):
        """Get most frequently validated domains"""
        query = db.session.query(
            cls.domain, 
            func.count(cls.id).label('count')
        )
        
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(cls.timestamp >= since)
        
        return query.group_by(cls.domain).order_by(desc('count')).limit(limit).all()
    
    @classmethod
    def get_validation_ratio(cls, days=None):
        """Get ratio of valid vs invalid vs error validations"""
        query = db.session.query(
            cls.dnssec_status,
            func.count(cls.id).label('count')
        )
        
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(cls.timestamp >= since)
        
        results = query.group_by(cls.dnssec_status).all()
        
        total = sum(result.count for result in results)
        if total == 0:
            return {'valid': 0, 'invalid': 0, 'error': 0, 'total': 0}
        
        ratios = {'total': total}
        for result in results:
            ratios[result.dnssec_status] = {
                'count': result.count,
                'percentage': round((result.count / total) * 100, 1)
            }
        
        return ratios
    
    @classmethod
    def get_hourly_requests(cls, hours=24):
        """Get hourly request counts for charts"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        results = db.session.query(
            func.strftime('%Y-%m-%d %H:00:00', cls.timestamp).label('hour'),
            func.count(cls.id).label('count')
        ).filter(
            cls.timestamp >= since
        ).group_by(
            func.strftime('%Y-%m-%d %H:00:00', cls.timestamp)
        ).order_by('hour').all()
        
        return [(result.hour, result.count) for result in results]
    
    @classmethod
    def get_source_breakdown(cls, days=None):
        """Get breakdown of API vs webapp requests"""
        query = db.session.query(
            cls.source,
            func.count(cls.id).label('count')
        )
        
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            query = query.filter(cls.timestamp >= since)
        
        return query.group_by(cls.source).all()
