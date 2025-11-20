-- Sample Data for Telecom Database (MySQL Safe Version)
-- This file contains INSERT statements for 10 customers with diverse service combinations
-- All dates are relative to the current timestamp for realistic testing

-- Disable foreign key checks temporarily for easier insertion
SET FOREIGN_KEY_CHECKS = 0;

-- Set current timestamp variable for dynamic date calculations
SET @current_date = CURDATE();
SET @current_month_start = DATE_FORMAT(@current_date, '%Y-%m-01');
SET @last_month_start = DATE_SUB(@current_month_start, INTERVAL 1 MONTH);
SET @two_months_ago = DATE_SUB(@current_month_start, INTERVAL 2 MONTH);
SET @three_months_ago = DATE_SUB(@current_month_start, INTERVAL 3 MONTH);
SET @current_month_end = LAST_DAY(@current_date);
SET @last_month_end = LAST_DAY(@last_month_start);
SET @two_months_ago_end = LAST_DAY(@two_months_ago);

-- Clear existing data (optional - uncomment if you want to reset)
-- DELETE FROM AuditLog;
-- DELETE FROM Payments;
-- DELETE FROM OverageCharges;
-- DELETE FROM InvoiceLineItems;
-- DELETE FROM Invoices;
-- DELETE FROM CustomerDiscounts;
-- DELETE FROM SubscriptionAddOns;
-- DELETE FROM CustomerSubscriptions;
-- DELETE FROM CustomerPaymentMethods;
-- DELETE FROM Customers;
-- DELETE FROM Discounts;
-- DELETE FROM AddOns;
-- DELETE FROM ServicePlans;
-- DELETE FROM PaymentMethods;

-- build tables (optional - uncomment if you want to reset)
-- Create Customers table
DROP TABLE IF EXISTS Customers;
CREATE TABLE Customers (
    CustomerID INT PRIMARY KEY AUTO_INCREMENT,
    FirstName VARCHAR(100) NOT NULL,
    LastName VARCHAR(100) NOT NULL,
    Email VARCHAR(100) UNIQUE,
    Address VARCHAR(255),
    City VARCHAR(100),
    State VARCHAR(50),
    ZipCode VARCHAR(10),
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Status ENUM('Active', 'Inactive', 'Suspended') DEFAULT 'Active'
);

-- Create ServicePlans table (base plans offered by provider)
DROP TABLE IF EXISTS ServicePlans;
CREATE TABLE ServicePlans (
    PlanID INT PRIMARY KEY AUTO_INCREMENT,
    PlanName VARCHAR(100) NOT NULL,
    Description TEXT,
    DataAllowance DECIMAL(10, 2) COMMENT 'in GB',
    UnlimitedCalls BOOLEAN DEFAULT TRUE,
    UnlimitedTexts BOOLEAN DEFAULT TRUE,
    InternationalMinutes INT COMMENT 'included minutes or 0 for none',
    Price DECIMAL(10, 2) NOT NULL,
    BillingCycle ENUM('Monthly', 'Annual') DEFAULT 'Monthly',
    Status ENUM('Active', 'Discontinued') DEFAULT 'Active',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create AddOns table (extra services/features)
DROP TABLE IF EXISTS AddOns;
CREATE TABLE AddOns (
    AddOnID INT PRIMARY KEY AUTO_INCREMENT,
    AddOnName VARCHAR(100) NOT NULL,
    Description TEXT,
    Price DECIMAL(10, 2) NOT NULL,
    BillingCycle ENUM('Monthly', 'Annual', 'OneTime') DEFAULT 'Monthly',
    Status ENUM('Active', 'Discontinued') DEFAULT 'Active'
);

-- Create CustomerSubscriptions table (main table for managing customer services)
DROP TABLE IF EXISTS CustomerSubscriptions;
CREATE TABLE CustomerSubscriptions (
    SubscriptionID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    PlanID INT NOT NULL,
    PhoneNumber VARCHAR(15) UNIQUE NOT NULL,
    IMEI VARCHAR(20),
    ActivationDate DATE NOT NULL,
    RenewalDate DATE,
    SuspensionDate DATE,
    Status ENUM('Active', 'Pending', 'Suspended', 'Cancelled') DEFAULT 'Active',
    MonthlyDataUsage DECIMAL(10, 2) DEFAULT 0 COMMENT 'in GB',
    MonthlyMinutesUsed INT DEFAULT 0,
    MonthlyTextsUsed INT DEFAULT 0,
    DataWarningThreshold INT DEFAULT 80 COMMENT 'percentage',
    AutoRenew BOOLEAN DEFAULT TRUE,
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    LastModifiedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (PlanID) REFERENCES ServicePlans(PlanID)
);

-- Create SubscriptionAddOns junction table (many-to-many relationship)
DROP TABLE IF EXISTS SubscriptionAddOns;
CREATE TABLE SubscriptionAddOns (
    SubscriptionAddOnID INT PRIMARY KEY AUTO_INCREMENT,
    SubscriptionID INT NOT NULL,
    AddOnID INT NOT NULL,
    ActivationDate DATE NOT NULL,
    Status ENUM('Active', 'Suspended', 'Cancelled') DEFAULT 'Active',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_subscription_addon (SubscriptionID, AddOnID),
    FOREIGN KEY (SubscriptionID) REFERENCES CustomerSubscriptions(SubscriptionID) ON DELETE CASCADE,
    FOREIGN KEY (AddOnID) REFERENCES AddOns(AddOnID)
);

-- Create Invoices table
DROP TABLE IF EXISTS Invoices;
CREATE TABLE Invoices (
    InvoiceID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    InvoiceDate DATE NOT NULL,
    DueDate DATE NOT NULL,
    BillingPeriodStart DATE NOT NULL,
    BillingPeriodEnd DATE NOT NULL,
    SubtotalAmount DECIMAL(10, 2) NOT NULL,
    TaxAmount DECIMAL(10, 2) DEFAULT 0,
    DiscountAmount DECIMAL(10, 2) DEFAULT 0,
    TotalAmount DECIMAL(10, 2) NOT NULL,
    Status ENUM('Draft', 'Sent', 'Paid', 'Overdue', 'Cancelled') DEFAULT 'Draft',
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE
);

-- Create InvoiceLineItems table (charges on each invoice)
DROP TABLE IF EXISTS InvoiceLineItems;
CREATE TABLE InvoiceLineItems (
    LineItemID INT PRIMARY KEY AUTO_INCREMENT,
    InvoiceID INT NOT NULL,
    SubscriptionID INT,
    AddOnID INT,
    Description VARCHAR(255) NOT NULL,
    Quantity INT DEFAULT 1,
    UnitPrice DECIMAL(10, 2) NOT NULL,
    LineTotal DECIMAL(10, 2) NOT NULL,
    ChargeType ENUM('Base Plan', 'Add-On', 'Overage', 'Credit', 'Adjustment') DEFAULT 'Base Plan',
    FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID) ON DELETE CASCADE,
    FOREIGN KEY (SubscriptionID) REFERENCES CustomerSubscriptions(SubscriptionID),
    FOREIGN KEY (AddOnID) REFERENCES AddOns(AddOnID)
);

