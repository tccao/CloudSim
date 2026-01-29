"""
Configuration module for CloudSim Backend.

Loads environment variables from .env file and provides
typed configuration classes for different parts of the application.

AWS CREDENTIALS:
    - Production: AWS Secrets Manager (prod/cloudsim)
    - Development: root-credentials/credentials file

USAGE:
    from .config import settings, root_access_key, root_secret_key
    print(settings.aws_region)
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Tuple
from functools import lru_cache
import secrets
import warnings
import os
import configparser
import json


# =============================================================================
# AWS CREDENTIALS LOADING
# =============================================================================

def get_root_credentials() -> Tuple[str, str]:
    """Get root AWS credentials from Secrets Manager (for production)."""
    import boto3
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='prod/cloudsim')
    secret = json.loads(response['SecretString'])
    return secret['aws_access_key_id'], secret['aws_secret_access_key']


def load_local_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Load AWS credentials from root-credentials/credentials file (for development)."""
    config = configparser.ConfigParser()
    # Path relative to this file: backend/app/config.py -> root-credentials/credentials
    creds_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'root-credentials',
        'credentials'
    )
    
    if os.path.exists(creds_file):
        config.read(creds_file)
        if 'root' in config:
            return (
                config['root'].get('aws_access_key_id'),
                config['root'].get('aws_secret_access_key')
            )
    
    # Fall back to environment variables
    return os.getenv('AWS_ACCESS_KEY_ID'), os.getenv('AWS_SECRET_ACCESS_KEY')


# Load credentials based on environment
if os.getenv('ENVIRONMENT', 'development').lower() == 'production':
    root_access_key, root_secret_key = get_root_credentials()
else:
    root_access_key, root_secret_key = load_local_credentials()


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic BaseSettings automatically:
    - Reads from environment variables
    - Reads from .env file
    - Validates types
    - Provides defaults
    """
    
    # =========================================================================
    # ENVIRONMENT
    # =========================================================================
    environment: str = "development"  # development, staging, production
    debug: bool = True  # Set to False in production
    
    # =========================================================================
    # DATABASE
    # =========================================================================
    database_url: str = "postgresql://postgres:1@localhost:5432/cloudsim"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # =========================================================================
    # JWT AUTHENTICATION
    # =========================================================================
    secret_key: str = "your-secret-key"
    access_token_expire_minutes: int = 30
    algorithm: str = "HS256"
    
    # =========================================================================
    # CORS & SECURITY
    # =========================================================================
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    
    # =========================================================================
    # AWS CONFIGURATION
    # =========================================================================
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_account_id: str = "096615316348"
    
    # =========================================================================
    # IAM ROLE ARNS (for role-based AWS access)
    # =========================================================================
    # Format: arn:aws:iam::{account_id}:role/{role_name}
    aws_role_admin: Optional[str] = None      # Full access
    aws_role_developer: Optional[str] = None  # View + metrics, no create/terminate
    aws_role_devops: Optional[str] = None     # Developer + create instances
    aws_role_readonly: Optional[str] = None   # View only (User role)
    
    # =========================================================================
    # VPC CONFIGURATION (for dedicated CloudSim network)
    # =========================================================================
    # If set, new instances will be created in this VPC/subnet with this security group
    # Leave empty to use default VPC
    cloudsim_vpc_id: Optional[str] = None           # e.g., vpc-0abc123...
    cloudsim_subnet_id: Optional[str] = None        # Default subnet for new instances
    cloudsim_security_group_id: Optional[str] = None  # Default security group
    
    # =========================================================================
    # APPLICATION SETTINGS
    # =========================================================================
    enable_cost_explorer: bool = True
    enable_role_based_access: bool = False  # Set to True to enable IAM role assumption
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Validate SECRET_KEY security.
        - In production: must be at least 32 characters and not the default
        - In development: warn if using default key
        """
        default_key = "your-secret-key"
        
        # We can't access other fields directly in validators, so check via environment
        import os
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        if env == "production":
            if v == default_key:
                raise ValueError(
                    "SECRET_KEY must be changed from default in production. "
                    "Generate one with: openssl rand -hex 32"
                )
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production"
                )
        elif v == default_key:
            warnings.warn(
                "Using default SECRET_KEY. Generate a secure key for production: "
                "openssl rand -hex 32",
                UserWarning
            )
        
        return v
    
    @property
    def cors_origins(self) -> list[str]:
        """Parse comma-separated origins into list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def generate_secret_key() -> str:
    """Generate a cryptographically secure secret key."""
    return secrets.token_hex(32)


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    Use this function to get settings throughout the application.
    """
    return Settings()


# Convenience alias
settings = get_settings()
