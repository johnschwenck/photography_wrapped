"""
Storage Provider

Unified interface for accessing photos from local storage or cloud providers
(AWS S3, Azure Blob Storage, Google Cloud Storage).
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, BinaryIO
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """
    Abstract base class for storage providers.
    
    Defines the interface that all storage providers must implement,
    enabling seamless switching between local and cloud storage.
    """
    
    @abstractmethod
    def list_files(self, prefix: str, extensions: Optional[List[str]] = None) -> List[str]:
        """
        List files in storage matching prefix and extensions.
        
        Args:
            prefix: Path prefix to search under
            extensions: List of file extensions to filter (e.g., ['.jpg', '.arw'])
        
        Returns:
            List of file paths/URIs
        """
        pass
    
    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if file exists."""
        pass
    
    @abstractmethod
    def get_file(self, path: str) -> BinaryIO:
        """
        Get file content as binary stream.
        
        Args:
            path: Path to file
        
        Returns:
            Binary file stream
        """
        pass
    
    @abstractmethod
    def get_file_size(self, path: str) -> int:
        """Get file size in bytes."""
        pass
    
    @abstractmethod
    def get_modified_time(self, path: str) -> float:
        """Get file modification timestamp."""
        pass


class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage provider.
    
    Accesses files from the local filesystem.
    
    Attributes:
        base_path: Base directory for file operations
    
    Example:
        >>> storage = LocalStorageProvider('/photos')
        >>> files = storage.list_files('2025/concerts', ['.jpg', '.arw'])
    """
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize local storage provider.
        
        Args:
            base_path: Base directory path (optional)
        """
        self.base_path = base_path
    
    def list_files(self, prefix: str, extensions: Optional[List[str]] = None) -> List[str]:
        """List files in local directory."""
        search_path = os.path.join(self.base_path, prefix) if self.base_path else prefix
        files = []
        
        if not os.path.exists(search_path):
            logger.warning(f"Path does not exist: {search_path}")
            return files
        
        for root, dirs, filenames in os.walk(search_path):
            for filename in filenames:
                if extensions:
                    if any(filename.lower().endswith(ext.lower()) for ext in extensions):
                        files.append(os.path.join(root, filename))
                else:
                    files.append(os.path.join(root, filename))
        
        return files
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists locally."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        return os.path.exists(full_path)
    
    def get_file(self, path: str) -> BinaryIO:
        """Open local file for reading."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        return open(full_path, 'rb')
    
    def get_file_size(self, path: str) -> int:
        """Get local file size."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        return os.path.getsize(full_path)
    
    def get_modified_time(self, path: str) -> float:
        """Get local file modification time."""
        full_path = os.path.join(self.base_path, path) if self.base_path else path
        return os.path.getmtime(full_path)


class S3StorageProvider(StorageProvider):
    """
    AWS S3 storage provider.
    
    Accesses files from Amazon S3 buckets.
    
    Attributes:
        bucket: S3 bucket name
        region: AWS region
        client: boto3 S3 client
    
    Example:
        >>> storage = S3StorageProvider(
        ...     bucket='my-photo-bucket',
        ...     region='us-east-1'
        ... )
        >>> files = storage.list_files('photos/2025', ['.jpg'])
    """
    
    def __init__(self, bucket: str, region: str = 'us-east-1',
                 access_key_id: Optional[str] = None, secret_access_key: Optional[str] = None):
        """
        Initialize S3 storage provider.
        
        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key_id: AWS access key (optional, uses default credentials)
            secret_access_key: AWS secret key (optional)
        """
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 required for S3 storage. Install with: pip install boto3")
        
        self.bucket = bucket
        self.region = region
        
        if access_key_id and secret_access_key:
            self.client = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key
            )
        else:
            # Use default credentials
            self.client = boto3.client('s3', region_name=region)
        
        logger.info(f"Connected to S3 bucket: {bucket}")
    
    def list_files(self, prefix: str, extensions: Optional[List[str]] = None) -> List[str]:
        """List files in S3 bucket."""
        files = []
        paginator = self.client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue
            
            for obj in page['Contents']:
                key = obj['Key']
                if extensions:
                    if any(key.lower().endswith(ext.lower()) for ext in extensions):
                        files.append(f"s3://{self.bucket}/{key}")
                else:
                    files.append(f"s3://{self.bucket}/{key}")
        
        return files
    
    def file_exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        # Remove s3://bucket/ prefix if present
        key = path.replace(f"s3://{self.bucket}/", "")
        
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False
    
    def get_file(self, path: str) -> BinaryIO:
        """Download file from S3."""
        from io import BytesIO
        
        key = path.replace(f"s3://{self.bucket}/", "")
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return BytesIO(obj['Body'].read())
    
    def get_file_size(self, path: str) -> int:
        """Get S3 object size."""
        key = path.replace(f"s3://{self.bucket}/", "")
        response = self.client.head_object(Bucket=self.bucket, Key=key)
        return response['ContentLength']
    
    def get_modified_time(self, path: str) -> float:
        """Get S3 object last modified time."""
        key = path.replace(f"s3://{self.bucket}/", "")
        response = self.client.head_object(Bucket=self.bucket, Key=key)
        return response['LastModified'].timestamp()


