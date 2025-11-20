import mysql.connector
from mysql.connector import Error
import pandas as pd
from sqlalchemy import create_engine, text
import argparse
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional, List
import re
import structlog
import sys
import logging

# Configure structlog to output to stderr instead of stdout
# This is critical for MCP servers which must keep stdout clean for JSON-RPC
logging.basicConfig(
    stream=sys.stderr,
    format='%(message)s',
    level=logging.INFO
)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Initialize FastMCP server
mcp = FastMCP("telecom_customer_support")

# Create structured logger for application code
logger = structlog.get_logger(__name__)

# Database configuration - initialize from CloudFormation
from utils import initialize_database_from_cloudformation

engine = initialize_database_from_cloudformation(
    database_name='customer_db',
    logger_instance=logger
)

def query_to_dataframe(query: str, params: Dict = None) -> pd.DataFrame:
    """Execute SQL query a  nd return results as DataFrame"""
    try:
        df = pd.read_sql(query, engine, params=params)
        return df
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

def execute_ddl_statement(statement: str, params: Dict = None) -> bool:
    """Execute DDL statement (INSERT, UPDATE, DELETE) and return success status"""
    try:
        with engine.begin() as conn:
            result = conn.execute(text(statement), params or {})
            rows_affected = result.rowcount
            print(f"Statement executed successfully. Rows affected: {rows_affected}", file=sys.stderr)
            return True
    except Exception as e:
        print(f"Error executing statement: {e}", file=sys.stderr)
        return False


def df_to_dict(df: pd.DataFrame) -> Dict[str, Any]:
    """Convert DataFrame to dictionary format for MCP response"""
    if df is None or df.empty:
        return {'message': 'No results found', 'data': []}
    return {'data': df.to_dict('records'), 'count': len(df)}

# =============================================================================
# 1. CUSTOMER ACCOUNT LOOKUP TOOLS
# =============================================================================

@mcp.tool()
def find_customer_by_phone(phone: str) -> Dict[str, Any]:
    """Find customer by phone number (most common lookup).
    
    Args:
        phone: Customer's phone number (e.g., '555-1001')
        
    Returns:
        Customer details including name, email, status, and account creation date
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Email,
        cs.PhoneNumber,
        c.Status as AccountStatus,
        c.CreatedDate as CustomerSince
    FROM Customers c
    JOIN CustomerSubscriptions cs 
        ON c.CustomerID = cs.CustomerID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE cs.PhoneNumber = %(phone)s
    )
    """
    df = query_to_dataframe(query, {'phone': phone})
    return df_to_dict(df)

