-- ============================================================================
-- 03_ai_mistake_and_fix.sql
-- Documentation of Actual AI Mistake (1-to-Many SQL Join Fan-Out Trap) & Fix
-- Synthetic Dataset: CampusStay Student Housing Marketplace Simulation
-- ============================================================================
-- USER PROMPT GIVEN TO AI ASSISTANT:
-- "Calculate total confirmed Gross Booking Value, Platform Commission Revenue,
--  Net Profit, and Total Collected Installment Payments by City."
-- ============================================================================

-- ❌ 1. BROKEN AI-GENERATED SQL QUERY (DO NOT USE IN PRODUCTION)
-- Root Cause of AI Mistake:
--   1) Joined `bookings` (1 row per booking) directly to `payment_installments`
--      (1 to 4 rows per booking) AND `property_promotions` (1 to 3 rows per property)
--      in a single flat SELECT before aggregating!
--   2) Every multi-installment booking had its `gross_booking_value_gbp`,
--      `commission_revenue`, and `cost` multiplied by (num_installments * num_promotions).
--   3) Inflated total confirmed bookings from 945 to 5,625 (+495.24%) and overstated
--      Platform Commission Revenue from £981,618.49 to £5,677,352.25 (+478.37%).
SELECT
    p.city,
    COUNT(b.booking_id) AS ai_reported_bookings,
    ROUND(SUM(b.gross_booking_value_gbp), 2) AS ai_inflated_gbv_gbp,
    ROUND(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 2) AS ai_inflated_revenue_gbp,
    ROUND(
        SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
        - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp),
        2
    ) AS ai_inflated_net_profit_gbp,
    ROUND(SUM(pi.installment_amount_gbp), 2) AS ai_inflated_payments_collected_gbp
FROM bookings b
INNER JOIN properties p
    ON b.property_id = p.property_id
LEFT JOIN payment_installments pi
    ON b.booking_id = pi.booking_id
LEFT JOIN property_promotions pr
    ON p.property_id = pr.property_id
WHERE b.booking_status = 'Confirmed'
GROUP BY p.city
ORDER BY ai_inflated_revenue_gbp DESC;


-- ✅ 2. CORRECTED & VERIFIED SQL QUERY (PRE-AGGREGATED CTE AT BOOKING GRAIN)
-- Fix Applied:
--   1) Pre-aggregated `payment_installments` by `booking_id` inside a dedicated CTE
--      (`booking_payments`) so the join to `bookings` is strictly 1-to-1.
--   2) Removed the unnecessary flat join to `property_promotions` (or isolated it
--      into a property-grain CTE when promotional discounts are needed).
--   3) Verified £0.00 variance against independent Python/Pandas ground truth
--      and `data_quality_audit_report.json`.
WITH booking_payments AS (
    SELECT
        booking_id,
        COUNT(payment_id) AS installment_count,
        ROUND(SUM(installment_amount_gbp) FILTER (WHERE payment_status = 'Paid'), 2) AS collected_payments_gbp
    FROM payment_installments
    GROUP BY booking_id
)
SELECT
    p.city,
    COUNT(b.booking_id) AS verified_confirmed_bookings,
    ROUND(SUM(b.gross_booking_value_gbp), 2) AS verified_gbv_gbp,
    ROUND(SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2)), 2) AS verified_revenue_gbp,
    ROUND(
        SUM(ROUND(b.gross_booking_value_gbp * (p.partner_commission_pct / 100.0), 2))
        - SUM(b.marketing_cpa_gbp + p.ops_servicing_cost_gbp),
        2
    ) AS verified_net_profit_gbp,
    ROUND(SUM(COALESCE(bp.collected_payments_gbp, 0)), 2) AS verified_payments_collected_gbp
FROM bookings b
INNER JOIN properties p
    ON b.property_id = p.property_id
LEFT JOIN booking_payments bp
    ON b.booking_id = bp.booking_id
WHERE b.booking_status = 'Confirmed'
GROUP BY p.city
ORDER BY verified_revenue_gbp DESC;
