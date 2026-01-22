"""High-level S3 manager for data operations."""

import io
from typing import Optional, Dict, List, Any
from pathlib import Path

import pandas as pd

from aws.s3.s3_client import S3Client, Boto3S3Client
from aws.s3.exceptions import S3Error, S3UploadError, S3DownloadError
from utils import get_logger

logger = get_logger(__name__)


class S3Manager:
    """High-level manager for S3 operations with convenience methods."""
    
    def __init__(
        self,
        bucket_name: str,
        s3_client: Optional[S3Client] = None,
        default_prefix: Optional[str] = None,
    ):
        """
        Initialize S3 manager.
        
        Args:
            bucket_name: Default S3 bucket name
            s3_client: Optional S3Client instance (creates Boto3S3Client if not provided)
            default_prefix: Optional default prefix for object keys
        """
        self.bucket_name = bucket_name
        self.default_prefix = default_prefix or ""
        self.s3_client = s3_client or Boto3S3Client()
        
        logger.info(
            f"S3Manager initialized for bucket: {bucket_name}, "
            f"prefix: {self.default_prefix}"
        )
    
    def _build_key(self, object_key: str) -> str:
        """Build full object key with prefix."""
        if self.default_prefix:
            return f"{self.default_prefix.rstrip('/')}/{object_key.lstrip('/')}"
        return object_key.lstrip("/")
    
    def upload_file(
        self,
        object_key: str,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Upload a file to S3.
        
        Args:
            object_key: S3 object key (path)
            file_path: Local file path to upload
            metadata: Optional metadata dictionary
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            True if upload successful
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.upload_file(
            bucket_name=bucket,
            object_key=full_key,
            file_path=file_path,
            metadata=metadata,
        )
    
    def download_file(
        self,
        object_key: str,
        file_path: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Download a file from S3.
        
        Args:
            object_key: S3 object key (path)
            file_path: Local file path to save the downloaded file
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            True if download successful
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.download_file(
            bucket_name=bucket,
            object_key=full_key,
            file_path=file_path,
        )
    
    def upload_dataframe(
        self,
        object_key: str,
        dataframe: pd.DataFrame,
        format: str = "parquet",
        metadata: Optional[Dict[str, str]] = None,
        bucket_name: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """
        Upload a pandas DataFrame to S3.
        
        Args:
            object_key: S3 object key (path)
            dataframe: pandas DataFrame to upload
            format: File format ('parquet', 'csv', 'json', 'pickle')
            metadata: Optional metadata dictionary
            bucket_name: Optional bucket name (uses default if not provided)
            **kwargs: Additional arguments for pandas to_* methods
            
        Returns:
            True if upload successful
            
        Raises:
            S3UploadError: If upload fails
        """
        try:
            bucket = bucket_name or self.bucket_name
            full_key = self._build_key(object_key)
            
            # Ensure file extension matches format
            if not full_key.endswith(f".{format}"):
                full_key = f"{full_key}.{format}"
            
            # Convert DataFrame to bytes based on format
            buffer = io.BytesIO()
            
            if format.lower() == "parquet":
                dataframe.to_parquet(buffer, index=True, **kwargs)
            elif format.lower() == "csv":
                dataframe.to_csv(buffer, index=True, **kwargs)
            elif format.lower() == "json":
                dataframe.to_json(buffer, orient="records", **kwargs)
            elif format.lower() == "pickle":
                dataframe.to_pickle(buffer, **kwargs)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            buffer.seek(0)
            data = buffer.read()
            
            # Add format to metadata
            if metadata is None:
                metadata = {}
            metadata["dataframe_format"] = format
            metadata["rows"] = str(len(dataframe))
            metadata["columns"] = str(len(dataframe.columns))
            
            return self.s3_client.upload_bytes(
                bucket_name=bucket,
                object_key=full_key,
                data=data,
                metadata=metadata,
            )
            
        except Exception as e:
            logger.error(f"Failed to upload DataFrame: {e}")
            raise S3UploadError(f"Failed to upload DataFrame: {e}") from e
    
    def download_dataframe(
        self,
        object_key: str,
        format: Optional[str] = None,
        bucket_name: Optional[str] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """
        Download a pandas DataFrame from S3.
        
        Args:
            object_key: S3 object key (path)
            format: File format ('parquet', 'csv', 'json', 'pickle'). 
                    If None, inferred from file extension
            bucket_name: Optional bucket name (uses default if not provided)
            **kwargs: Additional arguments for pandas read_* methods
            
        Returns:
            pandas DataFrame
            
        Raises:
            S3DownloadError: If download fails
        """
        try:
            bucket = bucket_name or self.bucket_name
            full_key = self._build_key(object_key)
            
            # Infer format from extension if not provided
            if format is None:
                if full_key.endswith(".parquet"):
                    format = "parquet"
                elif full_key.endswith(".csv"):
                    format = "csv"
                elif full_key.endswith(".json"):
                    format = "json"
                elif full_key.endswith(".pkl") or full_key.endswith(".pickle"):
                    format = "pickle"
                else:
                    raise ValueError(
                        f"Cannot infer format from {object_key}. "
                        "Please specify format parameter."
                    )
            
            # Download bytes
            data = self.s3_client.download_bytes(
                bucket_name=bucket,
                object_key=full_key,
            )
            
            # Convert bytes to DataFrame
            buffer = io.BytesIO(data)
            
            if format.lower() == "parquet":
                return pd.read_parquet(buffer, **kwargs)
            elif format.lower() == "csv":
                return pd.read_csv(buffer, **kwargs)
            elif format.lower() == "json":
                return pd.read_json(buffer, orient="records", **kwargs)
            elif format.lower() == "pickle":
                return pd.read_pickle(buffer, **kwargs)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to download DataFrame: {e}")
            raise S3DownloadError(f"Failed to download DataFrame: {e}") from e
    
    def upload_bytes(
        self,
        object_key: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Upload bytes data to S3.
        
        Args:
            object_key: S3 object key (path)
            data: Bytes data to upload
            metadata: Optional metadata dictionary
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            True if upload successful
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.upload_bytes(
            bucket_name=bucket,
            object_key=full_key,
            data=data,
            metadata=metadata,
        )
    
    def download_bytes(
        self,
        object_key: str,
        bucket_name: Optional[str] = None,
    ) -> bytes:
        """
        Download bytes data from S3.
        
        Args:
            object_key: S3 object key (path)
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            Bytes data from S3
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.download_bytes(
            bucket_name=bucket,
            object_key=full_key,
        )
    
    def delete_object(
        self,
        object_key: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Delete an object from S3.
        
        Args:
            object_key: S3 object key (path)
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            True if deletion successful
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.delete_object(
            bucket_name=bucket,
            object_key=full_key,
        )
    
    def object_exists(
        self,
        object_key: str,
        bucket_name: Optional[str] = None,
    ) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            object_key: S3 object key (path)
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            True if object exists, False otherwise
        """
        bucket = bucket_name or self.bucket_name
        full_key = self._build_key(object_key)
        
        return self.s3_client.object_exists(
            bucket_name=bucket,
            object_key=full_key,
        )
    
    def list_objects(
        self,
        prefix: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> List[str]:
        """
        List objects in the bucket.
        
        Args:
            prefix: Optional prefix to filter objects
            bucket_name: Optional bucket name (uses default if not provided)
            
        Returns:
            List of object keys
        """
        bucket = bucket_name or self.bucket_name
        full_prefix = self._build_key(prefix) if prefix else self.default_prefix
        
        return self.s3_client.list_objects(
            bucket_name=bucket,
            prefix=full_prefix,
        )
    
    def upload_directory(
        self,
        directory_path: str,
        s3_prefix: Optional[str] = None,
        bucket_name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> List[str]:
        """
        Upload all files in a directory to S3.
        
        Args:
            directory_path: Local directory path
            s3_prefix: Optional S3 prefix for uploaded files
            bucket_name: Optional bucket name (uses default if not provided)
            metadata: Optional metadata dictionary to apply to all files
            
        Returns:
            List of uploaded object keys
        """
        directory = Path(directory_path)
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory_path}")
        
        uploaded_keys = []
        
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(directory)
                object_key = f"{s3_prefix}/{relative_path}" if s3_prefix else str(relative_path)
                
                try:
                    self.upload_file(
                        object_key=object_key,
                        file_path=str(file_path),
                        metadata=metadata,
                        bucket_name=bucket_name,
                    )
                    uploaded_keys.append(object_key)
                    logger.debug(f"Uploaded {file_path} to {object_key}")
                except Exception as e:
                    logger.error(f"Failed to upload {file_path}: {e}")
                    raise
        
        logger.info(f"Uploaded {len(uploaded_keys)} files from {directory_path}")
        return uploaded_keys
