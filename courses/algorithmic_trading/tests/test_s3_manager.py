"""Tests for S3 manager."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import io

import pytest
import pandas as pd

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from aws.s3.s3_manager import S3Manager
from aws.s3.s3_client import S3Client
from aws.s3.exceptions import S3UploadError, S3DownloadError


@pytest.fixture
def mock_s3_client():
    """Fixture for mocked S3Client."""
    return MagicMock(spec=S3Client)


@pytest.fixture
def s3_manager(mock_s3_client):
    """Fixture for S3Manager with mocked client."""
    return S3Manager(
        bucket_name="test-bucket",
        s3_client=mock_s3_client,
        default_prefix="data/",
    )


def test_s3_manager_initialization(mock_s3_client):
    """Test S3Manager initialization."""
    manager = S3Manager(
        bucket_name="test-bucket",
        s3_client=mock_s3_client,
    )
    
    assert manager.bucket_name == "test-bucket"
    assert manager.s3_client == mock_s3_client
    assert manager.default_prefix == ""


def test_build_key_with_prefix(s3_manager):
    """Test building object key with prefix."""
    key = s3_manager._build_key("file.txt")
    assert key == "data/file.txt"
    
    key = s3_manager._build_key("/file.txt")
    assert key == "data/file.txt"


def test_build_key_without_prefix():
    """Test building object key without prefix."""
    manager = S3Manager(bucket_name="test-bucket")
    key = manager._build_key("file.txt")
    assert key == "file.txt"


def test_upload_file(s3_manager, mock_s3_client, tmp_path):
    """Test file upload."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    
    mock_s3_client.upload_file.return_value = True
    
    result = s3_manager.upload_file(
        object_key="test.txt",
        file_path=str(test_file),
    )
    
    assert result is True
    mock_s3_client.upload_file.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/test.txt",
        file_path=str(test_file),
        metadata=None,
    )


def test_download_file(s3_manager, mock_s3_client, tmp_path):
    """Test file download."""
    mock_s3_client.download_file.return_value = True
    
    result = s3_manager.download_file(
        object_key="test.txt",
        file_path=str(tmp_path / "downloaded.txt"),
    )
    
    assert result is True
    mock_s3_client.download_file.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/test.txt",
        file_path=str(tmp_path / "downloaded.txt"),
    )


@pytest.mark.skipif(
    not hasattr(pd.DataFrame(), 'to_parquet') or 
    not hasattr(pd, 'read_parquet'),
    reason="Parquet support requires pyarrow or fastparquet"
)
def test_upload_dataframe_parquet(s3_manager, mock_s3_client):
    """Test DataFrame upload as Parquet."""
    try:
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        # Test if parquet is available
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=True)
    except (ImportError, ValueError):
        pytest.skip("Parquet engine not available")
    
    mock_s3_client.upload_bytes.return_value = True
    
    result = s3_manager.upload_dataframe(
        object_key="data.parquet",
        dataframe=df,
        format="parquet",
    )
    
    assert result is True
    mock_s3_client.upload_bytes.assert_called_once()
    call_kwargs = mock_s3_client.upload_bytes.call_args[1]
    assert call_kwargs["bucket_name"] == "test-bucket"
    assert call_kwargs["object_key"] == "data/data.parquet"
    assert "dataframe_format" in call_kwargs["metadata"]


def test_upload_dataframe_csv(s3_manager, mock_s3_client):
    """Test DataFrame upload as CSV."""
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
    mock_s3_client.upload_bytes.return_value = True
    
    result = s3_manager.upload_dataframe(
        object_key="data.csv",
        dataframe=df,
        format="csv",
    )
    
    assert result is True
    mock_s3_client.upload_bytes.assert_called_once()


def test_upload_dataframe_unsupported_format(s3_manager, mock_s3_client):
    """Test DataFrame upload with unsupported format."""
    from aws.s3.exceptions import S3UploadError
    
    df = pd.DataFrame({"col1": [1, 2, 3]})
    
    with pytest.raises(S3UploadError):
        s3_manager.upload_dataframe(
            object_key="data.xyz",
            dataframe=df,
            format="xyz",
        )


@pytest.mark.skipif(
    not hasattr(pd.DataFrame(), 'to_parquet') or 
    not hasattr(pd, 'read_parquet'),
    reason="Parquet support requires pyarrow or fastparquet"
)
def test_download_dataframe_parquet(s3_manager, mock_s3_client):
    """Test DataFrame download as Parquet."""
    try:
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=True)
        buffer.seek(0)
        parquet_data = buffer.read()
    except (ImportError, ValueError):
        pytest.skip("Parquet engine not available")
    
    mock_s3_client.download_bytes.return_value = parquet_data
    
    result = s3_manager.download_dataframe(
        object_key="data.parquet",
        format="parquet",
    )
    
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3
    mock_s3_client.download_bytes.assert_called_once()