class AzureBlobStorageProvider(StorageProvider):
    """
    Azure Blob Storage provider.
    
    Accesses files from Azure Blob Storage containers.
    
    Example:
        >>> storage = AzureBlobStorageProvider(
        ...     account_name='myaccount',
        ...     container='photos'
        ... )
    """
    
    def __init__(self, account_name: str, container: str, account_key: Optional[str] = None):
        """
        Initialize Azure Blob Storage provider.
        
        Args:
            account_name: Azure storage account name
            container: Container name
            account_key: Account key (optional, uses default credentials)
        """
        try:
            from azure.storage.blob import BlobServiceClient  # type: ignore
        except ImportError:
            raise ImportError("azure-storage-blob is required for Azure storage. Install with: pip install azure-storage-blob")
        
        self.account_name = account_name
        self.container = container
        
        if account_key:
            connection_string = (
                f"DefaultEndpointsProtocol=https;"
                f"AccountName={account_name};"
                f"AccountKey={account_key};"
                f"EndpointSuffix=core.windows.net"
            )
            self.client = BlobServiceClient.from_connection_string(connection_string)
        else:
            # Use default credentials
            account_url = f"https://{account_name}.blob.core.windows.net"
            self.client = BlobServiceClient(account_url=account_url)
        
        self.container_client = self.client.get_container_client(container)
        logger.info(f"Connected to Azure Blob Storage: {container}")
    
    def list_files(self, prefix: str, extensions: Optional[List[str]] = None) -> List[str]:
        """List blobs in container."""
        files = []
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        
        for blob in blobs:
            if extensions:
                if any(blob.name.lower().endswith(ext.lower()) for ext in extensions):
                    files.append(f"azure://{self.container}/{blob.name}")
            else:
                files.append(f"azure://{self.container}/{blob.name}")
        
        return files
    
    def file_exists(self, path: str) -> bool:
        """Check if blob exists."""
        blob_name = path.replace(f"azure://{self.container}/", "")
        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.exists()
    
    def get_file(self, path: str) -> BinaryIO:
        """Download blob."""
        from io import BytesIO
        
        blob_name = path.replace(f"azure://{self.container}/", "")
        blob_client = self.container_client.get_blob_client(blob_name)
        stream = BytesIO()
        blob_client.download_blob().readinto(stream)
        stream.seek(0)
        return stream
    
    def get_file_size(self, path: str) -> int:
        """Get blob size."""
        blob_name = path.replace(f"azure://{self.container}/", "")
        blob_client = self.container_client.get_blob_client(blob_name)
        properties = blob_client.get_blob_properties()
        return properties.size
    
    def get_modified_time(self, path: str) -> float:
        """Get blob last modified time."""
        blob_name = path.replace(f"azure://{self.container}/", "")
        blob_client = self.container_client.get_blob_client(blob_name)
        properties = blob_client.get_blob_properties()
        return properties.last_modified.timestamp()


