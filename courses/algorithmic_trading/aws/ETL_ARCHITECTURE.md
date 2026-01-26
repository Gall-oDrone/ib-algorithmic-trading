# ETL Pipeline Architecture Overview

## Executive Summary

This document outlines the recommended ETL (Extract, Transform, Load) architecture for the Interactive Brokers algorithmic trading data pipeline. The architecture is designed to be scalable, maintainable, and ready for migration to Amazon EKS (Elastic Kubernetes Service).

## Current Data Flow

```
Interactive Brokers API
    ↓
HistoricalDataHandler (Extract)
    ↓
DataFrameManager (Transform)
    ↓
Technical Indicators (Transform)
    ↓
S3Manager (Load)
    ↓
Amazon S3 (Data Lake)
```

## Recommended ETL Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EXTRACT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  IB API Connector (Container)                                   │
│  - Fetches historical OHLCV data                                 │
│  - Real-time market data streaming                              │
│  - Account/portfolio data                                        │
│  - Order execution data                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE QUEUE (SQS)                           │
│  - Decouples extract from transform                              │
│  - Handles backpressure                                         │
│  - Enables retry logic                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                      TRANSFORM LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Transform Workers (Kubernetes Jobs/Pods)                        │
│  - Data validation & cleaning                                   │
│  - Technical indicator calculations                              │
│  - Data enrichment                                               │
│  - Schema standardization                                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                        LOAD LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  S3 Data Lake (Parquet format)                                   │
│  - Raw data: s3://bucket/raw/{date}/{symbol}/                   │
│  - Processed: s3://bucket/processed/{date}/{symbol}/            │
│  - Indicators: s3://bucket/indicators/{date}/{symbol}/          │
│  - Metadata: s3://bucket/metadata/{date}/                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA CATALOG (AWS Glue)                       │
│  - Schema registry                                               │
│  - Data discovery                                                │
│  - Query optimization                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Recommended AWS Services

### Core Services

1. **Amazon S3** (Data Lake)
   - **Purpose**: Centralized data storage
   - **Format**: Parquet (columnar, compressed)
   - **Partitioning**: By date, symbol, data type
   - **Lifecycle Policies**: Move old data to Glacier/Deep Archive

2. **Amazon SQS** (Message Queue)
   - **Purpose**: Decouple extract and transform stages
   - **Type**: Standard Queue (high throughput) or FIFO (ordered processing)
   - **Dead Letter Queue**: Handle failed messages

3. **AWS Glue** (Data Catalog & ETL)
   - **Purpose**: Schema registry, data discovery, ETL jobs
   - **Crawlers**: Auto-discover S3 data schemas
   - **Jobs**: Serverless Spark-based transformations (optional)

4. **Amazon EKS** (Container Orchestration)
   - **Purpose**: Run ETL jobs as Kubernetes workloads
   - **Components**: Jobs, CronJobs, Deployments
   - **Auto-scaling**: Horizontal Pod Autoscaler (HPA)

5. **Amazon EventBridge** (Event-Driven Architecture)
   - **Purpose**: Trigger ETL jobs on schedules or events
   - **S3 Events**: Trigger on new file uploads
   - **Cron Jobs**: Scheduled data extraction

### Optional/Advanced Services

6. **Amazon Kinesis Data Streams** (Real-time Processing)
   - **Purpose**: Real-time market data streaming
   - **Use Case**: Live indicator calculations

7. **Amazon EMR** (Big Data Processing)
   - **Purpose**: Large-scale batch processing
   - **Use Case**: Historical backtesting, bulk indicator calculations

8. **Amazon RDS/Redshift** (Analytical Database)
   - **Purpose**: Query processed data
   - **Use Case**: Fast analytical queries, dashboards

9. **AWS Lambda** (Serverless Functions)
   - **Purpose**: Lightweight transformations, triggers
   - **Use Case**: S3 event handlers, API gateways

## ETL Pipeline Components

### 1. Extract Layer

**Component**: IB API Connector Service

**Responsibilities**:
- Connect to Interactive Brokers API
- Fetch historical data (OHLCV bars)
- Stream real-time market data
- Collect account/portfolio data
- Handle API rate limits and retries

**Implementation**:
- Containerized Python service
- Kubernetes Deployment with health checks
- Sends messages to SQS after data extraction
- Uploads raw data directly to S3

**S3 Structure**:
```
s3://trading-data-lake/
  raw/
    historical/
      {date}/
        {symbol}/
          bars_{timestamp}.parquet
    account/
      {date}/
        account_summary_{timestamp}.json
    orders/
      {date}/
        orders_{timestamp}.json
```

