"""
Data Import Service for Seller Performance Data.
Implements FR-01: Input Seller Performance Data.

Supports:
- CSV file import
- Excel file import  
- JSON data import
- Data validation and error reporting
- Bulk operations with transaction safety
"""
import csv
import json
import pandas as pd
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Optional
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings

from apps.performance.models import Seller, Order, CustomerFeedback
from apps.audit_trail.models import AuditEvent

User = get_user_model()
logger = logging.getLogger(__name__)


class DataImportService:
    """
    Service for importing seller performance data from various formats.
    Provides comprehensive validation and error handling.
    """
    
    # Supported file formats
    SUPPORTED_FORMATS = ['.csv', '.xlsx', '.xls', '.json']
    
    # Maximum file size (5MB)
    MAX_FILE_SIZE = getattr(settings, 'MAX_IMPORT_FILE_SIZE', 5 * 1024 * 1024)
    
    def __init__(self):
        self.import_stats = {
            'total_records': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': []
        }
    
    def import_seller_data(self, file_path: str, file_format: str, 
                          user: User, import_type: str = 'orders') -> Dict:
        """
        Import seller performance data from file.
        
        Args:
            file_path: Path to the import file
            file_format: File format (.csv, .xlsx, .json)
            user: User performing the import
            import_type: Type of data ('orders', 'sellers', 'feedback')
            
        Returns:
            Dict: Import results with statistics and errors
        """
        try:
            # Validate file format
            if file_format.lower() not in self.SUPPORTED_FORMATS:
                raise ValidationError(f"Unsupported file format: {file_format}")
            
            # Reset import statistics
            self._reset_stats()
            
            # Read data based on format
            data_rows = self._read_file(file_path, file_format)
            
            if not data_rows:
                raise ValidationError("No data found in file")
            
            # Process data based on import type
            with transaction.atomic():
                if import_type == 'orders':
                    result = self._import_orders(data_rows, user)
                elif import_type == 'sellers':
                    result = self._import_sellers(data_rows, user)
                elif import_type == 'feedback':
                    result = self._import_feedback(data_rows, user)
                else:
                    raise ValidationError(f"Unsupported import type: {import_type}")
                
                # Log import event
                AuditEvent.log_event(
                    event_type=AuditEvent.EventType.IMPORT_DATA,
                    user=user,
                    description=f"Data import completed: {import_type}",
                    severity=AuditEvent.Severity.MEDIUM,
                    file_path=file_path,
                    import_type=import_type,
                    **self.import_stats
                )
            
            return {
                'success': True,
                'statistics': self.import_stats,
                'message': f"Successfully imported {self.import_stats['successful_imports']} records"
            }
            
        except Exception as e:
            logger.error(f"Data import failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'statistics': self.import_stats
            }
    
    def _read_file(self, file_path: str, file_format: str) -> List[Dict]:
        """Read data from file based on format."""
        try:
            if file_format.lower() == '.csv':
                return self._read_csv(file_path)
            elif file_format.lower() in ['.xlsx', '.xls']:
                return self._read_excel(file_path)
            elif file_format.lower() == '.json':
                return self._read_json(file_path)
            else:
                raise ValidationError(f"Unsupported format: {file_format}")
        
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise ValidationError(f"Could not read file: {e}")
    
    def _read_csv(self, file_path: str) -> List[Dict]:
        """Read CSV file and return list of dictionaries."""
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                # Try to detect delimiter
                sample = file.read(1024)
                file.seek(0)
                
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is row 1)
                    if any(row.values()):  # Skip empty rows
                        row['_row_number'] = row_num
                        data.append(row)
        
        except Exception as e:
            raise ValidationError(f"CSV reading error: {e}")
        
        return data
    
    def _read_excel(self, file_path: str) -> List[Dict]:
        """Read Excel file and return list of dictionaries."""
        try:
            df = pd.read_excel(file_path)
            
            # Convert NaN to None
            df = df.where(pd.notnull(df), None)
            
            # Convert to list of dictionaries
            data = []
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                row_dict['_row_number'] = index + 2  # Excel rows start from 1, header is row 1
                data.append(row_dict)
            
            return data
        
        except Exception as e:
            raise ValidationError(f"Excel reading error: {e}")
    
    def _read_json(self, file_path: str) -> List[Dict]:
        """Read JSON file and return list of dictionaries."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                
                if not isinstance(data, list):
                    raise ValidationError("JSON file must contain an array of objects")
                
                # Add row numbers
                for index, item in enumerate(data):
                    item['_row_number'] = index + 1
                
                return data
        
        except Exception as e:
            raise ValidationError(f"JSON reading error: {e}")
    
    def _import_orders(self, data_rows: List[Dict], user: User) -> Dict:
        """Import order data from parsed rows."""
        self.import_stats['total_records'] = len(data_rows)
        
        # Define required fields and their mappings
        required_fields = {
            'seller_id': ['seller_id', 'seller', 'seller_business_registration'],
            'order_number': ['order_number', 'order_id', 'order'],
            'customer_email': ['customer_email', 'email', 'customer'],
            'order_amount': ['order_amount', 'amount', 'total', 'price'],
            'order_date': ['order_date', 'date', 'created_date']
        }
        
        optional_fields = {
            'status': ['status', 'order_status'],
            'shipped_date': ['shipped_date', 'ship_date'],
            'delivered_date': ['delivered_date', 'delivery_date'],
            'is_returned': ['is_returned', 'returned', 'return'],
            'return_reason': ['return_reason', 'return_note']
        }
        
        for row in data_rows:
            try:
                # Map fields from row data
                order_data = self._map_row_fields(row, required_fields, optional_fields)
                
                # Validate and create order
                order = self._create_order_from_data(order_data, row['_row_number'])
                
                if order:
                    self.import_stats['successful_imports'] += 1
            
            except Exception as e:
                self.import_stats['failed_imports'] += 1
                self.import_stats['errors'].append({
                    'row': row.get('_row_number', 'unknown'),
                    'error': str(e),
                    'data': row
                })
        
        return self.import_stats
    
    def _import_sellers(self, data_rows: List[Dict], user: User) -> Dict:
        """Import seller data from parsed rows."""
        self.import_stats['total_records'] = len(data_rows)
        
        required_fields = {
            'business_name': ['business_name', 'name', 'company'],
            'business_registration': ['business_registration', 'registration', 'reg_number'],
            'email': ['email', 'user_email', 'contact_email']
        }
        
        optional_fields = {
            'description': ['description', 'about', 'bio'],
            'phone': ['phone', 'contact_phone', 'mobile'],
            'status': ['status', 'seller_status']
        }
        
        for row in data_rows:
            try:
                # Map fields from row data
                seller_data = self._map_row_fields(row, required_fields, optional_fields)
                
                # Create or update seller
                seller = self._create_seller_from_data(seller_data, row['_row_number'])
                
                if seller:
                    self.import_stats['successful_imports'] += 1
            
            except Exception as e:
                self.import_stats['failed_imports'] += 1
                self.import_stats['errors'].append({
                    'row': row.get('_row_number', 'unknown'),
                    'error': str(e),
                    'data': row
                })
        
        return self.import_stats
    
    def _import_feedback(self, data_rows: List[Dict], user: User) -> Dict:
        """Import customer feedback data from parsed rows."""
        self.import_stats['total_records'] = len(data_rows)
        
        required_fields = {
            'order_number': ['order_number', 'order_id', 'order'],
            'rating': ['rating', 'score', 'stars'],
            'customer_email': ['customer_email', 'email', 'customer']
        }
        
        optional_fields = {
            'comment': ['comment', 'feedback', 'review', 'notes'],
            'feedback_date': ['feedback_date', 'date', 'created_date']
        }
        
        for row in data_rows:
            try:
                # Map fields from row data
                feedback_data = self._map_row_fields(row, required_fields, optional_fields)
                
                # Create feedback
                feedback = self._create_feedback_from_data(feedback_data, row['_row_number'])
                
                if feedback:
                    self.import_stats['successful_imports'] += 1
            
            except Exception as e:
                self.import_stats['failed_imports'] += 1
                self.import_stats['errors'].append({
                    'row': row.get('_row_number', 'unknown'),
                    'error': str(e),
                    'data': row
                })
        
        return self.import_stats
    
    def _map_row_fields(self, row: Dict, required_fields: Dict, 
                       optional_fields: Dict) -> Dict:
        """Map row data to model fields using field mappings."""
        mapped_data = {}
        
        # Map required fields
        for field_name, possible_keys in required_fields.items():
            value = None
            for key in possible_keys:
                if key in row and row[key] is not None and str(row[key]).strip():
                    value = str(row[key]).strip()
                    break
            
            if value is None:
                raise ValidationError(f"Required field '{field_name}' not found or empty. "
                                    f"Expected one of: {', '.join(possible_keys)}")
            
            mapped_data[field_name] = value
        
        # Map optional fields
        for field_name, possible_keys in optional_fields.items():
            value = None
            for key in possible_keys:
                if key in row and row[key] is not None:
                    value = str(row[key]).strip() if str(row[key]).strip() else None
                    break
            
            if value:
                mapped_data[field_name] = value
        
        return mapped_data
    
    def _create_order_from_data(self, order_data: Dict, row_number: int) -> Optional[Order]:
        """Create Order instance from mapped data."""
        try:
            # Find seller
            seller = self._find_seller(order_data['seller_id'])
            if not seller:
                raise ValidationError(f"Seller not found: {order_data['seller_id']}")
            
            # Validate and convert data types
            order_amount = self._parse_decimal(order_data['order_amount'])
            order_date = self._parse_date(order_data['order_date'])
            
            # Check if order already exists
            if Order.objects.filter(order_number=order_data['order_number']).exists():
                raise ValidationError(f"Order {order_data['order_number']} already exists")
            
            # Create order
            order = Order.objects.create(
                seller=seller,
                order_number=order_data['order_number'],
                customer_email=order_data['customer_email'],
                order_amount=order_amount,
                order_date=order_date,
                status=order_data.get('status', Order.Status.PENDING),
                shipped_date=self._parse_date(order_data.get('shipped_date')),
                delivered_date=self._parse_date(order_data.get('delivered_date')),
                is_returned=self._parse_boolean(order_data.get('is_returned', False)),
                return_reason=order_data.get('return_reason')
            )
            
            return order
            
        except Exception as e:
            raise ValidationError(f"Row {row_number}: {e}")
    
    def _create_seller_from_data(self, seller_data: Dict, row_number: int) -> Optional[Seller]:
        """Create or update Seller instance from mapped data."""
        try:
            # Check if user exists
            user_email = seller_data['email']
            user, created = User.objects.get_or_create(
                email=user_email,
                defaults={
                    'role': User.Role.SELLER,
                    'is_verified': True,
                    'is_approved': True
                }
            )
            
            # Check if seller profile exists
            seller, seller_created = Seller.objects.get_or_create(
                business_registration=seller_data['business_registration'],
                defaults={
                    'user': user,
                    'business_name': seller_data['business_name'],
                    'description': seller_data.get('description', ''),
                    'status': seller_data.get('status', Seller.Status.ACTIVE)
                }
            )
            
            # Update if not created
            if not seller_created:
                seller.business_name = seller_data['business_name']
                seller.description = seller_data.get('description', seller.description)
                seller.save()
            
            return seller
            
        except Exception as e:
            raise ValidationError(f"Row {row_number}: {e}")
    
    def _create_feedback_from_data(self, feedback_data: Dict, row_number: int) -> Optional[CustomerFeedback]:
        """Create CustomerFeedback instance from mapped data."""
        try:
            # Find order
            order = Order.objects.filter(order_number=feedback_data['order_number']).first()
            if not order:
                raise ValidationError(f"Order not found: {feedback_data['order_number']}")
            
            # Validate rating
            rating = int(float(feedback_data['rating']))
            if not (1 <= rating <= 5):
                raise ValidationError(f"Rating must be between 1 and 5, got: {rating}")
            
            # Create feedback
            feedback = CustomerFeedback.objects.create(
                order=order,
                customer_email=feedback_data['customer_email'],
                rating=rating,
                comment=feedback_data.get('comment', ''),
                created_at=self._parse_date(feedback_data.get('feedback_date')) or timezone.now()
            )
            
            return feedback
            
        except Exception as e:
            raise ValidationError(f"Row {row_number}: {e}")
    
    def _find_seller(self, seller_identifier: str) -> Optional[Seller]:
        """Find seller by ID, business registration, or business name."""
        try:
            # Try by ID first
            if seller_identifier.isdigit():
                seller = Seller.objects.filter(id=int(seller_identifier)).first()
                if seller:
                    return seller
            
            # Try by business registration
            seller = Seller.objects.filter(business_registration=seller_identifier).first()
            if seller:
                return seller
            
            # Try by business name
            seller = Seller.objects.filter(business_name__iexact=seller_identifier).first()
            return seller
            
        except Exception:
            return None
    
    def _parse_decimal(self, value: str) -> Decimal:
        """Parse string to Decimal with validation."""
        if not value:
            raise ValidationError("Amount cannot be empty")
        
        try:
            # Remove currency symbols and commas
            clean_value = str(value).replace('$', '').replace(',', '').strip()
            return Decimal(clean_value)
        except (InvalidOperation, ValueError):
            raise ValidationError(f"Invalid amount format: {value}")
    
    def _parse_date(self, value: str) -> Optional[datetime]:
        """Parse string to datetime with multiple format support."""
        if not value:
            return None
        
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ'
        ]
        
        for date_format in date_formats:
            try:
                parsed_date = datetime.strptime(str(value), date_format)
                return timezone.make_aware(parsed_date) if timezone.is_naive(parsed_date) else parsed_date
            except ValueError:
                continue
        
        raise ValidationError(f"Invalid date format: {value}")
    
    def _parse_boolean(self, value) -> bool:
        """Parse various boolean representations."""
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ['true', '1', 'yes', 'y', 'on']
        
        return bool(value)
    
    def _reset_stats(self):
        """Reset import statistics."""
        self.import_stats = {
            'total_records': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'errors': []
        }
    
    def get_import_template(self, import_type: str) -> Dict:
        """Get template structure for import files."""
        templates = {
            'orders': {
                'required_columns': [
                    'seller_id', 'order_number', 'customer_email', 
                    'order_amount', 'order_date'
                ],
                'optional_columns': [
                    'status', 'shipped_date', 'delivered_date', 
                    'is_returned', 'return_reason'
                ],
                'example_data': {
                    'seller_id': '1 or ABC123',
                    'order_number': 'ORD-001',
                    'customer_email': 'customer@example.com',
                    'order_amount': '99.99',
                    'order_date': '2024-01-15',
                    'status': 'delivered',
                    'shipped_date': '2024-01-16',
                    'delivered_date': '2024-01-18',
                    'is_returned': 'false',
                    'return_reason': ''
                }
            },
            'sellers': {
                'required_columns': [
                    'business_name', 'business_registration', 'email'
                ],
                'optional_columns': [
                    'description', 'phone', 'status'
                ],
                'example_data': {
                    'business_name': 'ABC Electronics',
                    'business_registration': 'ABC123',
                    'email': 'seller@abc.com',
                    'description': 'Electronics retailer',
                    'phone': '+1-555-0123',
                    'status': 'active'
                }
            },
            'feedback': {
                'required_columns': [
                    'order_number', 'rating', 'customer_email'
                ],
                'optional_columns': [
                    'comment', 'feedback_date'
                ],
                'example_data': {
                    'order_number': 'ORD-001',
                    'rating': '5',
                    'customer_email': 'customer@example.com',
                    'comment': 'Great product!',
                    'feedback_date': '2024-01-20'
                }
            }
        }
        
        return templates.get(import_type, {})