@mcp.tool()
def find_customer_by_email(email: str) -> Dict[str, Any]:
    """Find customer by email address.
    
    Args:
        email: Customer's email address
        
    Returns:
        Customer details including ID, name, phone, and account status
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Email,
        c.Status as AccountStatus
    FROM Customers c
    JOIN CustomerSubscriptions cs 
        ON c.CustomerID = cs.CustomerID
    WHERE c.Email = %(email)s
    """
    df = query_to_dataframe(query, {'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_complete_customer_profile(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Get complete customer profile with all phone lines and services.
    
    Args:
        phone: Customer's contact phone number
        email: Customer's email address
        
    Returns:
        Complete customer profile including all service lines, plans, and usage
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Email,
        c.Phone as ContactPhone,
        c.Status as AccountStatus,
        cs.PhoneNumber as ServiceLine,
        sp.PlanName,
        cs.Status as LineStatus,
        cs.RenewalDate,
        cs.MonthlyDataUsage,
        cs.Notes
    FROM Customers c
    LEFT JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    LEFT JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY cs.ActivationDate
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 2. BILLING AND INVOICE TOOLS
# =============================================================================

@mcp.tool()
def get_current_bill(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Get current month's bill for a customer.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Current invoice details including amounts, due date, and status
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        i.InvoiceDate,
        i.DueDate,
        i.SubtotalAmount,
        i.TaxAmount,
        i.DiscountAmount,
        i.TotalAmount,
        i.Status as InvoiceStatus
    FROM Customers c
    JOIN Invoices i ON c.CustomerID = i.CustomerID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND i.BillingPeriodStart >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
    ORDER BY i.InvoiceDate DESC
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_bill_breakdown(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Get detailed breakdown of current bill.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Detailed line items showing what customer is being charged for
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        ili.Description,
        ili.Quantity,
        ili.UnitPrice,
        ili.LineTotal,
        ili.ChargeType
    FROM Customers c
    JOIN Invoices i ON c.CustomerID = i.CustomerID
    JOIN InvoiceLineItems ili ON i.InvoiceID = ili.InvoiceID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND i.BillingPeriodStart >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
    ORDER BY ili.ChargeType, ili.LineTotal DESC
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_payment_history(phone: str = "", email: str = "", months: int = 3) -> Dict[str, Any]:
    """Check payment history for specified number of months.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        months: Number of months to look back (default: 3)
        
    Returns:
        Payment history including dates, amounts, methods, and status
    """
    query = """
    SELECT 
        p.PaymentDate,
        p.PaymentAmount,
        pm.MethodName as PaymentMethod,
        p.Status as PaymentStatus,
        p.TransactionID,
        i.TotalAmount as InvoiceAmount,
        p.Notes
    FROM Customers c
    JOIN Payments p ON c.CustomerID = p.CustomerID
    JOIN Invoices i ON p.InvoiceID = i.InvoiceID
    JOIN PaymentMethods pm ON p.PaymentMethod = pm.MethodID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND p.PaymentDate >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)
    ORDER BY p.PaymentDate DESC
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email, 'months': months})
    return df_to_dict(df)

@mcp.tool()
def get_overdue_invoices(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Find overdue invoices for a customer.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Overdue invoices with amounts and days overdue
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Phone,
        i.InvoiceDate,
        i.DueDate,
        i.TotalAmount,
        i.Status,
        DATEDIFF(CURDATE(), i.DueDate) as DaysOverdue
    FROM Customers c
    JOIN Invoices i ON c.CustomerID = i.CustomerID
    WHERE i.Status = 'Overdue'
    AND c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY i.DueDate
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 3. SERVICE PLAN AND USAGE TOOLS
# =============================================================================

@mcp.tool()
def get_current_plans(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Get current plan details for all customer lines.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Current service plans for all lines including pricing and renewal dates
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        sp.PlanName,
        sp.Description,
        sp.DataAllowance,
        sp.Price,
        cs.Status as LineStatus,
        cs.RenewalDate
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY cs.ActivationDate
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    print(f"current plans:\n{df.to_markdown()}", file=sys.stderr)
    return df_to_dict(df)

@mcp.tool()
def get_current_usage(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Check current month usage for all customer lines.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Current usage statistics including data, minutes, texts, and usage percentages
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        sp.PlanName,
        sp.DataAllowance,
        cs.MonthlyDataUsage as CurrentDataUsage,
        cs.MonthlyMinutesUsed,
        cs.MonthlyTextsUsed,
        cs.DataWarningThreshold,
        CASE 
            WHEN sp.DataAllowance IS NULL THEN 'Unlimited'
            ELSE CONCAT(ROUND((cs.MonthlyDataUsage / sp.DataAllowance) * 100, 1), '%%')
        END as DataUsagePercent
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND cs.Status = 'Active'
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_overage_charges(phone: str = "", email: str = "", months: int = 3) -> Dict[str, Any]:
    """Check for overage charges in recent months.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        months: Number of months to look back (default: 3)
        
    Returns:
        Overage charges by type and billing month
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        oc.BillingMonth,
        oc.OverageType,
        oc.OverageAmount,
        oc.ChargePerUnit,
        oc.TotalCharge
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN OverageCharges oc ON cs.SubscriptionID = oc.SubscriptionID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND oc.BillingMonth >= DATE_SUB(CURDATE(), INTERVAL %(months)s MONTH)
    ORDER BY oc.BillingMonth DESC
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email, 'months': months})
    return df_to_dict(df)

# =============================================================================
# 4. ADD-ON AND FEATURE TOOLS
# =============================================================================

@mcp.tool()
def get_active_addons(phone: str = "", email: str = "") -> Dict[str, Any]:
    """List all active add-ons for customer.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Active add-ons with pricing and activation details
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        ao.AddOnName,
        ao.Description,
        ao.Price,
        sao.ActivationDate,
        sao.Status as AddOnStatus
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN SubscriptionAddOns sao ON cs.SubscriptionID = sao.SubscriptionID
    JOIN AddOns ao ON sao.AddOnID = ao.AddOnID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY cs.PhoneNumber, ao.AddOnName
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_available_addons() -> Dict[str, Any]:
    """Show available add-ons customer could purchase.
    
    Returns:
        Available add-ons with descriptions and pricing
    """
    query = """
    SELECT 
        ao.AddOnName,
        ao.Description,
        ao.Price,
        ao.BillingCycle,
        ao.Status
    FROM AddOns ao
    WHERE ao.Status = 'Active'
    ORDER BY ao.Price
    """
    df = query_to_dataframe(query)
    return df_to_dict(df)

# =============================================================================
# 5. DISCOUNT AND PROMOTION TOOLS
# =============================================================================

@mcp.tool()
def get_active_discounts(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Check active discounts for customer.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Active discounts with expiry information
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        d.DiscountName,
        d.Description,
        d.DiscountType,
        d.DiscountValue,
        cd.AppliedDate,
        cd.ExpiryDate,
        cd.Status as DiscountStatus,
        CASE 
            WHEN cd.ExpiryDate IS NULL THEN 'Permanent'
            WHEN cd.ExpiryDate > CURDATE() THEN CONCAT('Expires in ', DATEDIFF(cd.ExpiryDate, CURDATE()), ' days')
            ELSE 'Expired'
        END as ExpiryInfo
    FROM Customers c
    JOIN CustomerDiscounts cd ON c.CustomerID = cd.CustomerID
    JOIN Discounts d ON cd.DiscountID = d.DiscountID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND cd.Status = 'Active'
    ORDER BY cd.AppliedDate
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 6. ACCOUNT STATUS AND TROUBLESHOOTING TOOLS
# =============================================================================

@mcp.tool()
def check_account_suspension(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Check if account is suspended and why.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Account status, suspension details, and overdue invoice information
        If no invoices returned, its possible it wasn't sent and should be fixed.
    """
    query = """SELECT 
        i.InvoiceDate,
        c.FirstName,
        c.LastName,
        c.Status as AccountStatus,
        cs.PhoneNumber,
        cs.Status as LineStatus,
        cs.SuspensionDate,
        cs.Notes,
        COUNT(i.InvoiceID) as OverdueInvoices,
        SUM(i.TotalAmount) as OverdueAmount
    FROM CustomerSubscriptions cs 
    JOIN Customers c
        ON cs.CustomerID = c.CustomerID
    JOIN Invoices i 
        ON c.CustomerID = i.CustomerID 
        -- AND i.Status = 'Overdue'
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    GROUP BY c.CustomerID, cs.SubscriptionID
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def get_recent_account_activity(phone: str = "", email: str = "", days: int = 30) -> Dict[str, Any]:
    """Get recent account activity/changes.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        days: Number of days to look back (default: 30)
        
    Returns:
        Recent account changes and modifications
    """
    query = """
    SELECT 
        al.LogTimestamp,
        al.ActionType,
        al.OldValue,
        al.NewValue,
        al.ChangedBy,
        al.Reason,
        cs.PhoneNumber
    FROM Customers c
    JOIN AuditLog al ON c.CustomerID = al.CustomerID
    LEFT JOIN CustomerSubscriptions cs ON al.SubscriptionID = cs.SubscriptionID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND al.LogTimestamp >= DATE_SUB(CURDATE(), INTERVAL %(days)s DAY)
    ORDER BY al.LogTimestamp DESC
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email, 'days': days})
    return df_to_dict(df)