-- Create OverageCharges table (track usage overages)
DROP TABLE IF EXISTS OverageCharges;
CREATE TABLE OverageCharges (
    OverageID INT PRIMARY KEY AUTO_INCREMENT,
    SubscriptionID INT NOT NULL,
    BillingMonth DATE NOT NULL,
    OverageType ENUM('Data', 'Minutes', 'Texts', 'International') NOT NULL,
    OverageAmount DECIMAL(10, 2) NOT NULL,
    ChargePerUnit DECIMAL(10, 2) NOT NULL,
    TotalCharge DECIMAL(10, 2) NOT NULL,
    InvoiceLineItemID INT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (SubscriptionID) REFERENCES CustomerSubscriptions(SubscriptionID) ON DELETE CASCADE,
    FOREIGN KEY (InvoiceLineItemID) REFERENCES InvoiceLineItems(LineItemID)
);

-- Create PaymentMethods table
DROP TABLE IF EXISTS PaymentMethods;
CREATE TABLE PaymentMethods (
    MethodID INT PRIMARY KEY AUTO_INCREMENT,
    MethodName VARCHAR(50) NOT NULL,
    Description VARCHAR(255),
    Status ENUM('Active', 'Inactive') DEFAULT 'Active'
);

-- Create CustomerPaymentMethods table (customers can have multiple payment methods)
DROP TABLE IF EXISTS CustomerPaymentMethods;
CREATE TABLE CustomerPaymentMethods (
    CustomerPaymentMethodID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    MethodID INT NOT NULL,
    PaymentMethodDetails VARCHAR(255) COMMENT 'Last 4 digits of card, account ending, etc',
    IsDefault BOOLEAN DEFAULT FALSE,
    Status ENUM('Active', 'Inactive', 'Expired') DEFAULT 'Active',
    ExpiryDate DATE,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (MethodID) REFERENCES PaymentMethods(MethodID)
);

