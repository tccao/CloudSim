# =============================================================================
# config.py - Application Configuration
# =============================================================================
# Centralized configuration for CloudSim backend.
# Loads environment variables from .env file using Pydantic BaseSettings.
#
# CONFIGURATION SOURCES (in priority order):
# 1. Environment variables
# 2. .env file
# 3. Default values
#
# AWS CREDENTIALS (in priority order):
# 1. Environment variables / .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# 2. Development only: root-credentials/credentials file
# 3. AWS profile (~/.aws/credentials)
# 4. Default boto3 credential chain
#
# The local root-credentials file is a development super-key convenience and is
# intentionally never loaded when CLOUDSIM_ENVIRONMENT=production.
#
# USAGE:
#   from .config import settings
#   print(settings.aws_region)
#   print(settings.cors_origins)
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, Tuple
from functools import lru_cache
from pathlib import Path
import secrets
import warnings
import os
import configparser


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


# =============================================================================
# AWS CREDENTIALS LOADING
# =============================================================================

def load_local_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Load dev-only AWS super-key credentials from root-credentials/credentials.
    
    Looks for credentials in:
    1. root-credentials/credentials file (INI format, [root] section)
    
    Returns:
        Tuple of (access_key_id, secret_access_key) or (None, None)
    """
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
    
    return None, None


# =============================================================================
# CREDENTIAL INITIALIZATION
# =============================================================================
# Load development super-key credentials only outside production. Environment
# variables and .env still take priority through BaseSettings below.
if os.getenv('CLOUDSIM_ENVIRONMENT', 'development').lower() == 'production':
    root_access_key, root_secret_key = None, None
else:
    root_access_key, root_secret_key = load_local_credentials()


# =============================================================================
# SETTINGS CLASS
# =============================================================================
class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic BaseSettings automatically:
    - Reads from environment variables
    - Reads from .env file
    - Validates types
    - Provides defaults
    """
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # =========================================================================
    # ENVIRONMENT
    # =========================================================================
    environment: str = Field("development", validation_alias="CLOUDSIM_ENVIRONMENT")  # development, staging, production
    debug: bool = Field(True, validation_alias="CLOUDSIM_DEBUG")  # Set to False in production
    
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
    aws_access_key_id: Optional[str] = root_access_key
    aws_secret_access_key: Optional[str] = root_secret_key
    aws_session_token: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_region: str = "us-east-1"
    aws_account_id: str = "096615316348"
    
    # =========================================================================
    # IAM ROLE ARNS (for role-based AWS access)
    # =========================================================================
    # Format: arn:aws:iam::{account_id}:role/{role_name}
    aws_role_admin: Optional[str] = None      # Full access
    aws_role_devops: Optional[str] = None     # Full EC2, no terminate
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
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """
        Validate SECRET_KEY security.
        
        Rules:
        - Production: Must be at least 32 characters and not the default
        - Development: Warn if using default key
        
        Generate a secure key with: openssl rand -hex 32
        """
        default_key = "your-secret-key"
        
        # We can't access other fields directly in validators, so check via environment
        import os
        env = os.getenv("CLOUDSIM_ENVIRONMENT", "development").lower()
        
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
    
    # =========================================================================
    # PROPERTIES
    # =========================================================================
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
    

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def generate_secret_key() -> str:
    """
    Generate a cryptographically secure secret key.
    
    Usage:
        python -c "from app.config import generate_secret_key; print(generate_secret_key())"
    """
    return secrets.token_hex(32)


# =============================================================================
# SETTINGS SINGLETON
# =============================================================================
@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    
    Use this function to get settings throughout the application.
    The @lru_cache decorator ensures the settings are only loaded once.
    """
    return Settings()


# Convenience alias for direct import
settings = get_settings()
