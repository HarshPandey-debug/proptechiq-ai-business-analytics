-- ============================================================================
-- 01_schema_and_load.sql
-- PostgreSQL 15+ DDL Schema & Data Load Script
-- Domain: Synthetic Student Housing / PropTech Marketplace (CampusStay Simulation)
-- ============================================================================

DROP TABLE IF EXISTS payment_installments CASCADE;
DROP TABLE IF EXISTS property_promotions CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS students CASCADE;
DROP TABLE IF EXISTS properties CASCADE;

-- 1. Dimension Table: properties (Simulated PBSA Residences)
CREATE TABLE properties (
    property_id               VARCHAR(20) PRIMARY KEY,
    property_name             VARCHAR(120) NOT NULL,
    city                      VARCHAR(60)  NOT NULL,
    university_corridor       VARCHAR(120) NOT NULL,
    room_tier                 VARCHAR(40)  NOT NULL,
    total_beds                INTEGER      NOT NULL CHECK (total_beds > 0),
    standard_weekly_rent_gbp  NUMERIC(10, 2) NOT NULL CHECK (standard_weekly_rent_gbp > 0),
    partner_commission_pct    NUMERIC(5, 2)  NOT NULL CHECK (partner_commission_pct BETWEEN 0 AND 100),
    ops_servicing_cost_gbp    NUMERIC(10, 2) NOT NULL CHECK (ops_servicing_cost_gbp >= 0)
);

-- 2. Dimension Table: students (Simulated Customer Profiles)
CREATE TABLE students (
    student_id           VARCHAR(20) PRIMARY KEY,
    full_name            VARCHAR(100) NOT NULL,
    email                VARCHAR(150) NOT NULL UNIQUE,
    nationality          VARCHAR(60)  NOT NULL,
    student_cohort       VARCHAR(30)  NOT NULL CHECK (student_cohort IN ('International', 'Domestic')),
    study_level          VARCHAR(50)  NOT NULL,
    acquisition_channel  VARCHAR(60)  NOT NULL,
    signup_date          DATE         NOT NULL
);

-- 3. Fact Table: bookings (1 row per lease booking)
CREATE TABLE bookings (
    booking_id               VARCHAR(25) PRIMARY KEY,
    student_id               VARCHAR(20) NOT NULL REFERENCES students(student_id),
    property_id              VARCHAR(20) NOT NULL REFERENCES properties(property_id),
    booking_date             DATE        NOT NULL,
    academic_intake          VARCHAR(30) NOT NULL,
    check_in_date            DATE        NOT NULL,
    lease_weeks              INTEGER     NOT NULL CHECK (lease_weeks > 0),
    weekly_rent_gbp          NUMERIC(10, 2) NOT NULL CHECK (weekly_rent_gbp > 0),
    gross_booking_value_gbp  NUMERIC(12, 2) NOT NULL CHECK (gross_booking_value_gbp > 0),
    marketing_cpa_gbp        NUMERIC(10, 2) NOT NULL CHECK (marketing_cpa_gbp >= 0),
    booking_status           VARCHAR(20) NOT NULL CHECK (booking_status IN ('Confirmed', 'Cancelled', 'Pending'))
);

-- 4. Fact Table: payment_installments (1-to-Many: 1 booking -> 1..4 installment payments)
-- IMPORTANT GRAIN NOTE: Joining `bookings` directly to `payment_installments` without
-- pre-aggregating `payment_installments` by `booking_id` causes a 1-to-many fan-out!
CREATE TABLE payment_installments (
    payment_id              VARCHAR(25) PRIMARY KEY,
    booking_id              VARCHAR(25) NOT NULL REFERENCES bookings(booking_id),
    installment_number      INTEGER     NOT NULL CHECK (installment_number BETWEEN 1 AND 12),
    payment_date            DATE        NOT NULL,
    installment_amount_gbp  NUMERIC(12, 2) NOT NULL CHECK (installment_amount_gbp >= 0),
    payment_method          VARCHAR(40) NOT NULL,
    payment_status          VARCHAR(20) NOT NULL CHECK (payment_status IN ('Paid', 'Refunded', 'Scheduled'))
);

-- 5. Bridge/Campaign Table: property_promotions (1-to-Many: 1 property -> 1..3 active campaigns)
CREATE TABLE property_promotions (
    promo_id            VARCHAR(20) PRIMARY KEY,
    property_id         VARCHAR(20) NOT NULL REFERENCES properties(property_id),
    campaign_name       VARCHAR(80) NOT NULL,
    promo_discount_gbp  NUMERIC(10, 2) NOT NULL CHECK (promo_discount_gbp >= 0),
    active_intake       VARCHAR(30) NOT NULL
);

CREATE INDEX idx_bookings_date_status ON bookings(booking_date, booking_status);
CREATE INDEX idx_bookings_property ON bookings(property_id);
CREATE INDEX idx_bookings_student ON bookings(student_id);
CREATE INDEX idx_payments_booking ON payment_installments(booking_id, payment_status);
CREATE INDEX idx_properties_city_tier ON properties(city, room_tier);