-- Create Payments table
DROP TABLE IF EXISTS Payments;
CREATE TABLE Payments (
    PaymentID INT PRIMARY KEY AUTO_INCREMENT,
    InvoiceID INT NOT NULL,
    CustomerID INT NOT NULL,
    PaymentAmount DECIMAL(10, 2) NOT NULL,
    PaymentDate DATE NOT NULL,
    PaymentMethod INT NOT NULL,
    TransactionID VARCHAR(255),
    Status ENUM('Pending', 'Completed', 'Failed', 'Refunded') DEFAULT 'Pending',
    Notes TEXT,
    CreatedDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (InvoiceID) REFERENCES Invoices(InvoiceID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (PaymentMethod) REFERENCES PaymentMethods(MethodID)
);

-- Create Discounts table
DROP TABLE IF EXISTS Discounts;
CREATE TABLE Discounts (
    DiscountID INT PRIMARY KEY AUTO_INCREMENT,
    DiscountName VARCHAR(100) NOT NULL,
    Description TEXT,
    DiscountType ENUM('Percentage', 'FixedAmount') NOT NULL,
    DiscountValue DECIMAL(5, 2) NOT NULL,
    ValidFrom DATE NOT NULL,
    ValidUntil DATE,
    ApplicableToPlans VARCHAR(255) COMMENT 'comma-separated PlanIDs or "All"',
    Status ENUM('Active', 'Inactive', 'Expired') DEFAULT 'Active'
);

-- Create CustomerDiscounts junction table
DROP TABLE IF EXISTS CustomerDiscounts;
CREATE TABLE CustomerDiscounts (
    CustomerDiscountID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    DiscountID INT NOT NULL,
    AppliedDate DATE NOT NULL,
    ExpiryDate DATE,
    Status ENUM('Active', 'Used', 'Expired', 'Cancelled') DEFAULT 'Active',
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (DiscountID) REFERENCES Discounts(DiscountID)
);

-- Create AuditLog table (track customer support actions)
DROP TABLE IF EXISTS AuditLog;
CREATE TABLE AuditLog (
    LogID INT PRIMARY KEY AUTO_INCREMENT,
    CustomerID INT NOT NULL,
    SubscriptionID INT,
    ActionType VARCHAR(100) NOT NULL COMMENT 'e.g., Plan Changed, Add-On Added, Service Suspended',
    OldValue TEXT,
    NewValue TEXT,
    ChangedBy VARCHAR(100),
    Reason TEXT,
    LogTimestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE,
    FOREIGN KEY (SubscriptionID) REFERENCES CustomerSubscriptions(SubscriptionID) ON DELETE SET NULL
);

-- Create useful indexes
CREATE INDEX idx_customer_status ON Customers(Status);
CREATE INDEX idx_subscription_customer ON CustomerSubscriptions(CustomerID);
CREATE INDEX idx_subscription_status ON CustomerSubscriptions(Status);
CREATE INDEX idx_invoice_customer ON Invoices(CustomerID);
CREATE INDEX idx_invoice_status ON Invoices(Status);
CREATE INDEX idx_invoice_duedate ON Invoices(DueDate);
CREATE INDEX idx_payment_customer ON Payments(CustomerID);
CREATE INDEX idx_payment_status ON Payments(Status);
CREATE INDEX idx_plan_status ON ServicePlans(Status);

-- Insert Payment Methods (foundation data)
INSERT INTO PaymentMethods (MethodName, Description, Status) VALUES
('Credit Card', 'Payment via Visa/Mastercard/Amex', 'Active'),
('Debit Card', 'Direct debit from checking account', 'Active'),
('Bank Account', 'ACH transfer from bank account', 'Active'),
('Check', 'Paper check payment', 'Active');

-- Insert Service Plans
INSERT INTO ServicePlans (PlanName, Description, DataAllowance, UnlimitedCalls, UnlimitedTexts, InternationalMinutes, Price, BillingCycle, Status) VALUES
('Basic', 'Entry level plan with essential features', 5.0, TRUE, TRUE, 0, 40.00, 'Monthly', 'Active'),
('Standard', 'Mid-tier plan with more data', 15.0, TRUE, TRUE, 50, 55.00, 'Monthly', 'Active'),
('Unlimited Plus', 'Premium unlimited plan', NULL, TRUE, TRUE, 200, 75.00, 'Monthly', 'Active'),
('Family Basic', 'Family plan for multiple lines', 20.0, TRUE, TRUE, 100, 120.00, 'Monthly', 'Active'),
('Business Pro', 'Business plan with priority support', NULL, TRUE, TRUE, 500, 95.00, 'Monthly', 'Active'),
('Senior Plan', 'Discounted plan for seniors', 3.0, TRUE, TRUE, 0, 25.00, 'Monthly', 'Active');

-- Insert Add-Ons
INSERT INTO AddOns (AddOnName, Description, Price, BillingCycle, Status) VALUES
('Device Insurance', 'Protection against damage and theft', 12.00, 'Monthly', 'Active'),
('International Roaming', 'Data and calling while traveling abroad', 15.00, 'Monthly', 'Active'),
('Extra 5GB Data', 'Additional 5GB monthly data allowance', 10.00, 'Monthly', 'Active'),
('Premium Support', '24/7 priority customer support', 8.00, 'Monthly', 'Active'),
('Mobile Hotspot', 'Use phone as WiFi hotspot', 5.00, 'Monthly', 'Active'),
('Cloud Storage 50GB', '50GB cloud storage for photos and files', 6.00, 'Monthly', 'Active'),
('Caller ID Plus', 'Enhanced caller identification features', 3.00, 'Monthly', 'Active');

-- Insert Discounts
INSERT INTO Discounts (DiscountName, Description, DiscountType, DiscountValue, ValidFrom, ValidUntil, ApplicableToPlans, Status) VALUES
('New Customer Promo', '20% off first 3 months', 'Percentage', 20.00, DATE_SUB(@current_date, INTERVAL 6 MONTH), DATE_ADD(@current_date, INTERVAL 6 MONTH), 'All', 'Active'),
('Senior Discount', '$10 off monthly for 65+ customers', 'FixedAmount', 10.00, DATE_SUB(@current_date, INTERVAL 12 MONTH), NULL, '6', 'Active'),
('Military Discount', '15% off for military personnel', 'Percentage', 15.00, DATE_SUB(@current_date, INTERVAL 12 MONTH), NULL, 'All', 'Active'),
('Family Bundle Discount', '$20 off when 3+ lines', 'FixedAmount', 20.00, DATE_SUB(@current_date, INTERVAL 6 MONTH), DATE_ADD(@current_date, INTERVAL 6 MONTH), '4', 'Active'),
('Loyalty Discount', '10% off for 2+ year customers', 'Percentage', 10.00, DATE_SUB(@current_date, INTERVAL 12 MONTH), NULL, 'All', 'Active');

-- Insert Customers (10 diverse customers) - created over the past 3 months
INSERT INTO Customers (FirstName, LastName, Email, Address, City, State, ZipCode, CreatedDate, Status) VALUES
('John', 'Smith', 'john.smith@gmail.com', '123 Main St', 'Springfield', 'IL', '62701', DATE_SUB(@current_date, INTERVAL 75 DAY), 'Active'),
('Sarah', 'Johnson', 'sarah.johnson@yahoo.com', '456 Oak Ave', 'Chicago', 'IL', '60601', DATE_SUB(@current_date, INTERVAL 65 DAY), 'Active'),
('Michael', 'Brown', 'michael.brown@outlook.com', '789 Pine Rd', 'Peoria', 'IL', '61601', DATE_SUB(@current_date, INTERVAL 85 DAY), 'Active'),
('Emily', 'Davis', 'emily.davis@hotmail.com', '321 Elm St', 'Rockford', 'IL', '61101', DATE_SUB(@current_date, INTERVAL 55 DAY), 'Active'),
('Robert', 'Wilson', 'robert.wilson@aol.com', '654 Maple Dr', 'Naperville', 'IL', '60540', DATE_SUB(@current_date, INTERVAL 45 DAY), 'Active'),
('Lisa', 'Anderson', 'lisa.anderson@icloud.com', '987 Cedar Ln', 'Aurora', 'IL', '60502', DATE_SUB(@current_date, INTERVAL 70 DAY), 'Suspended'),
('David', 'Taylor', 'david.taylor@comcast.net', '147 Birch Way', 'Joliet', 'IL', '60431', DATE_SUB(@current_date, INTERVAL 80 DAY), 'Active'),
('Jennifer', 'Martinez', 'jennifer.martinez@verizon.net', '258 Walnut St', 'Elgin', 'IL', '60120', DATE_SUB(@current_date, INTERVAL 35 DAY), 'Active'),
('William', 'Garcia', 'william.garcia@att.net', '369 Spruce Ave', 'Waukegan', 'IL', '60085', DATE_SUB(@current_date, INTERVAL 60 DAY), 'Active'),
('Amanda', 'Rodriguez', 'amanda.rodriguez@protonmail.com', '741 Ash Blvd', 'Schaumburg', 'IL', '60173', DATE_SUB(@current_date, INTERVAL 90 DAY), 'Active');

-- Insert Customer Payment Methods
INSERT INTO CustomerPaymentMethods (CustomerID, MethodID, PaymentMethodDetails, IsDefault, Status, ExpiryDate, CreatedDate) VALUES
-- John Smith - Credit Card primary, Bank Account backup
(1, 1, 'Visa ending in 1234', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 24 MONTH), DATE_SUB(@current_date, INTERVAL 75 DAY)),
(1, 3, 'Account ending in 5678', FALSE, 'Active', NULL, DATE_SUB(@current_date, INTERVAL 70 DAY)),
-- Sarah Johnson - Debit Card only
(2, 2, 'Debit ending in 2345', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 18 MONTH), DATE_SUB(@current_date, INTERVAL 65 DAY)),
-- Michael Brown - Multiple cards
(3, 1, 'Mastercard ending in 3456', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 30 MONTH), DATE_SUB(@current_date, INTERVAL 85 DAY)),
(3, 1, 'Amex ending in 4567', FALSE, 'Active', DATE_ADD(@current_date, INTERVAL 12 MONTH), DATE_SUB(@current_date, INTERVAL 60 DAY)),
-- Emily Davis - Bank Account
(4, 3, 'Account ending in 6789', TRUE, 'Active', NULL, DATE_SUB(@current_date, INTERVAL 55 DAY)),
-- Robert Wilson - Credit Card
(5, 1, 'Visa ending in 7890', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 20 MONTH), DATE_SUB(@current_date, INTERVAL 45 DAY)),
-- Lisa Anderson - Expired card (suspended account)
(6, 1, 'Visa ending in 8901', TRUE, 'Expired', DATE_SUB(@current_date, INTERVAL 2 MONTH), DATE_SUB(@current_date, INTERVAL 70 DAY)),
-- David Taylor - Credit Card
(7, 1, 'Mastercard ending in 9012', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 14 MONTH), DATE_SUB(@current_date, INTERVAL 80 DAY)),
-- Jennifer Martinez - Debit Card
(8, 2, 'Debit ending in 0123', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 22 MONTH), DATE_SUB(@current_date, INTERVAL 35 DAY)),
-- William Garcia - Bank Account
(9, 3, 'Account ending in 1234', TRUE, 'Active', NULL, DATE_SUB(@current_date, INTERVAL 60 DAY)),
-- Amanda Rodriguez - Credit Card
(10, 1, 'Visa ending in 2345', TRUE, 'Active', DATE_ADD(@current_date, INTERVAL 26 MONTH), DATE_SUB(@current_date, INTERVAL 90 DAY));
-- Insert Customer Subscriptions (diverse combinations) - activated over past 3 months
INSERT INTO CustomerSubscriptions (CustomerID, PlanID, PhoneNumber, IMEI, ActivationDate, RenewalDate, Status, MonthlyDataUsage, MonthlyMinutesUsed, MonthlyTextsUsed, DataWarningThreshold, AutoRenew, Notes, CreatedDate) VALUES
-- John Smith - 2 lines (Unlimited Plus + Standard)
(1, 3, '555-1001', '123456789012345', DATE_SUB(@current_date, INTERVAL 75 DAY), DATE_ADD(@current_date, INTERVAL 15 DAY), 'Active', 25.0, 1200, 850, 80, TRUE, 'Primary line - heavy data user', DATE_ADD(@current_date, INTERVAL -22 MONTH)),
(1, 2, '555-1002', '123456789012346', DATE_SUB(@current_date, INTERVAL 65 DAY), DATE_ADD(@current_date, INTERVAL 25 DAY), 'Active', 8.0, 450, 320, 90, TRUE, 'Secondary line for spouse', DATE_ADD(@current_date, INTERVAL -22 MONTH)),
-- Sarah Johnson - 1 line (Basic plan)
(2, 1, '555-2001', '234567890123456', DATE_SUB(@current_date, INTERVAL 65 DAY), DATE_ADD(@current_date, INTERVAL 25 DAY), 'Active', 3.0, 680, 1200, 85, TRUE, 'Light user, mostly texts', DATE_ADD(@current_date, INTERVAL -6 MONTH)),
-- Michael Brown - 3 lines (Family Basic) - long-term customer
(3, 4, '555-3001', '345678901234567', DATE_SUB(@current_date, INTERVAL 85 DAY), DATE_ADD(@current_date, INTERVAL 5 DAY), 'Active', 17.6, 890, 650, 75, TRUE, 'Family plan - main line', DATE_ADD(@current_date, INTERVAL -5 YEAR)),
(3, 4, '555-3002', '345678901234568', DATE_SUB(@current_date, INTERVAL 85 DAY), DATE_ADD(@current_date, INTERVAL 5 DAY), 'Active', 12.0, 320, 890, 80, TRUE, 'Teen daughter line', DATE_ADD(@current_date, INTERVAL -5 YEAR)),
(3, 4, '555-3003', '345678901234569', DATE_SUB(@current_date, INTERVAL 85 DAY), DATE_ADD(@current_date, INTERVAL 5 DAY), 'Active', 5.0, 150, 200, 90, TRUE, 'Backup/emergency line', DATE_ADD(@current_date, INTERVAL -5 YEAR)),
-- Emily Davis - 1 line (Business Pro)
(4, 5, '555-4001', '456789012345678', DATE_SUB(@current_date, INTERVAL 55 DAY), DATE_ADD(@current_date, INTERVAL 35 DAY), 'Active', 45.0, 2100, 450, 70, TRUE, 'Business user - high usage', DATE_ADD(@current_date, INTERVAL -10 MONTH)),
-- Robert Wilson - 1 line (Senior Plan)
(5, 6, '555-5001', '567890123456789', DATE_SUB(@current_date, INTERVAL 45 DAY), DATE_ADD(@current_date, INTERVAL 45 DAY), 'Active', 1.0, 200, 150, 95, TRUE, 'Senior customer - minimal usage', DATE_ADD(@current_date, INTERVAL -9 MONTH)),
-- Lisa Anderson - 1 line (Suspended)
(6, 2, '555-6001', '678901234567890', DATE_SUB(@current_date, INTERVAL 70 DAY), DATE_ADD(@current_date, INTERVAL 20 DAY), 'Suspended', 0.0, 0, 0, 80, FALSE, 'Suspended for non-payment', DATE_ADD(@current_date, INTERVAL -2 MONTH)),
-- David Taylor - 2 lines (Unlimited Plus)
(7, 3, '555-7001', '789012345678901', DATE_SUB(@current_date, INTERVAL 80 DAY), DATE_ADD(@current_date, INTERVAL 10 DAY), 'Active', 35.0, 1800, 920, 75, TRUE, 'Power user - streaming', DATE_ADD(@current_date, INTERVAL -19 MONTH)),
(7, 3, '555-7002', '789012345678902', DATE_SUB(@current_date, INTERVAL 60 DAY), DATE_ADD(@current_date, INTERVAL 30 DAY), 'Active', 28.0, 1200, 680, 80, TRUE, 'Work phone', DATE_ADD(@current_date, INTERVAL -19 MONTH)),
-- Jennifer Martinez - 1 line (Standard)
(8, 2, '555-8001', '890123456789012', DATE_SUB(@current_date, INTERVAL 35 DAY), DATE_ADD(@current_date, INTERVAL 55 DAY), 'Active', 11.0, 750, 1100, 85, TRUE, 'Moderate user', DATE_ADD(@current_date, INTERVAL -3 MONTH)),
-- William Garcia - 1 line (Basic)
(9, 1, '555-9001', '901234567890123', DATE_SUB(@current_date, INTERVAL 60 DAY), DATE_ADD(@current_date, INTERVAL 30 DAY), 'Active', 4.25, 420, 680, 90, TRUE, 'Budget conscious customer', DATE_ADD(@current_date, INTERVAL -5 MONTH)),
-- Amanda Rodriguez - 2 lines (Business Pro + Basic)
(10, 5, '555-1101', '012345678901234', DATE_SUB(@current_date, INTERVAL 90 DAY), @current_date, 'Active', 38.0, 1950, 520, 70, TRUE, 'Business line', DATE_ADD(@current_date, INTERVAL -11 MONTH)),
(10, 1, '555-1102', '012345678901235', DATE_SUB(@current_date, INTERVAL 75 DAY), DATE_ADD(@current_date, INTERVAL 15 DAY), 'Active', 2.0, 180, 450, 95, TRUE, 'Personal backup line', DATE_ADD(@current_date, INTERVAL -8 MONTH));

