# AWS S3 Integration

Production-ready AWS S3 integration for uploading and retrieving data to/from Amazon S3.

## Features

- **Object-Oriented Design**: Clean, modular architecture following SOLID principles
- **Abstract Base Classes**: Extensible design with abstract S3Client interface
- **Boto3 Implementation**: Production-ready Boto3-based S3 client
- **DataFrame Support**: Built-in support for pandas DataFrame upload/download
- **Error Handling**: Comprehensive exception handling with custom exceptions
- **Logging**: Integrated logging for all operations
- **Configuration**: Environment-based configuration management
- **Testing**: Full test suite with pytest

## Installation

The AWS S3 integration requires `boto3` which is included in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Configuration

Configure AWS credentials via environment variables:

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
export AWS_DEFAULT_BUCKET=your-bucket-name
export AWS_ENDPOINT_URL=https://s3.amazonaws.com  # Optional, for S3-compatible services
```

Or use AWS credentials file (`~/.aws/credentials`) or IAM roles (for EC2/ECS).

## Usage

### Basic File Operations

```python
from aws.s3.s3_manager import S3Manager

# Initialize S3 manager
s3_manager = S3Manager(
    bucket_name="my-trading-data",
    default_prefix="historical_data/",
)

# Upload a file
s3_manager.upload_file(
    object_key="AAPL_data.csv",
    file_path="/local/path/to/AAPL_data.csv",
    metadata={"source": "IB_API", "symbol": "AAPL"},
)

# Download a file
s3_manager.download_file(
    object_key="AAPL_data.csv",
    file_path="/local/path/to/downloaded_AAPL_data.csv",
)

# Check if object exists
if s3_manager.object_exists("AAPL_data.csv"):
    print("File exists in S3")

# Delete an object
s3_manager.delete_object("AAPL_data.csv")

# List objects
objects = s3_manager.list_objects(prefix="historical_data/")
for obj_key in objects:
    print(f"Found: {obj_key}")
```

### DataFrame Operations

```python
import pandas as pd
from aws.s3.s3_manager import S3Manager

s3_manager = S3Manager(bucket_name="my-trading-data")

# Create sample DataFrame
df = pd.DataFrame({
    "date": pd.date_range("2024-01-01", periods=100),
    "open": [100 + i for i in range(100)],
    "high": [101 + i for i in range(100)],
    "low": [99 + i for i in range(100)],
    "close": [100.5 + i for i in range(100)],
    "volume": [1000000] * 100,
})

# Upload DataFrame as Parquet (recommended for large datasets)
s3_manager.upload_dataframe(
    object_key="AAPL_2024.parquet",
    dataframe=df,
    format="parquet",
)

# Upload DataFrame as CSV
s3_manager.upload_dataframe(
    object_key="AAPL_2024.csv",
    dataframe=df,
    format="csv",
)

# Download DataFrame
df_downloaded = s3_manager.download_dataframe(
    object_key="AAPL_2024.parquet",
    format="parquet",
)

# Format is auto-inferred from file extension
df_downloaded = s3_manager.download_dataframe(
    object_key="AAPL_2024.parquet",
)
```

### Bytes Operations

```python
from aws.s3.s3_manager import S3Manager

s3_manager = S3Manager(bucket_name="my-trading-data")

# Upload bytes
data = b"Binary data content"
s3_manager.upload_bytes(
    object_key="data.bin",
    data=data,
    metadata={"content_type": "application/octet-stream"},
)

# Download bytes
downloaded_data = s3_manager.download_bytes("data.bin")
```

### Directory Upload

```python
from aws.s3.s3_manager import S3Manager

s3_manager = S3Manager(bucket_name="my-trading-data")

# Upload entire directory
uploaded_keys = s3_manager.upload_directory(
    directory_path="/local/path/to/data",
    s3_prefix="backup/2024-01-01",
)