# =============================================================================
# 7. PAYMENT METHOD TOOLS
# =============================================================================

@mcp.tool()
def get_payment_methods(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Show customer's payment methods.
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Payment methods with expiry status and default settings
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        pm.MethodName,
        cpm.PaymentMethodDetails,
        cpm.IsDefault,
        cpm.Status,
        cpm.ExpiryDate,
        CASE 
            WHEN cpm.ExpiryDate IS NOT NULL AND cpm.ExpiryDate < CURDATE() THEN 'EXPIRED'
            WHEN cpm.ExpiryDate IS NOT NULL AND cpm.ExpiryDate <= DATE_ADD(CURDATE(), INTERVAL 30 DAY) THEN 'EXPIRING SOON'
            ELSE 'VALID'
        END as ExpiryStatus
    FROM Customers c
    JOIN CustomerPaymentMethods cpm ON c.CustomerID = cpm.CustomerID
    JOIN PaymentMethods pm ON cpm.MethodID = pm.MethodID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY cpm.IsDefault DESC, cpm.Status
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 8. FAMILY/MULTI-LINE ACCOUNT TOOLS
# =============================================================================

@mcp.tool()
def get_family_lines(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Show all lines for a family account.
    
    Args:
        phone: Primary account holder's phone number
        email: Primary account holder's email address
        
    Returns:
        All lines on the family account with usage and status
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        sp.PlanName,
        cs.Status,
        cs.MonthlyDataUsage,
        cs.Notes,
        cs.ActivationDate
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    ORDER BY cs.ActivationDate
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

@mcp.tool()
def calculate_total_monthly_cost(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Calculate total monthly cost for customer (all lines + add-ons).
    
    Args:
        phone: Customer's phone number
        email: Customer's email address
        
    Returns:
        Breakdown of total monthly costs including plans and add-ons
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        SUM(sp.Price) as TotalPlanCost,
        SUM(COALESCE(ao.Price, 0)) as TotalAddOnCost,
        SUM(sp.Price) + SUM(COALESCE(ao.Price, 0)) as TotalMonthlyCost
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    LEFT JOIN SubscriptionAddOns sao ON cs.SubscriptionID = sao.SubscriptionID AND sao.Status = 'Active'
    LEFT JOIN AddOns ao ON sao.AddOnID = ao.AddOnID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
        AND cs.Status = 'Active'
    GROUP BY c.CustomerID
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 9. BUSINESS ACCOUNT TOOLS
# =============================================================================

@mcp.tool()
def get_business_account_summary(phone: str = "", email: str = "") -> Dict[str, Any]:
    """Business account summary.
    
    Args:
        phone: Business account phone number
        email: Business account email address
        
    Returns:
        Business account overview with line counts and usage statistics
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Email,
        COUNT(cs.SubscriptionID) as TotalLines,
        SUM(CASE WHEN cs.Status = 'Active' THEN 1 ELSE 0 END) as ActiveLines,
        SUM(cs.MonthlyDataUsage) as TotalDataUsage,
        AVG(sp.Price) as AvgPlanCost
    FROM Customers c
    JOIN CustomerSubscriptions cs ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
    WHERE c.CustomerID = (
        SELECT c.CustomerID
        FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
    )
    GROUP BY c.CustomerID
    """
    df = query_to_dataframe(query, {'phone': phone, 'email': email})
    return df_to_dict(df)

# =============================================================================
# 10. AGENT REFERENCE TOOLS
# =============================================================================

@mcp.tool()
def find_overdue_customers() -> Dict[str, Any]:
    """Find customers with overdue payments (for collections).
    
    Returns:
        List of customers with overdue payments sorted by days overdue
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        c.Email,
        i.DueDate,
        i.TotalAmount,
        DATEDIFF(CURDATE(), i.DueDate) as DaysOverdue
    FROM Customers c
    JOIN Invoices i 
        ON c.CustomerID = i.CustomerID
    WHERE i.Status = 'Overdue'
    ORDER BY DaysOverdue DESC
    """
    df = query_to_dataframe(query)
    return df_to_dict(df)

@mcp.tool()
def find_high_usage_customers(usage_threshold: float = 0.8) -> Dict[str, Any]:
    """Find customers with high data usage (potential upsell opportunities).
    
    Args:
        usage_threshold: Usage percentage threshold (default: 0.8 for 80%)
        
    Returns:
        Customers with high data usage who might need plan upgrades
    """
    query = """
    SELECT 
        c.FirstName,
        c.LastName,
        cs.PhoneNumber,
        sp.PlanName,
        cs.PlanID,
        cs.MonthlyDataUsage,
        sp.DataAllowance,
        ROUND((cs.MonthlyDataUsage / sp.DataAllowance) * 100, 1) as UsagePercent
    FROM Customers c
    JOIN CustomerSubscriptions cs 
        ON c.CustomerID = cs.CustomerID
    JOIN ServicePlans sp 
        ON cs.PlanID = sp.PlanID
    WHERE sp.DataAllowance IS NOT NULL
        AND cs.MonthlyDataUsage > (sp.DataAllowance * %(threshold)s)
        AND cs.Status = 'Active'
    ORDER BY UsagePercent DESC
    """

    df = query_to_dataframe(query, {'threshold': usage_threshold})
    return df_to_dict(df)

@mcp.tool()
def find_loyalty_eligible_customers(days: int = 365) -> Dict[str, Any]:
    """Find long-term customers eligible for loyalty discounts.

    Args:
        days: Minimum days required to be considered loyal (default: 365 days for 1 year)
    
    Returns:
        Any Long-term customers without loyalty discounts who may be eligible
    """
    query = """SELECT 
        c.FirstName,
        c.LastName,
        cd.CustomerDiscountID,
        c.Status,
        MIN(cs.CreatedDate) as MemberSince,
        DATEDIFF(CURDATE(), cs.CreatedDate) as DaysAsCustomer,
        COUNT(cs.SubscriptionID) as NumberOfLines
    FROM Customers c
    JOIN CustomerSubscriptions cs 
        ON c.CustomerID = cs.CustomerID
    LEFT JOIN CustomerDiscounts cd 
        ON c.CustomerID = cd.CustomerID 
        AND cd.DiscountID = 5
    WHERE DATEDIFF(CURDATE(), cs.CreatedDate) > %(days)s
        AND cd.CustomerDiscountID IS NULL
        AND c.Status = 'Active'
    GROUP BY c.CustomerID
    ORDER BY DaysAsCustomer DESC"""



    df = query_to_dataframe(query, {'days': days})
    return df_to_dict(df)

# =============================================================================
# 11. SERVICE MANAGEMENT TOOLS (from notebook)
# =============================================================================

@mcp.tool()
def add_new_line(plan_name: str, phone: str = "", email: str = "") -> Dict[str, Any]:
    """Add a new line to a customer's account.

    Args:
        plan_name: Name of the plan (e.g., 'Basic', 'Unlimited Plus', 'Family Basic')
        phone: Customer's phone number
        email: Customer's email address

    Returns:
        New line details including plan name, activation date, and renewal date
    """

    plan_name_query = """
    SELECT PlanID, PlanName
    FROM ServicePlans
    WHERE PlanName = %(plan_name)s
    """
    print(f"Looking for plan by name: {plan_name}\nquery: {plan_name_query}", file=sys.stderr)
    df = query_to_dataframe(plan_name_query, {'plan_name': plan_name})
    if len(df) > 0:
        print(f"plans query result:\n{df.to_markdown()}", file=sys.stderr)
        plan_id = df_to_dict(df)['data'][0]['PlanID']
        customer_id_query = """SELECT c.CustomerID
            FROM Customers c
                LEFT JOIN CustomerSubscriptions cs 
                    ON c.CustomerID = cs.CustomerID
                WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
                LIMIT 1
        """
        customer_results = query_to_dataframe(customer_id_query, {'phone': phone, 'email': email})
        if len(customer_results) > 0:
            customer_id = df_to_dict(customer_results)['data'][0]['CustomerID']
        
            query = """
            INSERT INTO CustomerSubscriptions (
                CustomerID, 
                PlanID, 
                PhoneNumber, 
                IMEI, 
                ActivationDate, 
                RenewalDate, 
                Status, 
                AutoRenew, 
                Notes
            ) VALUES (
                :customer_id,            -- CustomerID
                :plan_id,                -- Plan ID
                '555-1003',                 -- New phone number
                '123456789012347',          -- New IMEI
                CURDATE(),                  -- Today
                DATE_ADD(CURDATE(), INTERVAL 30 DAY), -- Next month
                'Active',                   -- Active status
                TRUE,                       -- Auto-renew
                'New phone line added'
            );
            """
            successful = execute_ddl_statement(query, {'plan_id': plan_id, 'customer_id': customer_id})
            if successful:
                return "Successfully added new phone line to customer plan"
            else:
                return "Error adding service plan!"
        else:
            return f"Customer with phone number '{phone}' or email '{email}' could not be found."
    else:
        return f"No plan with the name like '{plan_name}' could be found. Try a variation in the naming?"

@mcp.tool()
def cancel_service_plan(plan_name: str, phone: str = "", email: str = "", phone_to_cancel = "") -> str:
    """Cancel a service plan for a customer.

    Args:
        plan_name: Name of the plan to cancel (e.g., 'Basic', 'Unlimited Plus', 'Family Basic')
        phone: Customer's phone number
        email: Customer's email address
        phone_to_cancel: phone number for the line to cancel service. Assumes same as phone if not specified.

    Returns:
        Confirmation message
    """
    check_for_plan_qry = """SELECT 
            c.FirstName,
            c.LastName,
            cs.PhoneNumber,
            sp.PlanName,
            sp.Description,
            sp.Price,
            cs.Status as LineStatus,
            cs.RenewalDate
        FROM Customers c
        JOIN CustomerSubscriptions cs 
            ON c.CustomerID = cs.CustomerID
        JOIN ServicePlans sp 
            ON cs.PlanID = sp.PlanID
        WHERE c.CustomerID = (
            SELECT c.CustomerID
            FROM Customers c
            LEFT JOIN CustomerSubscriptions cs 
                ON c.CustomerID = cs.CustomerID
            WHERE (cs.PhoneNumber = %(phone)s OR c.Email = %(email)s)
            LIMIT 1
            )
        AND sp.PlanName = %(plan_name)s
        ORDER BY cs.ActivationDate
        """

    existing_plans_df = query_to_dataframe(check_for_plan_qry, {'phone': phone, 'email': email, 'plan_name': plan_name})
    print(f"current {plan_name} plans:\n{df.to_markdown()}", file=sys.stderr)
    if len(existing_plans_df) > 0:
        print(f"Verified User is subscribed to plan '{plan_name}'", file=sys.stderr)
        if phone_to_cancel == "":
            phone_to_cancel = phone
            
        if len(existing_plans_df) > 1:
            return f"Discovered more than one line using the {plan_name} plan:\n{df.to_markdown()}. Ask customer which phone number they'd like to cancel."
        else:
            
    
            query = """UPDATE CustomerSubscriptions cs
JOIN ServicePlans sp ON cs.PlanID = sp.PlanID
JOIN Customers c ON cs.CustomerID = c.CustomerID
JOIN (
    SELECT c.CustomerID
    FROM Customers c
    LEFT JOIN CustomerSubscriptions _cs
        ON c.CustomerID = _cs.CustomerID
    WHERE (_cs.PhoneNumber = :phone OR c.Email = :email)
    LIMIT 1
) AS target ON c.CustomerID = target.CustomerID
SET cs.Status = 'Cancelled', cs.LastModifiedDate = CURRENT_TIMESTAMP
WHERE sp.PlanName = :plan_name;
            """
            successful = execute_ddl_statement(query, {'phone': phone_to_cancel, 'email': email, 'plan_name': plan_name})
            contact_info = phone if phone else email
            if successful:
                return f"Successfully cancelled plan '{plan_name}' for customer '{contact_info}' effective today"
            else: 
                return f"Problem with removing plan '{plan_name}' from customer '{contact_info}'"
    else:
        contact_info = phone if phone else email
        return f"No active subscription found for plan '{plan_name}' for customer '{contact_info}'"

if __name__ == "__main__":
    mcp.run(transport='stdio')