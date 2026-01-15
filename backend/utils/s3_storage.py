"""S3 storage utilities for file uploads."""

import os
import boto3
import uuid
import logging
from typing import Optional
from pathlib import Path
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class S3Storage:
    """Handle S3 file operations for uploaded documents."""
    
    def __init__(self):
        self.bucket_name = "fundonboarding"
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize S3 client with credentials from environment
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=self.region
        )
        
        # Validate credentials on initialization
        self._validate_connection()
    
    def _validate_connection(self):
        """Validate S3 connection and bucket access."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✅ S3 connection validated for bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"❌ S3 bucket '{self.bucket_name}' not found")
            elif error_code == '403':
                logger.error(f"❌ Access denied to S3 bucket '{self.bucket_name}'")
            else:
                logger.error(f"❌ S3 connection error: {error_code}")
            raise e
    
    async def upload_file(self, file_content: bytes, filename: str, content_type: str = None) -> str:
        """
        Upload file to S3 and return the S3 URL.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            # Generate unique filename
            file_extension = Path(filename).suffix
            unique_filename = f"{uuid.uuid4()}_{filename}"
            s3_key = f"uploads/{unique_filename}"
            
            # Determine content type if not provided
            if not content_type:
                if file_extension.lower() == '.pdf':
                    content_type = 'application/pdf'
                elif file_extension.lower() in ['.csv']:
                    content_type = 'text/csv'
                elif file_extension.lower() in ['.xlsx', '.xls']:
                    content_type = 'application/vnd.ms-excel'
                else:
                    content_type = 'application/octet-stream'
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                ServerSideEncryption='AES256'  # Encrypt at rest
            )
            
            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ File uploaded to S3: {filename} -> {s3_url}")
            return s3_url
            
        except ClientError as e:
            logger.error(f"❌ Failed to upload {filename} to S3: {str(e)}")
            raise e
    
    async def download_file(self, s3_url: str, local_path: str) -> str:
        """
        Download file from S3 to local path for processing.
        
        Args:
            s3_url: S3 URL of the file
            local_path: Local path to save the file
            
        Returns:
            Local file path
        """
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[1]
            
            # Create local directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download from S3
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            
            logger.info(f"✅ File downloaded from S3: {s3_url} -> {local_path}")
            return local_path
            
        except ClientError as e:
            logger.error(f"❌ Failed to download from S3: {s3_url} - {str(e)}")
            raise e
    
    async def delete_file(self, s3_url: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            s3_url: S3 URL of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[1]
            
            # Delete from S3
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            
            logger.info(f"✅ File deleted from S3: {s3_url}")
            return True
            
        except ClientError as e:
            logger.error(f"❌ Failed to delete from S3: {s3_url} - {str(e)}")
            return False
    
    def get_file_info(self, s3_url: str) -> dict:
        """
        Get file metadata from S3.
        
        Args:
            s3_url: S3 URL of the file
            
        Returns:
            Dictionary with file metadata
        """
        try:
            # Extract S3 key from URL
            s3_key = s3_url.split(f"{self.bucket_name}.s3.{self.region}.amazonaws.com/")[1]
            
            # Get object metadata
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            return {
                "size": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", "unknown"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag", "").strip('"'),
                "s3_key": s3_key
            }
            
        except ClientError as e:
            logger.error(f"❌ Failed to get file info from S3: {s3_url} - {str(e)}")
            return {}


# Global S3 storage instance
s3_storage = None

def get_s3_storage() -> Optional[S3Storage]:
    """Get or create S3 storage instance."""
    global s3_storage
    
    # Check if AWS credentials are available
    if not all([
        os.getenv("AWS_ACCESS_KEY_ID"),
        os.getenv("AWS_SECRET_ACCESS_KEY")
    ]):
        logger.warning("⚠️ AWS credentials not found. S3 storage disabled.")
        return None
    
    if s3_storage is None:
        try:
            s3_storage = S3Storage()
        except Exception as e:
            logger.error(f"❌ Failed to initialize S3 storage: {str(e)}")
            return None
    
    return s3_storage