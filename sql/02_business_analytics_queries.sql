-- ============================================================================
-- 02_business_analytics_queries.sql
-- Production PostgreSQL Analytical Queries for PropTech Business Intelligence
-- Synthetic Dataset: CampusStay Student Housing Marketplace Simulation
-- Reconciled 100% (£0.00 variance) with Python/Pandas & data_quality_audit_report.json
-- ============================================================================

-- ============================================================================
-- QUERY 1A: Executive Revenue, Cost & Net Profit Summary by City (Confirmed Bookings)
-- Verified Totals: 945 Bookings | GBV: £12,066,564.00 | Revenue: £981,618.49 | Net Profit: £741,926.28
-- ============================================================================
SELECT
    p.city,
    COUNT(b.booking_id) AS confirmed_bookings,
    ROUND(AVG(b.lease_weeks), 1) AS avg_lease_weeks,
    ROUND(SUM(b.gross_booking_value_gbp), 2) AS total_gbv_gbp,
    ROUND(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 2) AS platform_revenue_gbp,
    ROUND(SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp), 2) AS total_direct_cost_gbp,
    ROUND(
        SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
        - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp),
        2
    ) AS net_profit_gbp,
    ROUND(
        (
            SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
            - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp)
        ) * 100.0
        / NULLIF(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 0),
        2
    ) AS net_profit_margin_pct
FROM bookings b
INNER JOIN properties p
    ON b.property_id = p.property_id
WHERE b.booking_status = 'Confirmed'
GROUP BY p.city
ORDER BY platform_revenue_gbp DESC;


-- ============================================================================
-- QUERY 1B: Revenue & Unit Economics Breakdown by Room Tier (Including Sunk CPA)
-- Verified Totals: Recognized Revenue: £981,618.49 | Fully Loaded Net Profit: £730,742.63
-- ============================================================================
SELECT
    p.room_tier,
    COUNT(b.booking_id) AS total_bookings,
    COUNT(b.booking_id) FILTER (WHERE b.booking_status = 'Confirmed') AS confirmed_bookings,
    ROUND(
        COUNT(b.booking_id) FILTER (WHERE b.booking_status = 'Cancelled') * 100.0 / COUNT(b.booking_id),
        2
    ) AS cancellation_rate_pct,
    ROUND(
        SUM(CASE WHEN b.booking_status = 'Confirmed' THEN b.gross_booking_value_gbp ELSE 0 END),
        2
    ) AS confirmed_gbv_gbp,
    ROUND(
        SUM(
            CASE
                WHEN b.booking_status = 'Confirmed'
                THEN ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)
                ELSE 0
            END
        ),
        2
    ) AS recognized_revenue_gbp,
    ROUND(
        SUM(
            CASE
                WHEN b.booking_status = 'Confirmed'
                THEN b.marketing_cpa_gbp + p.ops_servicing_cost_gbp
                ELSE b.marketing_cpa_gbp
            END
        ),
        2
    ) AS fully_loaded_cost_gbp,
    ROUND(
        SUM(
            CASE
                WHEN b.booking_status = 'Confirmed'
                THEN ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)
                     - (b.marketing_cpa_gbp + p.ops_servicing_cost_gbp)
                ELSE -b.marketing_cpa_gbp
            END
        ),
        2
    ) AS fully_loaded_net_profit_gbp
FROM bookings b
INNER JOIN properties p
    ON b.property_id = p.property_id
GROUP BY p.room_tier
ORDER BY recognized_revenue_gbp DESC;


-- ============================================================================
-- QUERY 2A: Student Customer Segmentation by Cohort & Study Level
-- ============================================================================
SELECT
    s.student_cohort,
    s.study_level,
    COUNT(DISTINCT s.student_id) AS active_students,
    COUNT(b.booking_id) AS confirmed_bookings,
    ROUND(AVG(b.lease_weeks), 1) AS avg_lease_weeks,
    ROUND(AVG(b.gross_booking_value_gbp), 2) AS avg_booking_gbv_gbp,
    ROUND(SUM(b.gross_booking_value_gbp), 2) AS segment_gbv_gbp,
    ROUND(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 2) AS segment_revenue_gbp,
    ROUND(
        SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
        - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp),
        2
    ) AS segment_net_profit_gbp
FROM bookings b
INNER JOIN students s
    ON b.student_id = s.student_id
INNER JOIN properties p
    ON b.property_id = p.property_id
WHERE b.booking_status = 'Confirmed'
GROUP BY s.student_cohort, s.study_level
ORDER BY segment_revenue_gbp DESC;


