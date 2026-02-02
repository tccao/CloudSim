# =============================================================================
# aws_role_manager.py - AWS IAM Role Management
# =============================================================================
# Provides role-based AWS access using STS AssumeRole.
# Maps CloudSim user roles to IAM roles for fine-grained access control.
#
# ROLE MAPPING:
# - Admin           -> aws_role_admin (Full EC2 + user management)
# - DevOps Engineer -> aws_role_devops (Full EC2 access including terminate, NO user management)
# - User            -> aws_role_readonly (Own instances only)
#
# USAGE:
#   from .aws_role_manager import get_aws_client_for_user
#   
#   # Get EC2 client with user's role-based permissions
#   ec2_client = get_aws_client_for_user('ec2', user.role, user.id)
#
# ENABLE:
#   Set ENABLE_ROLE_BASED_ACCESS=true in .env
#   Configure IAM role ARNs: AWS_ROLE_ADMIN, AWS_ROLE_DEVOPS, AWS_ROLE_READONLY
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================
import boto3
from typing import Dict, Optional
from botocore.exceptions import ClientError
import logging

from .config import settings


# =============================================================================
# LOGGING
# =============================================================================
logger = logging.getLogger(__name__)


# =============================================================================
# AWS ROLE MANAGER CLASS
# =============================================================================
class AWSRoleManager:
    """
    Production-grade AWS role management with AssumeRole.
    
    Creates AWS clients with temporary credentials based on user role.
    Caches credentials to avoid repeated STS calls.
    
    FEATURES:
    - Assumes IAM roles via STS
    - Caches clients for performance
    - Auto-refreshes expired credentials
    """
    
    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------
    def __init__(self):
        """Initialize STS client and credential cache."""
        self.sts_client = boto3.client(
            'sts',
            region_name=settings.aws_region,
        )
        self._role_sessions: Dict[str, Dict] = {}
    
    # -------------------------------------------------------------------------
    # Assume Role
    # -------------------------------------------------------------------------
    def assume_role(self, role_arn: str, session_name: str, duration: int = 3600) -> Dict:
        """
        Assume an IAM role and return temporary credentials.
        
        Args:
            role_arn: Full ARN of the role to assume
                      (e.g., arn:aws:iam::123456789012:role/CloudSimAdmin)
            session_name: Name for the session (appears in CloudTrail)
            duration: How long credentials are valid (seconds, default 1 hour)
            
        Returns:
            Credentials dict with:
            - AccessKeyId
            - SecretAccessKey
            - SessionToken
            - Expiration
            
        Raises:
            ClientError: If role assumption fails
        """
        try:
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                DurationSeconds=duration
            )
            logger.info(f"Assumed role {role_arn} for session {session_name}")
            return response['Credentials']
        except ClientError as e:
            logger.error(f"Failed to assume role {role_arn}: {e}")
            raise
    
    # -------------------------------------------------------------------------
    # Get Service Client
    # -------------------------------------------------------------------------
    def get_service_client(self, service: str, role_arn: str, session_name: str):
        """
        Get AWS service client with assumed role credentials.
        
        Args:
            service: AWS service name (ec2, cloudwatch, ce, etc.)
            role_arn: IAM role ARN to assume
            session_name: Session identifier for CloudTrail
            
        Returns:
            boto3 client for the specified service
        """
        credentials = self.assume_role(role_arn, session_name)
        
        return boto3.client(
            service,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=settings.aws_region,
        )
    
    # -------------------------------------------------------------------------
    # Get Cached Client
    # -------------------------------------------------------------------------
    def get_cached_client(self, service: str, role_arn: str, user_id: str):
        """
        Get cached client or create new one if expired.
        
        Caches clients by user_id:role_arn:service combination.
        Automatically refreshes if credentials are expired.
        
        Args:
            service: AWS service name
            role_arn: IAM role ARN
            user_id: User identifier (for session naming and caching)
            
        Returns:
            boto3 client for the specified service
        """
        cache_key = f"{user_id}:{role_arn}:{service}"
        
        # Check if we have a cached client
        if cache_key in self._role_sessions:
            try:
                client = self._role_sessions[cache_key]
                # Test with a simple call to verify credentials still valid
                if service == 'ec2':
                    client.describe_regions(MaxResults=1)
                return client
            except ClientError:
                # Credentials expired, remove from cache
                del self._role_sessions[cache_key]
                logger.info(f"Cached credentials expired for {cache_key}")
        
        # Create new client
        session_name = f"cloudsim-{user_id}-{service}"[:64]  # Max 64 chars
        client = self.get_service_client(service, role_arn, session_name)
        self._role_sessions[cache_key] = client
        
        return client


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================
_role_manager: Optional[AWSRoleManager] = None


def get_role_manager() -> AWSRoleManager:
    """
    Get or create the role manager singleton.
    
    Returns the same AWSRoleManager instance on each call.
    """
    global _role_manager
    if _role_manager is None:
        _role_manager = AWSRoleManager()
    return _role_manager


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_role_arn_for_user(user_role: str) -> Optional[str]:
    """
    Map CloudSim user role to IAM role ARN.
    
    Args:
        user_role: CloudSim role (Admin, DevOps Engineer, User)
        
    Returns:
        IAM role ARN or None if role-based access is disabled
        
    Role Mapping:
        Admin        -> settings.aws_role_admin
        DevOps Engineer -> settings.aws_role_devops
        User         -> settings.aws_role_readonly
    """
    if not settings.enable_role_based_access:
        return None
    
    role_mapping = {
        'Admin': settings.aws_role_admin,
        'DevOps Engineer': settings.aws_role_devops,
        'User': settings.aws_role_readonly,
    }
    
    return role_mapping.get(user_role)


def get_aws_client_for_user(service: str, user_role: str, user_id: int):
    """
    Factory function to get AWS client based on user role.
    
    If role-based access is disabled, returns None (caller should use default client).
    If enabled, returns a client with assumed role credentials.
    
    Args:
        service: AWS service name (ec2, cloudwatch, ce)
        user_role: CloudSim user role (Admin, DevOps Engineer, User)
        user_id: User ID for session naming
        
    Returns:
        boto3 client or None if role-based access is disabled
        
    Example:
        client = get_aws_client_for_user('ec2', 'DevOps Engineer', 123)
        if client:
            instances = client.describe_instances()
        else:
            # Use default client
            instances = ec2.describe_instances()
    """
    role_arn = get_role_arn_for_user(user_role)
    
    if not role_arn:
        logger.debug(f"Role-based access disabled or no role for {user_role}")
        return None
    
    role_manager = get_role_manager()
    return role_manager.get_cached_client(service, role_arn, str(user_id))