print(f"Uploaded {len(uploaded_keys)} files")
```

### Custom S3 Client

```python
from aws.s3.s3_client import Boto3S3Client
from aws.s3.s3_manager import S3Manager

# Create custom S3 client with specific credentials
s3_client = Boto3S3Client(
    aws_access_key_id="custom_key",
    aws_secret_access_key="custom_secret",
    region_name="us-west-2",
    endpoint_url="https://s3.us-west-2.amazonaws.com",  # Optional
)

# Use custom client with manager
s3_manager = S3Manager(
    bucket_name="my-bucket",
    s3_client=s3_client,
)
```

### Integration with Trading App

```python
from aws.s3.s3_manager import S3Manager
from storage.dataframe_manager import DataFrameManager
from handlers.historical_data_handler import HistoricalDataHandler

# Get historical data
data_handler = HistoricalDataHandler()
# ... fetch data using TradingApp ...

# Convert to DataFrames
df_manager = DataFrameManager(data_handler)
dataframes = df_manager.create_dataframes(tickers=["AAPL", "TSLA"])

# Upload to S3
s3_manager = S3Manager(
    bucket_name="trading-historical-data",
    default_prefix="daily_data/",
)

for ticker, df in dataframes.items():
    s3_manager.upload_dataframe(
        object_key=f"{ticker}_historical.parquet",
        dataframe=df,
        format="parquet",
        metadata={"ticker": ticker, "source": "IB_API"},
    )
```

## Architecture

### Class Hierarchy

```
S3Client (ABC)
    └── Boto3S3Client (Implementation)

S3Manager (High-level interface)
    └── Uses S3Client for operations
```

### Key Classes

- **S3Client**: Abstract base class defining S3 operations interface
- **Boto3S3Client**: Boto3-based implementation of S3Client
- **S3Manager**: High-level manager with convenience methods for common operations
- **S3Error**: Base exception for all S3-related errors
- **S3ConnectionError**: Raised when connection to S3 fails
- **S3UploadError**: Raised when upload operations fail
- **S3DownloadError**: Raised when download operations fail
- **S3BucketError**: Raised when bucket operations fail
- **S3ObjectError**: Raised when object operations fail

## Error Handling

All S3 operations raise custom exceptions that inherit from `S3Error`:

```python
from aws.s3.exceptions import (
    S3Error,
    S3UploadError,
    S3DownloadError,
    S3BucketError,
)

try:
    s3_manager.upload_file("file.txt", "/local/path")
except S3UploadError as e:
    print(f"Upload failed: {e}")
except S3BucketError as e:
    print(f"Bucket error: {e}")
except S3Error as e:
    print(f"S3 error: {e}")
```

## Testing

Run the test suite:

```bash
# Run all S3 tests
pytest tests/test_s3_client.py tests/test_s3_manager.py -v

# Run with coverage
pytest --cov=aws tests/test_s3_client.py tests/test_s3_manager.py
```

## Best Practices

1. **Use Parquet format** for large DataFrames (better compression and performance)
2. **Set appropriate metadata** when uploading files for better organization
3. **Use prefixes** to organize files in S3 buckets
4. **Handle exceptions** appropriately in production code
5. **Use IAM roles** instead of access keys when running on AWS infrastructure
6. **Enable versioning** on S3 buckets for critical data
7. **Use lifecycle policies** to manage data retention and costs

## Supported Formats

- **Parquet**: Recommended for large DataFrames (fast, compressed)
- **CSV**: Human-readable, good for small datasets
- **JSON**: Good for structured data exchange
- **Pickle**: Python-specific, preserves data types

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_ACCESS_KEY_ID` | AWS access key ID | None |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | None |
| `AWS_REGION` | AWS region name | `us-east-1` |
| `AWS_ENDPOINT_URL` | Custom S3 endpoint URL | None |
| `AWS_DEFAULT_BUCKET` | Default bucket name | None |

## License

This module is part of the Interactive Brokers Algorithmic Trading Framework.
