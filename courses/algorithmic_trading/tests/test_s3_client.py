"""Tests for S3 client."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open
import io

import pytest
from botocore.exceptions import ClientError

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from aws.s3.s3_client import Boto3S3Client
from aws.s3.exceptions import (
    S3ConnectionError,
    S3UploadError,
    S3DownloadError,
    S3BucketError,
    S3ObjectError,
)


@pytest.fixture
def mock_boto3_client():
    """Fixture for mocked boto3 S3 client."""
    with patch("aws.s3.s3_client.boto3") as mock_boto3:
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        yield mock_client


@pytest.fixture
def s3_client(mock_boto3_client):
    """Fixture for S3Client with mocked boto3."""
    return Boto3S3Client(
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        region_name="us-east-1",
    )


def test_s3_client_initialization(mock_boto3_client):
    """Test S3 client initialization."""
    client = Boto3S3Client(
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        region_name="us-east-1",
    )
    
    assert client.aws_access_key_id == "test_key"
    assert client.aws_secret_access_key == "test_secret"
    assert client.region_name == "us-east-1"
    assert client._s3_client is not None


def test_s3_client_initialization_failure():
    """Test S3 client initialization failure."""
    with patch("aws.s3.s3_client.boto3") as mock_boto3:
        mock_boto3.client.side_effect = Exception("Connection failed")
        
        with pytest.raises(S3ConnectionError):
            Boto3S3Client()


def test_ensure_bucket_exists_existing(s3_client, mock_boto3_client):
    """Test ensuring bucket exists when it already exists."""
    mock_boto3_client.head_bucket.return_value = {}
    
    s3_client._ensure_bucket_exists("test-bucket")
    
    mock_boto3_client.head_bucket.assert_called_once_with(Bucket="test-bucket")
    mock_boto3_client.create_bucket.assert_not_called()


def test_ensure_bucket_exists_create(s3_client, mock_boto3_client):
    """Test creating bucket when it doesn't exist."""
    # Mock 404 error for head_bucket
    error_response = {"Error": {"Code": "404"}}
    mock_boto3_client.head_bucket.side_effect = ClientError(
        error_response, "HeadBucket"
    )
    
    s3_client._ensure_bucket_exists("test-bucket")
    
    mock_boto3_client.create_bucket.assert_called_once()


def test_ensure_bucket_exists_error(s3_client, mock_boto3_client):
    """Test error handling when bucket check fails."""
    error_response = {"Error": {"Code": "403"}}
    mock_boto3_client.head_bucket.side_effect = ClientError(
        error_response, "HeadBucket"
    )
    
    with pytest.raises(S3BucketError):
        s3_client._ensure_bucket_exists("test-bucket")


def test_upload_file_success(s3_client, mock_boto3_client, tmp_path):
    """Test successful file upload."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    mock_boto3_client.head_bucket.return_value = {}
    mock_boto3_client.upload_file.return_value = None
    
    result = s3_client.upload_file(
        bucket_name="test-bucket",
        object_key="test.txt",
        file_path=str(test_file),
    )
    
    assert result is True
    mock_boto3_client.upload_file.assert_called_once()


def test_upload_file_not_found(s3_client, mock_boto3_client):
    """Test file upload when file doesn't exist."""
    with pytest.raises(S3UploadError):
        s3_client.upload_file(
            bucket_name="test-bucket",
            object_key="test.txt",
            file_path="/nonexistent/file.txt",
        )


def test_upload_file_error(s3_client, mock_boto3_client, tmp_path):
    """Test file upload error handling."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    mock_boto3_client.head_bucket.return_value = {}
    error_response = {"Error": {"Code": "AccessDenied"}}
    mock_boto3_client.upload_file.side_effect = ClientError(
        error_response, "PutObject"
    )
    
    with pytest.raises(S3UploadError):
        s3_client.upload_file(
            bucket_name="test-bucket",
            object_key="test.txt",
            file_path=str(test_file),
        )


def test_download_file_success(s3_client, mock_boto3_client, tmp_path):
    """Test successful file download."""
    mock_boto3_client.download_file.return_value = None
    
    result = s3_client.download_file(
        bucket_name="test-bucket",
        object_key="test.txt",
        file_path=str(tmp_path / "downloaded.txt"),
    )
    
    assert result is True
    mock_boto3_client.download_file.assert_called_once()


def test_download_file_not_found(s3_client, mock_boto3_client, tmp_path):
    """Test file download when object doesn't exist."""
    error_response = {"Error": {"Code": "404"}}
    mock_boto3_client.download_file.side_effect = ClientError(
        error_response, "GetObject"
    )
    
    with pytest.raises(S3DownloadError):
        s3_client.download_file(
            bucket_name="test-bucket",
            object_key="nonexistent.txt",
            file_path=str(tmp_path / "downloaded.txt"),
        )


