"""Base S3 client for AWS S3 operations."""

import io
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.client import BaseClient

from config import get_config
from aws.s3.exceptions import (
    S3Error,
    S3ConnectionError,
    S3UploadError,
    S3DownloadError,
    S3BucketError,
    S3ObjectError,
)
from utils import get_logger

logger = get_logger(__name__)


class S3Client(ABC):
    """Abstract base class for S3 client operations."""
    
    @abstractmethod
    def upload_file(
        self,
        bucket_name: str,
        object_key: str,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Upload a file to S3."""
        pass
    
    @abstractmethod
    def download_file(
        self,
        bucket_name: str,
        object_key: str,
        file_path: str,
    ) -> bool:
        """Download a file from S3."""
        pass
    
    @abstractmethod
    def upload_bytes(
        self,
        bucket_name: str,
        object_key: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Upload bytes data to S3."""
        pass
    
    @abstractmethod
    def download_bytes(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        """Download bytes data from S3."""
        pass
    
    @abstractmethod
    def delete_object(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bool:
        """Delete an object from S3."""
        pass
    
    @abstractmethod
    def object_exists(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bool:
        """Check if an object exists in S3."""
        pass
    
    @abstractmethod
    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
    ) -> list:
        """List objects in a bucket."""
        pass


class Boto3S3Client(S3Client):
    """Boto3-based implementation of S3Client."""
    
    def __init__(
        self,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize Boto3 S3 client.
        
        Args:
            aws_access_key_id: AWS access key ID (defaults to config or env)
            aws_secret_access_key: AWS secret access key (defaults to config or env)
            region_name: AWS region name (defaults to config or env)
            endpoint_url: Custom endpoint URL (for S3-compatible services)
        """
        config = get_config()
        
        self.aws_access_key_id = aws_access_key_id or getattr(
            config, "aws_access_key_id", None
        )
        self.aws_secret_access_key = aws_secret_access_key or getattr(
            config, "aws_secret_access_key", None
        )
        self.region_name = region_name or getattr(config, "aws_region", "us-east-1")
        self.endpoint_url = endpoint_url or getattr(config, "aws_endpoint_url", None)
        
        self._s3_client: Optional[BaseClient] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the boto3 S3 client."""
        try:
            client_kwargs = {
                "region_name": self.region_name,
            }
            
            if self.aws_access_key_id and self.aws_secret_access_key:
                client_kwargs.update({
                    "aws_access_key_id": self.aws_access_key_id,
                    "aws_secret_access_key": self.aws_secret_access_key,
                })
            
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            
            self._s3_client = boto3.client("s3", **client_kwargs)
            logger.info(f"S3 client initialized for region: {self.region_name}")
            
        except (BotoCoreError, Exception) as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise S3ConnectionError(f"Failed to initialize S3 client: {e}") from e
    
    @property
    def s3_client(self) -> BaseClient:
        """Get the S3 client instance."""
        if self._s3_client is None:
            self._initialize_client()
        return self._s3_client
    
    def _ensure_bucket_exists(self, bucket_name: str) -> None:
        """Ensure bucket exists, create if it doesn't."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            logger.debug(f"Bucket {bucket_name} exists")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                try:
                    self.s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={
                            "LocationConstraint": self.region_name
                        } if self.region_name != "us-east-1" else {}
                    )
                    logger.info(f"Created bucket: {bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket {bucket_name}: {create_error}")
                    raise S3BucketError(
                        f"Failed to create bucket {bucket_name}: {create_error}"
                    ) from create_error
            else:
                logger.error(f"Error checking bucket {bucket_name}: {e}")
                raise S3BucketError(f"Error accessing bucket {bucket_name}: {e}") from e
    
    def upload_file(
        self,
        bucket_name: str,
        object_key: str,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Upload a file to S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            file_path: Local file path to upload
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful
            
        Raises:
            S3UploadError: If upload fails
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            self._ensure_bucket_exists(bucket_name)
            
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata
            
            self.s3_client.upload_file(
                str(file_path_obj),
                bucket_name,
                object_key,
                ExtraArgs=extra_args if extra_args else None,
            )
            
            logger.info(
                f"Successfully uploaded {file_path} to s3://{bucket_name}/{object_key}"
            )
            return True
            
        except FileNotFoundError as e:
            logger.error(f"File not found for upload: {e}")
            raise S3UploadError(f"File not found: {file_path}") from e
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise S3UploadError(
                f"Failed to upload {file_path} to s3://{bucket_name}/{object_key}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            raise S3UploadError(f"Unexpected error during upload: {e}") from e
    
    def download_file(
        self,
        bucket_name: str,
        object_key: str,
        file_path: str,
    ) -> bool:
        """
        Download a file from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            file_path: Local file path to save the downloaded file
            
        Returns:
            True if download successful
            
        Raises:
            S3DownloadError: If download fails
        """
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            self.s3_client.download_file(
                bucket_name,
                object_key,
                str(file_path_obj),
            )
            
            logger.info(
                f"Successfully downloaded s3://{bucket_name}/{object_key} to {file_path}"
            )
            return True
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                logger.error(f"Object not found: s3://{bucket_name}/{object_key}")
                raise S3DownloadError(
                    f"Object not found: s3://{bucket_name}/{object_key}"
                ) from e
            else:
                logger.error(f"Failed to download file from S3: {e}")
                raise S3DownloadError(
                    f"Failed to download s3://{bucket_name}/{object_key}: {e}"
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            raise S3DownloadError(f"Unexpected error during download: {e}") from e
    
    def upload_bytes(
        self,
        bucket_name: str,
        object_key: str,
        data: bytes,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Upload bytes data to S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            data: Bytes data to upload
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful
            
        Raises:
            S3UploadError: If upload fails
        """
        try:
            self._ensure_bucket_exists(bucket_name)
            
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata
            
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=data,
                **extra_args,
            )
            
            logger.info(
                f"Successfully uploaded bytes to s3://{bucket_name}/{object_key} "
                f"({len(data)} bytes)"
            )
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload bytes to S3: {e}")
            raise S3UploadError(
                f"Failed to upload bytes to s3://{bucket_name}/{object_key}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during bytes upload: {e}")
            raise S3UploadError(f"Unexpected error during bytes upload: {e}") from e
    
    def download_bytes(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        """
        Download bytes data from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            
        Returns:
            Bytes data from S3
            
        Raises:
            S3DownloadError: If download fails
        """
        try:
            response = self.s3_client.get_object(
                Bucket=bucket_name,
                Key=object_key,
            )
            
            data = response["Body"].read()
            logger.info(
                f"Successfully downloaded bytes from s3://{bucket_name}/{object_key} "
                f"({len(data)} bytes)"
            )
            return data
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                logger.error(f"Object not found: s3://{bucket_name}/{object_key}")
                raise S3DownloadError(
                    f"Object not found: s3://{bucket_name}/{object_key}"
                ) from e
            else:
                logger.error(f"Failed to download bytes from S3: {e}")
                raise S3DownloadError(
                    f"Failed to download bytes from s3://{bucket_name}/{object_key}: {e}"
                ) from e
        except Exception as e:
            logger.error(f"Unexpected error during bytes download: {e}")
            raise S3DownloadError(f"Unexpected error during bytes download: {e}") from e
    
    def delete_object(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bool:
        """
        Delete an object from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            
        Returns:
            True if deletion successful
            
        Raises:
            S3ObjectError: If deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=bucket_name,
                Key=object_key,
            )
            
            logger.info(f"Successfully deleted s3://{bucket_name}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to delete object from S3: {e}")
            raise S3ObjectError(
                f"Failed to delete s3://{bucket_name}/{object_key}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during object deletion: {e}")
            raise S3ObjectError(f"Unexpected error during object deletion: {e}") from e
    
    def object_exists(
        self,
        bucket_name: str,
        object_key: str,
    ) -> bool:
        """
        Check if an object exists in S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: S3 object key (path)
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=bucket_name,
                Key=object_key,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return False
            else:
                logger.warning(f"Error checking object existence: {e}")
                return False
        except Exception as e:
            logger.warning(f"Unexpected error checking object existence: {e}")
            return False
    
    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
    ) -> list:
        """
        List objects in a bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            prefix: Optional prefix to filter objects
            
        Returns:
            List of object keys
            
        Raises:
            S3BucketError: If listing fails
        """
        try:
            kwargs = {"Bucket": bucket_name}
            if prefix:
                kwargs["Prefix"] = prefix
            
            response = self.s3_client.list_objects_v2(**kwargs)
            
            if "Contents" not in response:
                return []
            
            objects = [obj["Key"] for obj in response["Contents"]]
            logger.debug(f"Listed {len(objects)} objects from bucket {bucket_name}")
            return objects
            
        except ClientError as e:
            logger.error(f"Failed to list objects in bucket: {e}")
            raise S3BucketError(
                f"Failed to list objects in bucket {bucket_name}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error listing objects: {e}")
            raise S3BucketError(f"Unexpected error listing objects: {e}") from e
