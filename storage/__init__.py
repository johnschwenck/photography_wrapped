"""
Storage package for Photo Metadata Analysis System.
"""

from .storage_provider import (
    StorageProvider,
    LocalStorageProvider,
    S3StorageProvider,
    AzureBlobStorageProvider,
    GCSStorageProvider,
    create_storage_provider
)

__all__ = [
    'StorageProvider',
    'LocalStorageProvider',
    'S3StorageProvider',
    'AzureBlobStorageProvider',
    'GCSStorageProvider',
    'create_storage_provider',
]
