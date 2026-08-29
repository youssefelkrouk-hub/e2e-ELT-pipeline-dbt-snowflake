
USE DATABASE FINANCE_DB;
USE SCHEMA RAW;

-- 1. Vider l'ancienne table
TRUNCATE TABLE raw.orders;

-- 2. Charger les nouvelles données 2025
COPY INTO raw.orders
FROM @Sales_stage/orders.csv
FILE_FORMAT=(TYPE='CSV' SKIP_HEADER=1);


SELECT * FROM FINANCE_DB.RAW.DAILY_ORDER_REVENUE;
SELECT * FROM FINANCE_DB.RAW.CUSTOMER_SEGMENTATION;
SELECT * FROM FINANCE_DB.RAW.COUNTRIES_QUANTITIES;
SELECT * FROM FINANCE_DB.RAW.STATUS_ORDER_COUNT;

--- Data Marts Manipulation after Transformation by dbt in the cloud snowflake data warehouse