-- Insert Subscription Add-Ons (various combinations) - activated within past 3 months
INSERT INTO SubscriptionAddOns (SubscriptionID, AddOnID, ActivationDate, Status) VALUES
-- John Smith's lines
(1, 1, DATE_SUB(@current_date, INTERVAL 75 DAY), 'Active'),  -- Device Insurance on main line
(1, 2, DATE_SUB(@current_date, INTERVAL 60 DAY), 'Active'),  -- International Roaming
(1, 5, DATE_SUB(@current_date, INTERVAL 75 DAY), 'Active'),  -- Mobile Hotspot
(2, 1, DATE_SUB(@current_date, INTERVAL 65 DAY), 'Active'),  -- Device Insurance on second line
-- Michael Brown's family lines
(4, 1, DATE_SUB(@current_date, INTERVAL 85 DAY), 'Active'),  -- Device Insurance on main
(5, 7, DATE_SUB(@current_date, INTERVAL 70 DAY), 'Active'),  -- Caller ID Plus on teen line
(6, 1, DATE_SUB(@current_date, INTERVAL 85 DAY), 'Suspended'), -- Insurance suspended on backup line
-- Emily Davis business line
(7, 1, DATE_SUB(@current_date, INTERVAL 55 DAY), 'Active'),  -- Device Insurance
(7, 4, DATE_SUB(@current_date, INTERVAL 55 DAY), 'Active'),  -- Premium Support
(7, 5, DATE_SUB(@current_date, INTERVAL 55 DAY), 'Active'),  -- Mobile Hotspot
(7, 6, DATE_SUB(@current_date, INTERVAL 45 DAY), 'Active'),  -- Cloud Storage
-- David Taylor's lines
(10, 1, DATE_SUB(@current_date, INTERVAL 80 DAY), 'Active'),  -- Device Insurance main
(10, 2, DATE_SUB(@current_date, INTERVAL 50 DAY), 'Active'),  -- International Roaming
(10, 6, DATE_SUB(@current_date, INTERVAL 80 DAY), 'Active'),  -- Cloud Storage
(11, 1, DATE_SUB(@current_date, INTERVAL 60 DAY), 'Active'),  -- Device Insurance work phone
-- Jennifer Martinez
(12, 3, DATE_SUB(@current_date, INTERVAL 20 DAY), 'Active'), -- Extra 5GB Data
(12, 7, DATE_SUB(@current_date, INTERVAL 35 DAY), 'Active'), -- Caller ID Plus
-- Amanda Rodriguez business line
(14, 1, DATE_SUB(@current_date, INTERVAL 90 DAY), 'Active'), -- Device Insurance
(14, 4, DATE_SUB(@current_date, INTERVAL 90 DAY), 'Active'), -- Premium Support
(14, 5, DATE_SUB(@current_date, INTERVAL 90 DAY), 'Active'); -- Mobile Hotspot