class GCSStorageProvider(StorageProvider):
    """
    Google Cloud Storage provider.
    
    Accesses files from GCS buckets.
    
    Example:
        >>> storage = GCSStorageProvider(
        ...     bucket='my-photo-bucket',
        ...     project_id='my-project'
        ... )
    """
    
    def __init__(self, bucket: str, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """
        Initialize GCS storage provider.
        
        Args:
            bucket: GCS bucket name
            project_id: GCP project ID (optional)
            credentials_path: Path to service account JSON (optional)
        """
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage required for GCS. "
                "Install with: pip install google-cloud-storage"
            )
        
        if credentials_path:
            self.client = storage.Client.from_service_account_json(
                credentials_path,
                project=project_id
            )
        else:
            self.client = storage.Client(project=project_id)
        
        self.bucket = self.client.bucket(bucket)
        logger.info(f"Connected to GCS bucket: {bucket}")
    
    def list_files(self, prefix: str, extensions: Optional[List[str]] = None) -> List[str]:
        """List blobs in GCS bucket."""
        files = []
        blobs = self.bucket.list_blobs(prefix=prefix)
        
        for blob in blobs:
            if extensions:
                if any(blob.name.lower().endswith(ext.lower()) for ext in extensions):
                    files.append(f"gs://{self.bucket.name}/{blob.name}")
            else:
                files.append(f"gs://{self.bucket.name}/{blob.name}")
        
        return files
    
    def file_exists(self, path: str) -> bool:
        """Check if blob exists."""
        blob_name = path.replace(f"gs://{self.bucket.name}/", "")
        blob = self.bucket.blob(blob_name)
        return blob.exists()
    
    def get_file(self, path: str) -> BinaryIO:
        """Download blob."""
        from io import BytesIO
        
        blob_name = path.replace(f"gs://{self.bucket.name}/", "")
        blob = self.bucket.blob(blob_name)
        stream = BytesIO()
        blob.download_to_file(stream)
        stream.seek(0)
        return stream
    
    def get_file_size(self, path: str) -> int:
        """Get blob size."""
        blob_name = path.replace(f"gs://{self.bucket.name}/", "")
        blob = self.bucket.blob(blob_name)
        blob.reload()
        return blob.size or 0  # type: ignore
    
    def get_modified_time(self, path: str) -> float:
        """Get blob update time."""
        blob_name = path.replace(f"gs://{self.bucket.name}/", "")
        blob = self.bucket.blob(blob_name)
        blob.reload()
        return blob.updated.timestamp() if blob.updated else 0.0  # type: ignore


def create_storage_provider(config_path: str = 'config.yaml') -> StorageProvider:
    """
    Factory function to create storage provider from configuration.
    
    Args:
        config_path: Path to YAML configuration file
    
    Returns:
        Configured StorageProvider instance
    
    Example:
        >>> storage = create_storage_provider('config.yaml')
        >>> files = storage.list_files('photos/2025', ['.jpg'])
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    storage_config = config.get('storage', {})
    storage_type = storage_config.get('type', 'local')
    
    if storage_type == 'local':
        local_config = storage_config.get('local', {})
        return LocalStorageProvider(
            base_path=local_config.get('photos_base_path')
        )
    
    elif storage_type == 's3':
        s3_config = storage_config.get('s3', {})
        aws_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
        if not aws_key_id or not aws_secret:
            raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables are required for S3 storage")
        return S3StorageProvider(
            bucket=os.getenv('S3_BUCKET', s3_config.get('bucket')),
            region=s3_config.get('region', 'us-east-1'),
            access_key_id=aws_key_id,
            secret_access_key=aws_secret
        )
    
    elif storage_type == 'azure':
        azure_config = storage_config.get('azure', {})
        # account_key is optional (can use DefaultAzureCredential)
        return AzureBlobStorageProvider(
            account_name=os.getenv('AZURE_STORAGE_ACCOUNT', azure_config.get('account_name')),
            container=azure_config.get('container'),
            account_key=os.getenv('AZURE_STORAGE_KEY')  # type: ignore
        )
    
    elif storage_type == 'gcs':
        gcs_config = storage_config.get('gcs', {})
        return GCSStorageProvider(
            bucket=os.getenv('GCS_BUCKET', gcs_config.get('bucket')),
            project_id=os.getenv('GCP_PROJECT_ID', gcs_config.get('project_id')),
            credentials_path=os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 
                                      gcs_config.get('credentials_path'))
        )
    
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