-- ============================================================================
-- QUERY 2B: Student Value Tier Segmentation (Monetary LTV Tiers using CTEs)
-- ============================================================================
WITH student_monetary AS (
    SELECT
        s.student_id,
        s.student_cohort,
        s.nationality,
        s.acquisition_channel,
        COUNT(b.booking_id) AS total_confirmed_bookings,
        SUM(b.gross_booking_value_gbp) AS lifetime_gbv_gbp,
        SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)) AS lifetime_revenue_gbp,
        SUM(
            ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)
            - (b.marketing_cpa_gbp + p.ops_servicing_cost_gbp)
        ) AS lifetime_net_profit_gbp
    FROM students s
    INNER JOIN bookings b
        ON s.student_id = b.student_id
    INNER JOIN properties p
        ON b.property_id = p.property_id
    WHERE b.booking_status = 'Confirmed'
    GROUP BY s.student_id, s.student_cohort, s.nationality, s.acquisition_channel
),
tiered_students AS (
    SELECT
        *,
        CASE
            WHEN lifetime_revenue_gbp >= 1800 THEN '1 - VIP Platinum (>= £1,800 Rev)'
            WHEN lifetime_revenue_gbp >= 1100 THEN '2 - High-Value Gold (£1,100 - £1,799)'
            WHEN lifetime_revenue_gbp >= 700  THEN '3 - Core Silver (£700 - £1,099)'
            ELSE '4 - Short-Stay Bronze (< £700)'
        END AS customer_value_tier
    FROM student_monetary
)
SELECT
    customer_value_tier,
    COUNT(student_id) AS student_count,
    ROUND(COUNT(student_id) * 100.0 / SUM(COUNT(student_id)) OVER (), 2) AS share_of_students_pct,
    ROUND(AVG(lifetime_gbv_gbp), 2) AS avg_student_gbv_gbp,
    ROUND(SUM(lifetime_revenue_gbp), 2) AS tier_total_revenue_gbp,
    ROUND(SUM(lifetime_revenue_gbp) * 100.0 / SUM(SUM(lifetime_revenue_gbp)) OVER (), 2) AS share_of_revenue_pct,
    ROUND(SUM(lifetime_net_profit_gbp), 2) AS tier_net_profit_gbp
FROM tiered_students
GROUP BY customer_value_tier
ORDER BY customer_value_tier;


-- ============================================================================
-- QUERY 3: Monthly Revenue, GBV & Profit Trends (MoM Growth % & 3-Month Rolling Avg)
-- ============================================================================
WITH monthly_kpis AS (
    SELECT
        TO_CHAR(DATE_TRUNC('month', b.booking_date), 'YYYY-MM') AS booking_month,
        COUNT(b.booking_id) AS confirmed_bookings,
        ROUND(SUM(b.gross_booking_value_gbp), 2) AS monthly_gbv_gbp,
        ROUND(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 2) AS monthly_revenue_gbp,
        ROUND(
            SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
            - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp),
            2
        ) AS monthly_net_profit_gbp
    FROM bookings b
    INNER JOIN properties p
        ON b.property_id = p.property_id
    WHERE b.booking_status = 'Confirmed'
    GROUP BY DATE_TRUNC('month', b.booking_date)
)
SELECT
    booking_month,
    confirmed_bookings,
    monthly_gbv_gbp,
    monthly_revenue_gbp,
    monthly_net_profit_gbp,
    LAG(monthly_revenue_gbp) OVER (ORDER BY booking_month) AS prev_month_revenue_gbp,
    ROUND(
        (monthly_revenue_gbp - LAG(monthly_revenue_gbp) OVER (ORDER BY booking_month)) * 100.0
        / NULLIF(LAG(monthly_revenue_gbp) OVER (ORDER BY booking_month), 0),
        2
    ) AS mom_revenue_growth_pct,
    ROUND(
        AVG(monthly_revenue_gbp) OVER (
            ORDER BY booking_month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_3m_avg_revenue_gbp
FROM monthly_kpis
ORDER BY booking_month;


-- ============================================================================
-- QUERY 4: Acquisition Channel Efficiency & ROI Scorecard
-- ============================================================================
SELECT
    s.acquisition_channel,
    COUNT(b.booking_id) AS total_bookings,
    COUNT(b.booking_id) FILTER (WHERE b.booking_status = 'Confirmed') AS confirmed_bookings,
    ROUND(SUM(b.marketing_cpa_gbp), 2) AS total_marketing_spend_gbp,
    ROUND(
        SUM(
            CASE
                WHEN b.booking_status = 'Confirmed'
                THEN ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)
                ELSE 0
            END
        ),
        2
    ) AS recognized_revenue_gbp,
    ROUND(
        SUM(
            CASE
                WHEN b.booking_status = 'Confirmed'
                THEN ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)
                ELSE 0
            END
        ) / NULLIF(SUM(b.marketing_cpa_gbp), 0),
        2
    ) AS revenue_to_cpa_roas_x
FROM bookings b
INNER JOIN students s
    ON b.student_id = s.student_id
INNER JOIN properties p
    ON b.property_id = p.property_id
GROUP BY s.acquisition_channel
ORDER BY recognized_revenue_gbp DESC;