-- Insert Customer Discounts
INSERT INTO CustomerDiscounts (CustomerID, DiscountID, AppliedDate, ExpiryDate, Status) VALUES
-- New customer promos (first 3 months)
(2, 1, DATE_SUB(@current_date, INTERVAL 65 DAY), DATE_SUB(@current_date, INTERVAL 5 DAY), 'Used'),    -- Sarah's new customer promo (expired)
(5, 1, DATE_SUB(@current_date, INTERVAL 45 DAY), DATE_ADD(@current_date, INTERVAL 45 DAY), 'Active'),    -- Robert's new customer promo (still active)
(8, 1, DATE_SUB(@current_date, INTERVAL 35 DAY), DATE_ADD(@current_date, INTERVAL 55 DAY), 'Active'),    -- Jennifer's new customer promo (still active)
-- Senior discount
(5, 2, DATE_SUB(@current_date, INTERVAL 45 DAY), NULL, 'Active'),          -- Robert gets senior discount
-- Military discount
(4, 3, DATE_SUB(@current_date, INTERVAL 55 DAY), NULL, 'Active'),          -- Emily gets military discount
(7, 3, DATE_SUB(@current_date, INTERVAL 80 DAY), NULL, 'Active'),          -- David gets military discount
-- Family bundle discount
(3, 4, DATE_SUB(@current_date, INTERVAL 85 DAY), DATE_ADD(@current_date, INTERVAL 6 MONTH), 'Active'),  -- Michael's family gets bundle discount
-- Loyalty discount (long-term customer)
(3, 5, DATE_SUB(@current_date, INTERVAL 30 DAY), NULL, 'Active');          -- Michael gets loyalty discount