def test_download_dataframe_csv(s3_manager, mock_s3_client):
    """Test DataFrame download as CSV."""
    df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
    buffer = io.BytesIO()
    df.to_csv(buffer, index=True)
    buffer.seek(0)
    
    mock_s3_client.download_bytes.return_value = buffer.read()
    
    result = s3_manager.download_dataframe(
        object_key="data.csv",
        format="csv",
    )
    
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 3


@pytest.mark.skipif(
    not hasattr(pd.DataFrame(), 'to_parquet') or 
    not hasattr(pd, 'read_parquet'),
    reason="Parquet support requires pyarrow or fastparquet"
)
def test_download_dataframe_infer_format(s3_manager, mock_s3_client):
    """Test DataFrame download with format inference."""
    try:
        df = pd.DataFrame({"col1": [1, 2, 3]})
        buffer = io.BytesIO()
        df.to_parquet(buffer, index=True)
        buffer.seek(0)
        parquet_data = buffer.read()
    except (ImportError, ValueError):
        pytest.skip("Parquet engine not available")
    
    mock_s3_client.download_bytes.return_value = parquet_data
    
    result = s3_manager.download_dataframe(
        object_key="data.parquet",
    )
    
    assert isinstance(result, pd.DataFrame)


def test_download_dataframe_no_format(s3_manager, mock_s3_client):
    """Test DataFrame download without format."""
    from aws.s3.exceptions import S3DownloadError
    
    mock_s3_client.download_bytes.return_value = b"dummy data"
    
    with pytest.raises(S3DownloadError):
        s3_manager.download_dataframe(
            object_key="data.unknown",
        )


def test_upload_bytes(s3_manager, mock_s3_client):
    """Test bytes upload."""
    mock_s3_client.upload_bytes.return_value = True
    
    result = s3_manager.upload_bytes(
        object_key="data.bin",
        data=b"test data",
    )
    
    assert result is True
    mock_s3_client.upload_bytes.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/data.bin",
        data=b"test data",
        metadata=None,
    )


def test_download_bytes(s3_manager, mock_s3_client):
    """Test bytes download."""
    mock_s3_client.download_bytes.return_value = b"test data"
    
    result = s3_manager.download_bytes(
        object_key="data.bin",
    )
    
    assert result == b"test data"
    mock_s3_client.download_bytes.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/data.bin",
    )


def test_delete_object(s3_manager, mock_s3_client):
    """Test object deletion."""
    mock_s3_client.delete_object.return_value = True
    
    result = s3_manager.delete_object(
        object_key="test.txt",
    )
    
    assert result is True
    mock_s3_client.delete_object.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/test.txt",
    )


def test_object_exists(s3_manager, mock_s3_client):
    """Test object existence check."""
    mock_s3_client.object_exists.return_value = True
    
    result = s3_manager.object_exists(
        object_key="test.txt",
    )
    
    assert result is True
    mock_s3_client.object_exists.assert_called_once_with(
        bucket_name="test-bucket",
        object_key="data/test.txt",
    )


def test_list_objects(s3_manager, mock_s3_client):
    """Test object listing."""
    mock_s3_client.list_objects.return_value = ["file1.txt", "file2.txt"]
    
    result = s3_manager.list_objects(
        prefix="test/",
    )
    
    assert len(result) == 2
    mock_s3_client.list_objects.assert_called_once_with(
        bucket_name="test-bucket",
        prefix="data/test/",
    )


def test_upload_directory(s3_manager, mock_s3_client, tmp_path):
    """Test directory upload."""
    # Create test directory structure
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    (test_dir / "file1.txt").write_text("content1")
    (test_dir / "file2.txt").write_text("content2")
    (test_dir / "subdir").mkdir()
    (test_dir / "subdir" / "file3.txt").write_text("content3")
    
    mock_s3_client.upload_file.return_value = True
    
    result = s3_manager.upload_directory(
        directory_path=str(test_dir),
        s3_prefix="uploads",
    )
    
    assert len(result) == 3
    assert mock_s3_client.upload_file.call_count == 3


def test_upload_directory_not_directory(s3_manager, tmp_path):
    """Test directory upload with invalid path."""
    test_file = tmp_path / "not_a_dir.txt"
    test_file.write_text("content")
    
    with pytest.raises(ValueError):
        s3_manager.upload_directory(
            directory_path=str(test_file),
        )


def test_custom_bucket_name(s3_manager, mock_s3_client, tmp_path):
    """Test operations with custom bucket name."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    
    mock_s3_client.upload_file.return_value = True
    
    s3_manager.upload_file(
        object_key="test.txt",
        file_path=str(test_file),
        bucket_name="custom-bucket",
    )
    
    call_args = mock_s3_client.upload_file.call_args[1]
    assert call_args["bucket_name"] == "custom-bucket"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
