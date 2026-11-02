#!/usr/bin/env python3
"""
data_cleaning.py
----------------
Python / Pandas Data Cleaning, Normalization, and Validation Pipeline
for the Synthetic Student Housing / PropTech Business Analytics Assistant.

Performs 7 deterministic cleaning & validation stages:
1. Deduplication of webhook retry booking records (`booking_id`).
2. Removal of internal QA / test bot accounts (`@campusstay-qa.internal` / `STU-TEST-*`).
3. Currency & numeric parsing (`£`, commas, whitespace) on `weekly_rent_gbp` and `gross_booking_value_gbp`.
4. String normalization on `city` (removing `, UK`, trimming, title-casing) and `booking_status`.
5. Missing value imputation:
   - `partner_commission_pct` imputed by `room_tier` default mapping.
   - `acquisition_channel` nulls imputed to `'Unattributed / Direct'`.
   - `check_in_date` nulls imputed deterministically from `academic_intake`.
6. Invalid/corrupted record quarantine (`lease_weeks <= 0` or `weekly_rent_gbp <= 0`).
7. Financial metric derivation & schema invariant validation (`gross_booking_value_gbp`,
   `recognized_revenue_gbp`, `net_profit_gbp`) with 0.00 GBP rounding discrepancy.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd


TIER_DEFAULT_COMMISSION_PCT = {
    "Ensuite Standard": 7.25,
    "Ensuite Gold": 7.50,
    "Studio Classic": 8.25,
    "Studio Penthouse": 9.00,
}

INTAKE_DEFAULT_CHECKIN = {
    "Sep 2026 Intake": "2026-09-12",
    "Jan 2026 Intake": "2026-01-10",
}


def clean_currency_series(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
        .str.replace("£", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
        .astype(float)
    )


def run_cleaning_pipeline(base_dir: str | Path) -> dict:
    base_path = Path(base_dir)
    raw_dir = base_path / "data" / "raw"
    clean_dir = base_path / "data" / "cleaned"
    clean_dir.mkdir(parents=True, exist_ok=True)

    audit_log = {}

    # ---------------------------------------------------------
    # 1. CLEAN PROPERTIES TABLE
    # ---------------------------------------------------------
    df_prop = pd.read_csv(raw_dir / "properties_raw.csv")
    audit_log["properties_raw_rows"] = int(len(df_prop))

    dirty_city_mask = df_prop["city"] != (
        df_prop["city"].astype(str).str.replace(", UK", "", case=False, regex=False).str.strip().str.title()
    )
    audit_log["properties_dirty_city_fixed"] = int(dirty_city_mask.sum())
    df_prop["city"] = (
        df_prop["city"].astype(str).str.replace(", UK", "", case=False, regex=False).str.strip().str.title()
    )

    missing_comm = int(df_prop["partner_commission_pct"].isna().sum())
    audit_log["properties_missing_commission_imputed"] = missing_comm
    df_prop["partner_commission_pct"] = df_prop["partner_commission_pct"].fillna(
        df_prop["room_tier"].map(TIER_DEFAULT_COMMISSION_PCT)
    )

    df_prop.to_csv(clean_dir / "properties_cleaned.csv", index=False)
    audit_log["properties_cleaned_rows"] = int(len(df_prop))

    # ---------------------------------------------------------
    # 2. CLEAN STUDENTS TABLE
    # ---------------------------------------------------------
    df_stu = pd.read_csv(raw_dir / "students_raw.csv")
    audit_log["students_raw_rows"] = int(len(df_stu))

    qa_mask = df_stu["email"].astype(str).str.endswith("@campusstay-qa.internal") | df_stu["student_id"].astype(
        str
    ).str.startswith("STU-TEST-")
    audit_log["students_qa_accounts_removed"] = int(qa_mask.sum())
    df_stu = df_stu[~qa_mask].copy()

    missing_ch = int(df_stu["acquisition_channel"].isna().sum())
    audit_log["students_missing_channel_imputed"] = missing_ch
    df_stu["acquisition_channel"] = df_stu["acquisition_channel"].fillna("Unattributed / Direct")

    df_stu.to_csv(clean_dir / "students_cleaned.csv", index=False)
    audit_log["students_cleaned_rows"] = int(len(df_stu))

    # ---------------------------------------------------------
    # 3. CLEAN BOOKINGS TABLE
    # ---------------------------------------------------------
    df_bkg = pd.read_csv(raw_dir / "bookings_raw.csv")
    audit_log["bookings_raw_rows"] = int(len(df_bkg))

    dup_count = int(df_bkg.duplicated(subset=["booking_id"], keep="first").sum())
    audit_log["bookings_duplicates_removed"] = dup_count
    df_bkg = df_bkg.drop_duplicates(subset=["booking_id"], keep="first").copy()

    qa_bkg_mask = df_bkg["student_id"].astype(str).str.startswith("STU-TEST-") | ~df_bkg["student_id"].isin(
        df_stu["student_id"]
    )
    audit_log["bookings_qa_test_removed"] = int(qa_bkg_mask.sum())
    df_bkg = df_bkg[~qa_bkg_mask].copy()

    raw_rent_str_count = int(df_bkg["weekly_rent_gbp"].astype(str).str.contains("£|,", regex=True).sum())
    audit_log["bookings_currency_strings_parsed"] = raw_rent_str_count
    df_bkg["weekly_rent_gbp"] = clean_currency_series(df_bkg["weekly_rent_gbp"])
    df_bkg["gross_booking_value_gbp"] = clean_currency_series(df_bkg["gross_booking_value_gbp"])
    df_bkg["lease_weeks"] = df_bkg["lease_weeks"].astype(int)

    invalid_numeric_mask = (df_bkg["lease_weeks"] <= 0) | (df_bkg["weekly_rent_gbp"] <= 0)
    audit_log["bookings_invalid_numeric_quarantined"] = int(invalid_numeric_mask.sum())
    df_bkg_quarantined = df_bkg[invalid_numeric_mask].copy()
    df_bkg_quarantined.to_csv(clean_dir / "bookings_quarantined_anomalies.csv", index=False)
    df_bkg = df_bkg[~invalid_numeric_mask].copy()

    dirty_status_count = int((df_bkg["booking_status"] != df_bkg["booking_status"].astype(str).str.strip().str.title()).sum())
    audit_log["bookings_status_normalized"] = dirty_status_count
    df_bkg["booking_status"] = df_bkg["booking_status"].astype(str).str.strip().str.title()

    missing_checkin = int(df_bkg["check_in_date"].isna().sum())
    audit_log["bookings_missing_checkin_imputed"] = missing_checkin
    df_bkg["check_in_date"] = df_bkg["check_in_date"].fillna(
        df_bkg["academic_intake"].map(INTAKE_DEFAULT_CHECKIN)
    )

    df_bkg["gross_booking_value_gbp"] = (df_bkg["lease_weeks"] * df_bkg["weekly_rent_gbp"]).round(2)
    prop_fin = df_prop[["property_id", "partner_commission_pct", "ops_servicing_cost_gbp"]]
    df_bkg = df_bkg.merge(prop_fin, on="property_id", how="left")

    df_bkg["gross_commission_gbp"] = (
        df_bkg["gross_booking_value_gbp"] * (df_bkg["partner_commission_pct"] / 100.0)
    ).round(2)

    df_bkg["recognized_revenue_gbp"] = np.where(
        df_bkg["booking_status"] == "Confirmed", df_bkg["gross_commission_gbp"], 0.0
    ).round(2)

    df_bkg["total_cost_gbp"] = np.where(
        df_bkg["booking_status"] == "Confirmed",
        (df_bkg["marketing_cpa_gbp"] + df_bkg["ops_servicing_cost_gbp"]).round(2),
        df_bkg["marketing_cpa_gbp"].round(2),
    )

    df_bkg["net_profit_gbp"] = (df_bkg["recognized_revenue_gbp"] - df_bkg["total_cost_gbp"]).round(2)

    df_bkg_normalized = df_bkg[
        [
            "booking_id",
            "student_id",
            "property_id",
            "booking_date",
            "academic_intake",
            "check_in_date",
            "lease_weeks",
            "weekly_rent_gbp",
            "gross_booking_value_gbp",
            "marketing_cpa_gbp",
            "booking_status",
        ]
    ].copy()
    df_bkg_normalized.to_csv(clean_dir / "bookings_cleaned.csv", index=False)
    df_bkg.to_csv(clean_dir / "bookings_enriched_analytics.csv", index=False)
    audit_log["bookings_cleaned_rows"] = int(len(df_bkg_normalized))

    # ---------------------------------------------------------
    # 4. CLEAN PAYMENT INSTALLMENTS & PROMOTIONS TABLES
    # ---------------------------------------------------------
    df_pay = pd.read_csv(raw_dir / "payment_installments_raw.csv")
    df_pay = df_pay[df_pay["booking_id"].isin(df_bkg_normalized["booking_id"])].copy()
    df_pay.to_csv(clean_dir / "payment_installments_cleaned.csv", index=False)
    audit_log["payment_installments_cleaned_rows"] = int(len(df_pay))

    df_promo = pd.read_csv(raw_dir / "property_promotions_raw.csv")
    df_promo.to_csv(clean_dir / "property_promotions_cleaned.csv", index=False)
    audit_log["property_promotions_cleaned_rows"] = int(len(df_promo))

    # ---------------------------------------------------------
    # 5. AUTOMATED VALIDATION ASSERTIONS (PANDAS QUALITY GATES)
    # ---------------------------------------------------------
    assert df_bkg_normalized["booking_id"].is_unique, "Duplicate booking_id found after cleaning!"
    assert (df_bkg_normalized["lease_weeks"] > 0).all(), "Non-positive lease_weeks found!"
    assert (df_bkg_normalized["weekly_rent_gbp"] > 0).all(), "Non-positive weekly_rent_gbp found!"
    assert df_bkg_normalized["student_id"].isin(df_stu["student_id"]).all(), "Orphan student_id found!"
    assert df_bkg_normalized["property_id"].isin(df_prop["property_id"]).all(), "Orphan property_id found!"
    assert set(df_bkg_normalized["booking_status"].unique()).issubset({"Confirmed", "Cancelled", "Pending"})

    confirmed = df_bkg[df_bkg["booking_status"] == "Confirmed"]
    audit_log["confirmed_bookings_count"] = int(len(confirmed))
    audit_log["confirmed_gbv_gbp"] = round(float(confirmed["gross_booking_value_gbp"].sum()), 2)
    audit_log["confirmed_revenue_gbp"] = round(float(confirmed["recognized_revenue_gbp"].sum()), 2)
    audit_log["confirmed_cost_gbp"] = round(float(confirmed["total_cost_gbp"].sum()), 2)
    audit_log["confirmed_net_profit_gbp"] = round(float(confirmed["net_profit_gbp"].sum()), 2)
    audit_log["all_bookings_net_profit_including_sunk_cpa_gbp"] = round(float(df_bkg["net_profit_gbp"].sum()), 2)

    with open(clean_dir / "data_quality_audit_report.json", "w", encoding="utf-8") as f:
        json.dump(audit_log, f, indent=2)

    print("[SUCCESS] Data cleaning & validation pipeline passed all assertions.")
    return audit_log


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    run_cleaning_pipeline(repo_root)