-- Insert current month invoices (latest billing cycle)
INSERT INTO Invoices (CustomerID, InvoiceDate, DueDate, BillingPeriodStart, BillingPeriodEnd, SubtotalAmount, TaxAmount, DiscountAmount, TotalAmount, Status) VALUES
-- John Smith - 2 lines + add-ons
(1, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 130.00, 10.40, 0.00, 140.40, 'Sent'),
-- Sarah Johnson - Basic plan (paid)
(2, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 40.00, 3.20, 0.00, 43.20, 'Paid'),
-- Michael Brown - Family plan with discounts
(3, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 120.00, 9.60, 32.00, 97.60, 'Paid'),
-- Emily Davis - Business plan with military discount
(4, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 95.00, 7.60, 14.25, 88.35, 'Sent'),
-- Robert Wilson - Senior plan with discounts
(5, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 25.00, 2.00, 10.00, 17.00, 'Paid'),
-- Lisa Anderson - Suspended (no invoice)
-- (6, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 150.00, 12.00, 22.50, 139.50, 'Overdue'),
-- David Taylor - 2 Unlimited lines with military discount
(7, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 150.00, 12.00, 22.50, 139.50, 'Overdue'),
-- Jennifer Martinez - Standard + add-ons
(8, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 68.00, 5.44, 0.00, 73.44, 'Sent'),
-- William Garcia - Basic plan
(9, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 40.00, 3.20, 0.00, 43.20, 'Paid'),
-- Amanda Rodriguez - Business + Basic lines
(10, @current_month_start, DATE_ADD(@current_month_start, INTERVAL 25 DAY), @current_month_start, @current_month_end, 135.00, 10.80, 0.00, 145.80, 'Sent');