### 2. Transform Layer

**Component**: Transform Workers (Kubernetes Jobs)

**Responsibilities**:
- Read messages from SQS
- Download raw data from S3
- Validate and clean data
- Calculate technical indicators (MACD, ATR, Bollinger Bands)
- Enrich data with metadata
- Standardize schemas

**Implementation**:
- Kubernetes Job or CronJob
- Horizontal Pod Autoscaler based on SQS queue depth
- Parallel processing per symbol/timeframe
- Error handling with retry logic

**Processing Flow**:
```
SQS Message → Download from S3 → Validate → Transform → 
Calculate Indicators → Upload to S3 → Update Catalog → Delete Message
```

**S3 Structure**:
```
s3://trading-data-lake/
  processed/
    {date}/
      {symbol}/
        ohlcv_{timestamp}.parquet
  indicators/
    {date}/
      {symbol}/
        macd_{timestamp}.parquet
        atr_{timestamp}.parquet
        bollinger_{timestamp}.parquet
        combined_indicators_{timestamp}.parquet
```

### 3. Load Layer

**Component**: S3 Data Lake + AWS Glue Catalog

**Responsibilities**:
- Store processed data in optimized format (Parquet)
- Maintain data catalog for discovery
- Enable querying via Athena/Spark
- Manage data lifecycle

**Partitioning Strategy**:
- **Date Partitioning**: `/year=YYYY/month=MM/day=DD/`
- **Symbol Partitioning**: `/symbol={SYMBOL}/`
- **Data Type**: `/type={raw|processed|indicators}/`

**Example Path**:
```
s3://trading-data-lake/
  processed/
    year=2024/
      month=01/
        day=26/
          symbol=AAPL/
            ohlcv_20240126_143000.parquet
```

## Implementation Phases

### Phase 1: Foundation (Current → AWS Native)

**Goal**: Move from local processing to AWS-native architecture

1. **Enhance S3 Integration**
   - Implement partitioned uploads
   - Add data versioning
   - Set up lifecycle policies

2. **Add SQS Integration**
   - Create SQS queues for data pipeline
   - Modify extract layer to publish messages
   - Implement message handlers

3. **Containerize Components**
   - Create Docker images for:
     - IB API Connector
     - Transform Workers
     - Indicator Calculators
   - Test locally with Docker Compose

**Timeline**: 2-3 weeks

### Phase 2: Kubernetes Migration (EKS Ready)

**Goal**: Deploy to EKS with proper orchestration

1. **Kubernetes Manifests**
   - Deployments for long-running services
   - Jobs for batch processing
   - CronJobs for scheduled tasks
   - ConfigMaps and Secrets for configuration

2. **Auto-scaling**
   - Configure HPA based on SQS queue depth
   - Set resource limits and requests
   - Implement health checks

3. **Monitoring & Logging**
   - CloudWatch integration
   - Prometheus metrics
   - Centralized logging (CloudWatch Logs or ELK)

**Timeline**: 3-4 weeks

### Phase 3: Advanced Features

**Goal**: Add real-time processing and analytics

1. **Real-time Streaming**
   - Kinesis Data Streams for live data
   - Real-time indicator calculations
   - Stream processing with Kafka/Kinesis

2. **Data Catalog**
   - AWS Glue Crawlers for schema discovery
   - Athena for SQL queries
   - Data quality checks

3. **Advanced Analytics**
   - EMR for large-scale processing
   - ML model training pipeline
   - Backtesting infrastructure

**Timeline**: 4-6 weeks

## Data Formats & Standards

### Raw Data Format (Parquet)

```python
# Schema for OHLCV bars
{
    "date": "timestamp",
    "open": "double",
    "high": "double",
    "low": "double",
    "close": "double",
    "volume": "long",
    "symbol": "string",
    "bar_size": "string",  # e.g., "30 mins", "1 day"
    "source": "string",    # "IB_API"
    "extracted_at": "timestamp"
}
```

### Processed Data Format (Parquet)

```python
# Enhanced OHLCV with metadata
{
    "date": "timestamp",
    "open": "double",
    "high": "double",
    "low": "double",
    "close": "double",
    "volume": "long",
    "symbol": "string",
    "bar_size": "string",
    "source": "string",
    "extracted_at": "timestamp",
    "processed_at": "timestamp",
    "data_quality_score": "double",
    "is_valid": "boolean"
}
```

### Indicators Format (Parquet)