def test_upload_bytes_success(s3_client, mock_boto3_client):
    """Test successful bytes upload."""
    mock_boto3_client.head_bucket.return_value = {}
    mock_boto3_client.put_object.return_value = {}
    
    result = s3_client.upload_bytes(
        bucket_name="test-bucket",
        object_key="test.bin",
        data=b"test data",
    )
    
    assert result is True
    mock_boto3_client.put_object.assert_called_once()


def test_download_bytes_success(s3_client, mock_boto3_client):
    """Test successful bytes download."""
    mock_response = {"Body": io.BytesIO(b"test data")}
    mock_boto3_client.get_object.return_value = mock_response
    
    result = s3_client.download_bytes(
        bucket_name="test-bucket",
        object_key="test.bin",
    )
    
    assert result == b"test data"
    mock_boto3_client.get_object.assert_called_once()


def test_download_bytes_not_found(s3_client, mock_boto3_client):
    """Test bytes download when object doesn't exist."""
    error_response = {"Error": {"Code": "404"}}
    mock_boto3_client.get_object.side_effect = ClientError(
        error_response, "GetObject"
    )
    
    with pytest.raises(S3DownloadError):
        s3_client.download_bytes(
            bucket_name="test-bucket",
            object_key="nonexistent.bin",
        )


def test_delete_object_success(s3_client, mock_boto3_client):
    """Test successful object deletion."""
    mock_boto3_client.delete_object.return_value = {}
    
    result = s3_client.delete_object(
        bucket_name="test-bucket",
        object_key="test.txt",
    )
    
    assert result is True
    mock_boto3_client.delete_object.assert_called_once()


def test_delete_object_error(s3_client, mock_boto3_client):
    """Test object deletion error handling."""
    error_response = {"Error": {"Code": "AccessDenied"}}
    mock_boto3_client.delete_object.side_effect = ClientError(
        error_response, "DeleteObject"
    )
    
    with pytest.raises(S3ObjectError):
        s3_client.delete_object(
            bucket_name="test-bucket",
            object_key="test.txt",
        )


def test_object_exists_true(s3_client, mock_boto3_client):
    """Test object exists check when object exists."""
    mock_boto3_client.head_object.return_value = {}
    
    result = s3_client.object_exists(
        bucket_name="test-bucket",
        object_key="test.txt",
    )
    
    assert result is True


def test_object_exists_false(s3_client, mock_boto3_client):
    """Test object exists check when object doesn't exist."""
    error_response = {"Error": {"Code": "404"}}
    mock_boto3_client.head_object.side_effect = ClientError(
        error_response, "HeadObject"
    )
    
    result = s3_client.object_exists(
        bucket_name="test-bucket",
        object_key="nonexistent.txt",
    )
    
    assert result is False


def test_list_objects_success(s3_client, mock_boto3_client):
    """Test successful object listing."""
    mock_response = {
        "Contents": [
            {"Key": "file1.txt"},
            {"Key": "file2.txt"},
        ]
    }
    mock_boto3_client.list_objects_v2.return_value = mock_response
    
    result = s3_client.list_objects(
        bucket_name="test-bucket",
        prefix="test/",
    )
    
    assert len(result) == 2
    assert "file1.txt" in result
    assert "file2.txt" in result


def test_list_objects_empty(s3_client, mock_boto3_client):
    """Test object listing when bucket is empty."""
    mock_response = {}
    mock_boto3_client.list_objects_v2.return_value = mock_response
    
    result = s3_client.list_objects(
        bucket_name="test-bucket",
    )
    
    assert result == []


def test_list_objects_error(s3_client, mock_boto3_client):
    """Test object listing error handling."""
    error_response = {"Error": {"Code": "AccessDenied"}}
    mock_boto3_client.list_objects_v2.side_effect = ClientError(
        error_response, "ListObjects"
    )
    
    with pytest.raises(S3BucketError):
        s3_client.list_objects(
            bucket_name="test-bucket",
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