-- Insert Invoice Line Items for the invoices above
INSERT INTO InvoiceLineItems (InvoiceID, SubscriptionID, AddOnID, Description, Quantity, UnitPrice, LineTotal, ChargeType) VALUES
-- Invoice 1: John Smith (InvoiceID 1)
(1, 1, NULL, 'Unlimited Plus Plan - Line 1', 1, 75.00, 75.00, 'Base Plan'),
(1, 2, NULL, 'Standard Plan - Line 2', 1, 55.00, 55.00, 'Base Plan'),
(1, 1, 1, 'Device Insurance - Line 1', 1, 12.00, 12.00, 'Add-On'),
(1, 1, 2, 'International Roaming - Line 1', 1, 15.00, 15.00, 'Add-On'),
(1, 1, 5, 'Mobile Hotspot - Line 1', 1, 5.00, 5.00, 'Add-On'),
(1, 2, 1, 'Device Insurance - Line 2', 1, 12.00, 12.00, 'Add-On'),
(1, 1, NULL, 'Data Overage (10GB @ $2/GB)', 1, 20.00, 20.00, 'Overage'),
-- Invoice 2: Sarah Johnson (InvoiceID 2)
(2, 3, NULL, 'Basic Plan', 1, 40.00, 40.00, 'Base Plan'),
-- Invoice 3: Michael Brown (InvoiceID 3) - Family plan with discounts
(3, 4, NULL, 'Family Basic Plan - Line 1', 1, 120.00, 120.00, 'Base Plan'),
(3, 4, 1, 'Device Insurance - Line 1', 1, 12.00, 12.00, 'Add-On'),
(3, 5, 7, 'Caller ID Plus - Line 2', 1, 3.00, 3.00, 'Add-On'),
-- Invoice 4: Emily Davis (InvoiceID 4) - Business plan
(4, 7, NULL, 'Business Pro Plan', 1, 95.00, 95.00, 'Base Plan'),
(4, 7, 1, 'Device Insurance', 1, 12.00, 12.00, 'Add-On'),
(4, 7, 4, 'Premium Support', 1, 8.00, 8.00, 'Add-On'),
(4, 7, 5, 'Mobile Hotspot', 1, 5.00, 5.00, 'Add-On'),
(4, 7, 6, 'Cloud Storage 50GB', 1, 6.00, 6.00, 'Add-On'),
-- Invoice 5: Robert Wilson (InvoiceID 5) - Senior plan
(5, 8, NULL, 'Senior Plan', 1, 25.00, 25.00, 'Base Plan'),
-- Invoice 6: David Taylor (InvoiceID 7) - 2 Unlimited lines
(7, 10, NULL, 'Unlimited Plus Plan - Line 1', 1, 75.00, 75.00, 'Base Plan'),
(7, 11, NULL, 'Unlimited Plus Plan - Line 2', 1, 75.00, 75.00, 'Base Plan'),
(7, 10, 1, 'Device Insurance - Line 1', 1, 12.00, 12.00, 'Add-On'),
(7, 10, 2, 'International Roaming - Line 1', 1, 15.00, 15.00, 'Add-On'),
(7, 10, 6, 'Cloud Storage - Line 1', 1, 6.00, 6.00, 'Add-On'),
(7, 11, 1, 'Device Insurance - Line 2', 1, 12.00, 12.00, 'Add-On'),
-- Invoice 7: Jennifer Martinez (InvoiceID 8)
(8, 12, NULL, 'Standard Plan', 1, 55.00, 55.00, 'Base Plan'),
(8, 12, 3, 'Extra 5GB Data', 1, 10.00, 10.00, 'Add-On'),
(8, 12, 7, 'Caller ID Plus', 1, 3.00, 3.00, 'Add-On'),
-- Invoice 8: William Garcia (InvoiceID 9)
(9, 13, NULL, 'Basic Plan', 1, 40.00, 40.00, 'Base Plan'),
-- Invoice 9: Amanda Rodriguez (InvoiceID 10)
(10, 14, NULL, 'Business Pro Plan - Line 1', 1, 95.00, 95.00, 'Base Plan'),
(10, 15, NULL, 'Basic Plan - Line 2', 1, 40.00, 40.00, 'Base Plan'),
(10, 14, 1, 'Device Insurance - Line 1', 1, 12.00, 12.00, 'Add-On'),
(10, 14, 4, 'Premium Support - Line 1', 1, 8.00, 8.00, 'Add-On'),
(10, 14, 5, 'Mobile Hotspot - Line 1', 1, 5.00, 5.00, 'Add-On');

-- Insert Overage Charges for current month
INSERT INTO OverageCharges (SubscriptionID, BillingMonth, OverageType, OverageAmount, ChargePerUnit, TotalCharge, InvoiceLineItemID) VALUES
-- John Smith's main line exceeded data
(1, @current_month_start, 'Data', 10.00, 2.00, 20.00, 7),
-- Emily Davis exceeded international minutes
(7, @current_month_start, 'International', 150.00, 0.25, 37.50, NULL);

-- Insert sample payments for current month
INSERT INTO Payments (InvoiceID, CustomerID, PaymentAmount, PaymentDate, PaymentMethod, TransactionID, Status, Notes) VALUES
-- Paid invoices
(2, 2, 43.20, DATE_ADD(@current_month_start, INTERVAL 15 DAY), 2, CONCAT('TXN-', DATE_FORMAT(@current_date, '%Y%m%d'), '-001'), 'Completed', 'Auto-pay debit card'),
(3, 3, 97.60, DATE_ADD(@current_month_start, INTERVAL 12 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@current_date, '%Y%m%d'), '-002'), 'Completed', 'Credit card payment'),
(5, 5, 17.00, DATE_ADD(@current_month_start, INTERVAL 18 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@current_date, '%Y%m%d'), '-003'), 'Completed', 'Senior customer - on time'),
(9, 9, 43.20, DATE_ADD(@current_month_start, INTERVAL 20 DAY), 3, CONCAT('TXN-', DATE_FORMAT(@current_date, '%Y%m%d'), '-004'), 'Completed', 'Bank transfer'),
-- Partial payment
(7, 7, 100.00, DATE_SUB(@current_date, INTERVAL 2 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@current_date, '%Y%m%d'), '-005'), 'Completed', 'Partial payment - customer called about financial hardship');