```python
# Technical indicators
{
    "date": "timestamp",
    "symbol": "string",
    "macd": "double",
    "macd_signal": "double",
    "macd_histogram": "double",
    "atr": "double",
    "bb_upper": "double",
    "bb_middle": "double",
    "bb_lower": "double",
    "bb_bandwidth": "double",
    "bb_percent_b": "double",
    "calculated_at": "timestamp"
}
```

## Error Handling & Resilience

### Retry Strategy

1. **Exponential Backoff**: For transient failures
2. **Dead Letter Queue**: For permanently failed messages
3. **Circuit Breaker**: For external API failures
4. **Idempotency**: Ensure safe retries

### Monitoring & Alerting

1. **CloudWatch Metrics**:
   - SQS queue depth
   - Processing latency
   - Error rates
   - S3 upload/download success rates

2. **Alerts**:
   - Queue depth > threshold
   - Processing failures > threshold
   - Data quality issues
   - API rate limit warnings

## Security Considerations

1. **IAM Roles**: Use IAM roles for EKS pods (IRSA - IAM Roles for Service Accounts)
2. **Secrets Management**: AWS Secrets Manager for API keys
3. **Encryption**: S3 server-side encryption (SSE-S3 or SSE-KMS)
4. **VPC**: Deploy EKS in private subnets
5. **Network Policies**: Kubernetes network policies for pod-to-pod communication

## Cost Optimization

1. **S3 Storage Classes**: 
   - Standard for hot data
   - Intelligent-Tiering for variable access
   - Glacier for archival

2. **EKS Node Groups**:
   - Spot instances for batch jobs
   - Reserved instances for long-running services
   - Auto-scaling to minimize idle resources

3. **Data Lifecycle**:
   - Delete raw data after processing (if not needed)
   - Archive old processed data to Glacier
   - Compress data (Parquet already compressed)

## Migration Checklist

### Pre-Migration

- [ ] Review and document current data flow
- [ ] Identify all data sources and destinations
- [ ] Create data mapping documentation
- [ ] Set up AWS account and IAM roles
- [ ] Create S3 buckets with proper policies
- [ ] Set up SQS queues

### Containerization

- [ ] Create Dockerfiles for each component
- [ ] Build and test Docker images locally
- [ ] Set up Docker registry (ECR)
- [ ] Test with Docker Compose

### EKS Setup

- [ ] Create EKS cluster
- [ ] Configure node groups
- [ ] Set up IRSA for IAM roles
- [ ] Install necessary add-ons (ALB Ingress, etc.)
- [ ] Configure networking (VPC, subnets, security groups)

### Deployment

- [ ] Create Kubernetes manifests
- [ ] Deploy to dev environment
- [ ] Test end-to-end pipeline
- [ ] Monitor and tune performance
- [ ] Deploy to production

### Post-Migration

- [ ] Validate data integrity
- [ ] Monitor costs
- [ ] Optimize performance
- [ ] Document runbooks
- [ ] Train team on new infrastructure

## Recommended Directory Structure

```
courses/algorithmic_trading/
├── aws/
│   ├── etl/
│   │   ├── extract/
│   │   │   ├── ib_connector.py
│   │   │   └── data_extractor.py
│   │   ├── transform/
│   │   │   ├── data_validator.py
│   │   │   ├── indicator_calculator.py
│   │   │   └── data_enricher.py
│   │   ├── load/
│   │   │   ├── s3_loader.py
│   │   │   └── catalog_updater.py
│   │   └── orchestrator.py
│   ├── k8s/
│   │   ├── deployments/
│   │   ├── jobs/
│   │   ├── cronjobs/
│   │   └── configmaps/
│   ├── docker/
│   │   ├── Dockerfile.extract
│   │   ├── Dockerfile.transform
│   │   └── docker-compose.yml
│   └── terraform/  # Infrastructure as Code (optional)
│       ├── s3.tf
│       ├── sqs.tf
│       ├── eks.tf
│       └── glue.tf
└── ...
```

## Next Steps

1. **Review this architecture** with your team
2. **Prioritize features** based on business needs
3. **Start with Phase 1** (Foundation)
4. **Set up development environment** with Docker
5. **Create proof of concept** for one data pipeline
6. **Iterate and improve** based on learnings

## References

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [S3 Data Lake Best Practices](https://aws.amazon.com/blogs/big-data/building-a-data-lake-on-aws/)
- [Kubernetes Jobs Documentation](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [AWS Glue Documentation](https://docs.aws.amazon.com/glue/)
- [Parquet Format Specification](https://parquet.apache.org/)

---

**Document Version**: 1.0  
**Last Updated**: January 26, 2025  
**Author**: ETL Architecture Review
