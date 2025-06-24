"""
SMS Service Module for LetsGoal Application

This module provides SMS functionality using AWS SNS (Simple Notification Service).
It handles sending SMS messages, phone number validation, verification codes,
and compliance with SMS best practices.
"""

import os
import re
import random
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple

import boto3
import phonenumbers
from phonenumbers import NumberParseException
from botocore.exceptions import ClientError, BotoCoreError

from models import db, User, SmsDeliveryLog

# Configure logging
logger = logging.getLogger(__name__)

class SmsService:
    """
    SMS Service class for handling SMS operations with AWS SNS
    """
    
    def __init__(self):
        """Initialize the SMS service with AWS SNS client"""
        self.sns_client = None
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.sender_id = os.getenv('SMS_SENDER_ID', 'LetsGoal')
        self.cost_per_sms = Decimal('0.00645')  # AWS SNS cost per SMS in USD
        
        # Initialize AWS SNS client
        self._initialize_sns_client()
    
    def _initialize_sns_client(self):
        """Initialize the AWS SNS client with credentials"""
        try:
            # AWS credentials can be provided via:
            # 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
            # 2. AWS credentials file
            # 3. IAM role (when running on EC2)
            self.sns_client = boto3.client(
                'sns',
                region_name=self.region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            logger.info(f"SMS Service initialized with AWS SNS in region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS SNS client: {str(e)}")
            self.sns_client = None
    
    def validate_phone_number(self, phone_number: str, country_code: str = 'US') -> Tuple[bool, str]:
        """
        Validate and format a phone number using phonenumbers library
        
        Args:
            phone_number: Raw phone number string
            country_code: ISO country code (default: US)
            
        Returns:
            Tuple of (is_valid, formatted_number)
        """
        try:
            # Parse the phone number
            parsed_number = phonenumbers.parse(phone_number, country_code)
            
            # Check if the number is valid
            if not phonenumbers.is_valid_number(parsed_number):
                return False, "Invalid phone number format"
            
            # Format in E164 format for SMS
            formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            
            return True, formatted_number
        
        except NumberParseException as e:
            logger.warning(f"Phone number parsing error: {str(e)}")
            return False, f"Phone number parsing error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error validating phone number: {str(e)}")
            return False, "Phone number validation failed"
    
    def generate_verification_code(self) -> str:
        """Generate a 6-digit verification code"""
        return f"{random.randint(100000, 999999)}"
    
    def send_sms(self, 
                 phone_number: str, 
                 message: str, 
                 user_id: int,
                 message_type: str = 'notification',
                 metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Send an SMS message using AWS SNS
        
        Args:
            phone_number: E164 formatted phone number
            message: SMS message content (max 160 chars recommended)
            user_id: ID of the user receiving the SMS
            message_type: Type of message ('verification', 'reminder', 'notification')
            metadata: Additional metadata to store with the message
            
        Returns:
            Tuple of (success, message_id_or_error)
        """
        if not self.sns_client:
            error_msg = "SMS service not initialized. Check AWS credentials."
            logger.error(error_msg)
            self._log_sms_delivery(
                user_id=user_id,
                phone_number=phone_number,
                message_content=message,
                message_type=message_type,
                status='failed',
                error_message=error_msg,
                metadata=metadata
            )
            return False, error_msg
        
        try:
            # Validate phone number format
            is_valid, formatted_number = self.validate_phone_number(phone_number)
            if not is_valid:
                error_msg = f"Invalid phone number: {formatted_number}"
                logger.warning(error_msg)
                self._log_sms_delivery(
                    user_id=user_id,
                    phone_number=phone_number,
                    message_content=message,
                    message_type=message_type,
                    status='failed',
                    error_message=error_msg,
                    metadata=metadata
                )
                return False, error_msg
            
            # Truncate message if too long (SMS limit is 160 chars)
            if len(message) > 160:
                message = message[:157] + "..."
                logger.warning(f"Message truncated to 160 characters for user {user_id}")
            
            # Send SMS via AWS SNS
            response = self.sns_client.publish(
                PhoneNumber=formatted_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': self.sender_id
                    },
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': 'Transactional'  # For non-promotional messages
                    }
                }
            )
            
            message_id = response.get('MessageId', '')
            
            # Log successful delivery
            self._log_sms_delivery(
                user_id=user_id,
                phone_number=formatted_number,
                message_content=message,
                message_type=message_type,
                aws_message_id=message_id,
                status='sent',
                cost_usd=self.cost_per_sms,
                metadata=metadata
            )
            
            logger.info(f"SMS sent successfully to {formatted_number} (User: {user_id}, MessageID: {message_id})")
            return True, message_id
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"AWS SNS ClientError: {error_code} - {error_msg}")
            
            self._log_sms_delivery(
                user_id=user_id,
                phone_number=phone_number,
                message_content=message,
                message_type=message_type,
                status='failed',
                error_message=f"AWS Error: {error_code} - {error_msg}",
                metadata=metadata
            )
            return False, f"AWS Error: {error_msg}"
        
        except BotoCoreError as e:
            error_msg = f"AWS connection error: {str(e)}"
            logger.error(error_msg)
            
            self._log_sms_delivery(
                user_id=user_id,
                phone_number=phone_number,
                message_content=message,
                message_type=message_type,
                status='failed',
                error_message=error_msg,
                metadata=metadata
            )
            return False, error_msg
        
        except Exception as e:
            error_msg = f"Unexpected error sending SMS: {str(e)}"
            logger.error(error_msg)
            
            self._log_sms_delivery(
                user_id=user_id,
                phone_number=phone_number,
                message_content=message,
                message_type=message_type,
                status='failed',
                error_message=error_msg,
                metadata=metadata
            )
            return False, error_msg
    
    def send_verification_sms(self, user_id: int, phone_number: str) -> Tuple[bool, str]:
        """
        Send a verification code via SMS to verify phone number ownership
        
        Args:
            user_id: ID of the user
            phone_number: Phone number to verify
            
        Returns:
            Tuple of (success, verification_code_or_error)
        """
        # Generate verification code
        verification_code = self.generate_verification_code()
        
        # Create verification message
        message = f"Your LetsGoal verification code is: {verification_code}. This code expires in 10 minutes."
        
        # Send SMS
        success, result = self.send_sms(
            phone_number=phone_number,
            message=message,
            user_id=user_id,
            message_type='verification',
            metadata={'verification_code': verification_code}
        )
        
        if success:
            # Update user with verification code and expiration
            try:
                user = User.query.get(user_id)
                if user:
                    user.verification_code = verification_code
                    user.verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
                    db.session.commit()
                    logger.info(f"Verification code set for user {user_id}")
                
                return True, verification_code
            except Exception as e:
                logger.error(f"Failed to update user verification code: {str(e)}")
                return False, "Failed to store verification code"
        
        return False, result
    
    def verify_phone_number(self, user_id: int, verification_code: str) -> Tuple[bool, str]:
        """
        Verify a phone number using the provided verification code
        
        Args:
            user_id: ID of the user
            verification_code: Code provided by the user
            
        Returns:
            Tuple of (success, message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Check if verification code exists
            if not user.verification_code:
                return False, "No verification code found. Please request a new code."
            
            # Check if code has expired
            if user.verification_expires_at and user.verification_expires_at < datetime.utcnow():
                # Clear expired code
                user.verification_code = None
                user.verification_expires_at = None
                db.session.commit()
                return False, "Verification code has expired. Please request a new code."
            
            # Check if code matches
            if user.verification_code != verification_code:
                return False, "Invalid verification code"
            
            # Mark phone as verified
            user.phone_verified = True
            user.verification_code = None
            user.verification_expires_at = None
            db.session.commit()
            
            logger.info(f"Phone number verified successfully for user {user_id}")
            return True, "Phone number verified successfully"
        
        except Exception as e:
            logger.error(f"Error verifying phone number: {str(e)}")
            return False, "Verification failed due to system error"
    
    def _log_sms_delivery(self, 
                         user_id: int,
                         phone_number: str,
                         message_content: str,
                         message_type: str,
                         aws_message_id: Optional[str] = None,
                         status: str = 'sent',
                         cost_usd: Optional[Decimal] = None,
                         error_message: Optional[str] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """
        Log SMS delivery information to the database
        
        Args:
            user_id: ID of the user
            phone_number: Phone number the SMS was sent to
            message_content: Content of the SMS
            message_type: Type of message
            aws_message_id: AWS SNS message ID
            status: Delivery status
            cost_usd: Cost in USD
            error_message: Error message if delivery failed
            metadata: Additional metadata
        """
        try:
            log_entry = SmsDeliveryLog(
                user_id=user_id,
                phone_number=phone_number,
                message_content=message_content,
                message_type=message_type,
                aws_message_id=aws_message_id,
                status=status,
                cost_usd=cost_usd,
                error_message=error_message
            )
            
            if metadata:
                log_entry.set_metadata(metadata)
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log SMS delivery: {str(e)}")
            # Don't raise exception here to avoid breaking SMS sending
    
    def get_user_sms_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get SMS statistics for a user
        
        Args:
            user_id: ID of the user
            days: Number of days to look back
            
        Returns:
            Dictionary with SMS statistics
        """
        try:
            from_date = datetime.utcnow() - timedelta(days=days)
            
            logs = SmsDeliveryLog.query.filter(
                SmsDeliveryLog.user_id == user_id,
                SmsDeliveryLog.sent_at >= from_date
            ).all()
            
            total_sent = len(logs)
            total_cost = sum(log.cost_usd for log in logs if log.cost_usd)
            
            # Count by status
            status_counts = {}
            for log in logs:
                status_counts[log.status] = status_counts.get(log.status, 0) + 1
            
            # Count by message type
            type_counts = {}
            for log in logs:
                type_counts[log.message_type] = type_counts.get(log.message_type, 0) + 1
            
            return {
                'total_sent': total_sent,
                'total_cost_usd': float(total_cost) if total_cost else 0.0,
                'status_breakdown': status_counts,
                'type_breakdown': type_counts,
                'period_days': days
            }
        
        except Exception as e:
            logger.error(f"Error getting SMS stats for user {user_id}: {str(e)}")
            return {
                'total_sent': 0,
                'total_cost_usd': 0.0,
                'status_breakdown': {},
                'type_breakdown': {},
                'period_days': days,
                'error': str(e)
            }
    
    def check_opt_out(self, phone_number: str, message_content: str) -> bool:
        """
        Check if the incoming message is an opt-out request (STOP, UNSUBSCRIBE, etc.)
        
        Args:
            phone_number: Phone number that sent the message
            message_content: Content of the received message
            
        Returns:
            True if it's an opt-out request
        """
        opt_out_keywords = ['STOP', 'UNSUBSCRIBE', 'QUIT', 'CANCEL', 'END', 'OPTOUT']
        message_upper = message_content.strip().upper()
        
        # Check for exact matches or partial matches
        for keyword in opt_out_keywords:
            if keyword in message_upper:
                return True
        
        return False
    
    def handle_opt_out(self, phone_number: str) -> bool:
        """
        Handle opt-out request by disabling SMS for the user
        
        Args:
            phone_number: Phone number requesting opt-out
            
        Returns:
            True if opt-out was processed successfully
        """
        try:
            # Find user by phone number
            user = User.query.filter_by(phone_number=phone_number).first()
            if not user:
                logger.warning(f"Opt-out request from unknown phone number: {phone_number}")
                return False
            
            # Disable SMS for this user
            user.sms_enabled = False
            db.session.commit()
            
            logger.info(f"User {user.id} opted out of SMS notifications")
            
            # Send confirmation message
            confirmation_message = "You have been unsubscribed from LetsGoal SMS notifications. Reply START to resubscribe."
            self.send_sms(
                phone_number=phone_number,
                message=confirmation_message,
                user_id=user.id,
                message_type='notification',
                metadata={'type': 'opt_out_confirmation'}
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error handling opt-out for {phone_number}: {str(e)}")
            return False

# Global SMS service instance
sms_service = SmsService()