-- Insert Audit Log entries (activities over past 3 months)
INSERT INTO AuditLog (CustomerID, SubscriptionID, ActionType, OldValue, NewValue, ChangedBy, Reason, LogTimestamp) VALUES
-- Recent customer service activities
(1, 1, 'Add-On Added', NULL, 'International Roaming', 'support_sarah', 'Customer traveling to Europe next month', DATE_SUB(@current_date, INTERVAL 60 DAY)),
(6, NULL, 'Account Suspended', 'Active', 'Suspended', 'support_manager', 'Non-payment - 45 days overdue', DATE_SUB(@current_date, INTERVAL 15 DAY)),
(3, 6, 'Add-On Suspended', 'Active', 'Suspended', 'support_bob', 'Customer requested temporary suspension of insurance', DATE_SUB(@current_date, INTERVAL 30 DAY)),
(7, 10, 'Plan Changed', 'Standard', 'Unlimited Plus', 'support_mike', 'Customer upgrade due to high data usage', DATE_SUB(@current_date, INTERVAL 70 DAY)),
(10, 14, 'Add-On Added', NULL, 'Premium Support', 'support_sarah', 'Business customer requested priority support', DATE_SUB(@current_date, INTERVAL 90 DAY)),
(5, 8, 'Discount Applied', NULL, 'Senior Discount', 'support_jenny', 'Customer provided proof of age - 67 years old', DATE_SUB(@current_date, INTERVAL 45 DAY)),
(2, 3, 'Data Warning Updated', '85', '90', 'support_bob', 'Customer requested higher warning threshold', DATE_SUB(@current_date, INTERVAL 25 DAY)),
(4, 7, 'Usage Alert', NULL, 'International overage detected', 'system_auto', 'Automated alert - customer exceeded 500 international minutes', DATE_SUB(@current_date, INTERVAL 10 DAY)),
(7, NULL, 'Payment Plan Setup', NULL, 'Payment arrangement created', 'support_manager', 'Customer experiencing financial hardship - arranged payment plan', DATE_SUB(@current_date, INTERVAL 5 DAY)),
(8, 12, 'Add-On Added', NULL, 'Extra 5GB Data', 'support_sarah', 'Customer consistently hitting data limit', DATE_SUB(@current_date, INTERVAL 20 DAY));

-- Additional sample data for testing edge cases
-- Insert overage charges for previous months
INSERT INTO OverageCharges (SubscriptionID, BillingMonth, OverageType, OverageAmount, ChargePerUnit, TotalCharge) VALUES
(12, @last_month_start, 'Data', 5.00, 2.00, 10.00),
(12, @current_month_start, 'Minutes', 200.00, 0.15, 30.00),
(7, @last_month_start, 'International', 75.00, 0.25, 18.75);

-- Insert historical invoices (last month and two months ago)
INSERT INTO Invoices (CustomerID, InvoiceDate, DueDate, BillingPeriodStart, BillingPeriodEnd, SubtotalAmount, TaxAmount, DiscountAmount, TotalAmount, Status) VALUES
-- Last month invoices
(1, @last_month_start, DATE_ADD(@last_month_start, INTERVAL 25 DAY), @last_month_start, @last_month_end, 120.00, 9.60, 0.00, 129.60, 'Paid'),
(3, @last_month_start, DATE_ADD(@last_month_start, INTERVAL 25 DAY), @last_month_start, @last_month_end, 120.00, 9.60, 32.00, 97.60, 'Paid'),
(7, @last_month_start, DATE_ADD(@last_month_start, INTERVAL 25 DAY), @last_month_start, @last_month_end, 140.00, 11.20, 21.00, 130.20, 'Paid'),
-- Two months ago invoices
(2, @two_months_ago, DATE_ADD(@two_months_ago, INTERVAL 25 DAY), @two_months_ago, @two_months_ago_end, 40.00, 3.20, 8.00, 35.20, 'Paid'),
(4, @two_months_ago, DATE_ADD(@two_months_ago, INTERVAL 25 DAY), @two_months_ago, @two_months_ago_end, 95.00, 7.60, 14.25, 88.35, 'Paid');

-- Insert payments for historical invoices
INSERT INTO Payments (InvoiceID, CustomerID, PaymentAmount, PaymentDate, PaymentMethod, TransactionID, Status) VALUES
-- Last month payments
(11, 1, 129.60, DATE_ADD(@last_month_start, INTERVAL 20 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@last_month_start, '%Y%m%d'), '-001'), 'Completed'),
(12, 3, 97.60, DATE_ADD(@last_month_start, INTERVAL 18 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@last_month_start, '%Y%m%d'), '-002'), 'Completed'),
(13, 7, 130.20, DATE_ADD(@last_month_start, INTERVAL 22 DAY), 1, CONCAT('TXN-', DATE_FORMAT(@last_month_start, '%Y%m%d'), '-003'), 'Completed'),
-- Two months ago payments
(14, 2, 35.20, DATE_ADD(@two_months_ago, INTERVAL 15 DAY), 2, CONCAT('TXN-', DATE_FORMAT(@two_months_ago, '%Y%m%d'), '-004'), 'Completed'),
(15, 4, 88.35, DATE_ADD(@two_months_ago, INTERVAL 20 DAY), 3, CONCAT('TXN-', DATE_FORMAT(@two_months_ago, '%Y%m%d'), '-005'), 'Completed');

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- Verify the data was inserted correctly
-- SELECT 'Data insertion completed successfully' as Status;
-- SELECT COUNT(*) as CustomerCount FROM Customers;
-- SELECT COUNT(*) as SubscriptionCount FROM CustomerSubscriptions;
-- SELECT COUNT(*) as InvoiceCount FROM Invoices;
-- SELECT COUNT(*) as PaymentCount FROM Payments;