#!/usr/bin/env python3
"""
Database initialization module for DNSSEC Validator.

This module handles database management operations based on environment variables
set at startup, including database recreation and truncation.
"""

import os
import sys
import time
from datetime import datetime
from models import influx_logger

def initialize_database():
    """
    Initialize database based on environment variables.
    
    Environment Variables:
    - INFLUX_DB_RECREATE: Set to 'true' to recreate the database/bucket
    - INFLUX_DB_VERSION: Optional version string for schema versioning
    - INFLUX_DB_TRUNCATE: Set to 'true' to truncate all data (dangerous!)
    - INFLUX_DB_INIT_WAIT: Seconds to wait for InfluxDB to be ready (default: 5)
    """
    
    print("=" * 60)
    print("🗄️  DNSSEC Validator - Database Initialization")
    print("=" * 60)
    
    # Get environment variables
    recreate_db = os.getenv('INFLUX_DB_RECREATE', 'false').lower() == 'true'
    truncate_db = os.getenv('INFLUX_DB_TRUNCATE', 'false').lower() == 'true'
    db_version = os.getenv('INFLUX_DB_VERSION', None)
    init_wait = int(os.getenv('INFLUX_DB_INIT_WAIT', '5'))
    
    print(f"📊 InfluxDB Configuration:")
    print(f"   URL: {influx_logger.url}")
    print(f"   Organization: {influx_logger.org}")
    print(f"   Bucket: {influx_logger.bucket}")
    print(f"   Recreate Database: {recreate_db}")
    print(f"   Truncate Database: {truncate_db}")
    print(f"   Schema Version: {db_version or 'Not specified'}")
    print()
    
    # Validate conflicting options
    if recreate_db and truncate_db:
        print("⚠️  WARNING: Both RECREATE and TRUNCATE are set to true.")
        print("   RECREATE will be performed (truncate is redundant).")
        truncate_db = False
    
    # Wait for InfluxDB to be ready
    if init_wait > 0:
        print(f"⏳ Waiting {init_wait} seconds for InfluxDB to be ready...")
        time.sleep(init_wait)
    
    try:
        # Test connection first
        print("🔍 Testing InfluxDB connection...")
        if not influx_logger.client:
            print("❌ Failed to connect to InfluxDB")
            return False
        
        health = influx_logger.client.health()
        if health.status != "pass":
            print(f"❌ InfluxDB health check failed: {health.message}")
            return False
            
        print("✅ Successfully connected to InfluxDB")
        
        # Get current database info
        print("📋 Current database information:")
        db_info = influx_logger.get_database_info()
        if 'error' in db_info:
            print(f"   Status: {db_info['error']}")
        else:
            print(f"   Bucket: {db_info['bucket_name']} (ID: {db_info['bucket_id']})")
            print(f"   Description: {db_info.get('description', 'No description')}")
            print(f"   Created: {db_info.get('created_at', 'Unknown')}")
            if db_info.get('retention_rules'):
                for rule in db_info['retention_rules']:
                    print(f"   Retention: {rule.get('days', 'Unknown')} days")
        print()
        
        # Perform database operations
        success = True
        
        if recreate_db:
            print("🔄 Recreating database...")
            if influx_logger.recreate_database(version=db_version):
                print("✅ Database recreated successfully")
            else:
                print("❌ Failed to recreate database")
                success = False
                
        elif truncate_db:
            print("⚠️  🗑️  TRUNCATING DATABASE - ALL DATA WILL BE LOST!")
            print("   This operation will delete all historical data.")
            print("   Proceeding in 3 seconds... (Ctrl+C to cancel)")
            
            try:
                for i in range(3, 0, -1):
                    print(f"   {i}...")
                    time.sleep(1)
                
                print("   Truncating now...")
                if influx_logger.truncate_database():
                    print("✅ Database truncated successfully")
                else:
                    print("❌ Failed to truncate database")
                    success = False
                    
            except KeyboardInterrupt:
                print("\\n⏹️  Truncation cancelled by user")
                return False
        
        # Display final status
        if success:
            print()
            print("📋 Final database information:")
            final_db_info = influx_logger.get_database_info()
            if 'error' in final_db_info:
                print(f"   Status: {final_db_info['error']}")
            else:
                print(f"   Bucket: {final_db_info['bucket_name']} (ID: {final_db_info['bucket_id']})")
                print(f"   Description: {final_db_info.get('description', 'No description')}")
                print(f"   Created: {final_db_info.get('created_at', 'Unknown')}")
            
            print()
            print("✅ Database initialization completed successfully")
            print("🚀 Ready to start DNSSEC Validator application")
            
        else:
            print("❌ Database initialization failed")
            return False
            
    except KeyboardInterrupt:
        print("\\n⏹️  Database initialization cancelled by user")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error during database initialization: {e}")
        return False
        
    finally:
        print("=" * 60)
    
    return success

def print_environment_variables():
    """Print all relevant environment variables for debugging."""
    print("🔧 Environment Variables:")
    env_vars = [
        'INFLUX_URL', 'INFLUX_ORG', 'INFLUX_BUCKET', 'INFLUX_TOKEN',
        'INFLUX_DB_RECREATE', 'INFLUX_DB_TRUNCATE', 'INFLUX_DB_VERSION', 'INFLUX_DB_INIT_WAIT'
    ]
    
    for var in env_vars:
        value = os.getenv(var, 'Not set')
        if 'TOKEN' in var and value != 'Not set':
            value = f"{value[:8]}..." if len(value) > 8 else "***"
        print(f"   {var}: {value}")
    print()

if __name__ == "__main__":
    """Allow running this module directly for testing."""
    print_environment_variables()
    success = initialize_database()
    sys.exit(0 if success else 1)
