#!/usr/bin/env python3
"""
generate_dataset.py
-------------------
Generates a synthetic, simulated Student Housing / PropTech marketplace dataset
("CampusStay PBSA Marketplace") with intentional raw data quality anomalies and
a relational 1-to-many join structure for SQL & AI analytics verification.

Note: All records, student profiles, properties, and financial transactions in this
repository are 100% synthetic simulation data created for portfolio demonstration.

Tables generated in `data/raw/`:
1. students_raw.csv              - Simulated student profiles, nationality, study level, acquisition channel
2. properties_raw.csv            - Simulated PBSA properties across 6 UK university cities
3. bookings_raw.csv              - Lease bookings (includes duplicates, formatting noise, anomalies, cancelled rows)
4. payment_installments_raw.csv  - Multi-installment rent schedules (1-to-many per booking)
5. property_promotions_raw.csv   - Seasonal cashback/discount campaigns per property (1-to-many per property)
"""

from pathlib import Path
import numpy as np
import pandas as pd


def generate_proptech_dataset(base_dir: str | Path, seed: int = 42) -> None:
    rng = np.random.default_rng(seed)
    base_path = Path(base_dir)
    raw_dir = base_path / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # 1. PROPERTIES TABLE (28 synthetic PBSA properties across 6 UK cities)
    # ---------------------------------------------------------
    cities_config = [
        ("London", "University College London (UCL)", 320, 0.085, 65.0),
        ("London", "King's College London", 310, 0.085, 62.0),
        ("Manchester", "University of Manchester", 195, 0.075, 42.0),
        ("Birmingham", "University of Birmingham", 180, 0.070, 38.0),
        ("Edinburgh", "University of Edinburgh", 225, 0.080, 48.0),
        ("Glasgow", "University of Glasgow", 185, 0.072, 39.0),
        ("Nottingham", "University of Nottingham", 170, 0.068, 35.0),
    ]
    tiers = [
        ("Ensuite Standard", 1.00, 7.25, 38.0),
        ("Ensuite Gold", 1.15, 7.50, 44.0),
        ("Studio Classic", 1.35, 8.25, 52.0),
        ("Studio Penthouse", 1.65, 9.00, 68.0),
    ]

    properties_rows = []
    prop_id_counter = 101
    for city, uni, base_rent, _, base_op_cost in cities_config:
        for tier_name, mult, tier_comm_pct, tier_cost in tiers:
            prop_id = f"PROP-{prop_id_counter}"
            prop_id_counter += 1
            # Whole-pound weekly rent ensures exact 2-decimal commission math when paired with 4-week lease multiples
            weekly_rent = float(int(round(base_rent * mult + rng.integers(-10, 15))))
            comm_rate = float(tier_comm_pct)
            op_cost_per_booking = float(int(round((base_op_cost + tier_cost) * 1.8 + rng.integers(-8, 12))))

            # Intentional dirty city formatting on ~18% of properties
            noisy_city = city
            if rng.random() < 0.18:
                noisy_city = rng.choice([city.lower(), f" {city} ", f"{city.upper()}, UK"])

            properties_rows.append(
                {
                    "property_id": prop_id,
                    "property_name": f"CampusStay {city.split()[0]} {tier_name.split()[0]} {prop_id_counter}",
                    "city": noisy_city,
                    "university_corridor": uni,
                    "room_tier": tier_name,
                    "total_beds": int(rng.choice([80, 120, 150, 200, 250])),
                    "standard_weekly_rent_gbp": weekly_rent,
                    "partner_commission_pct": comm_rate if rng.random() > 0.10 else np.nan,  # 10% missing commission rate
                    "ops_servicing_cost_gbp": op_cost_per_booking,
                }
            )

    df_properties = pd.DataFrame(properties_rows)
    df_properties.to_csv(raw_dir / "properties_raw.csv", index=False)

    # ---------------------------------------------------------
    # 2. STUDENTS TABLE (650 simulated students + 10 internal QA test accounts)
    # ---------------------------------------------------------
    nationalities = ["India", "China", "UK", "Nigeria", "USA", "Germany", "France", "Malaysia"]
    nat_probs = [0.30, 0.22, 0.20, 0.08, 0.06, 0.05, 0.05, 0.04]
    study_levels = ["Postgraduate (Masters)", "Undergraduate", "PhD / Research", "Exchange / Foundation"]
    level_probs = [0.48, 0.36, 0.09, 0.07]
    channels = ["Organic Search", "University Partner Referral", "Paid Social (Meta/IG)", "Student Ambassador", "Direct / Repeat"]
    channel_probs = [0.32, 0.25, 0.20, 0.13, 0.10]

    students_rows = []
    for idx in range(1, 651):
        stu_id = f"STU-{1000 + idx}"
        nat = rng.choice(nationalities, p=nat_probs)
        is_intl = "Domestic" if nat == "UK" else "International"
        level = rng.choice(study_levels, p=level_probs)
        ch = rng.choice(channels, p=channel_probs)
        if rng.random() < 0.06:
            ch = None  # 6% missing acquisition channel

        created_dt = pd.Timestamp("2025-09-01") + pd.Timedelta(days=int(rng.integers(0, 390)))
        students_rows.append(
            {
                "student_id": stu_id,
                "full_name": f"Student_{idx}",
                "email": f"student{idx}@sim-univ-{nat.lower()}.example.org",
                "nationality": nat,
                "student_cohort": is_intl,
                "study_level": level,
                "acquisition_channel": ch,
                "signup_date": created_dt.strftime("%Y-%m-%d"),
            }
        )

    # Add 10 internal QA/test accounts (intentional anomaly to filter out)
    for t_idx in range(1, 11):
        students_rows.append(
            {
                "student_id": f"STU-TEST-{t_idx}",
                "full_name": f"QA Test Bot {t_idx}",
                "email": f"qa_bot_{t_idx}@campusstay-qa.internal",
                "nationality": "UK",
                "student_cohort": "Domestic",
                "study_level": "Undergraduate",
                "acquisition_channel": "Direct / Repeat",
                "signup_date": "2026-01-15",
            }
        )

    df_students = pd.DataFrame(students_rows)
    df_students.to_csv(raw_dir / "students_raw.csv", index=False)

    # ---------------------------------------------------------
    # 3. BOOKINGS TABLE (1,100 valid bookings + anomalies + duplicates)
    # ---------------------------------------------------------
    months = pd.date_range("2025-11-01", "2026-10-01", freq="MS")
    month_weights = np.array([0.05, 0.07, 0.08, 0.06, 0.07, 0.08, 0.11, 0.13, 0.14, 0.11, 0.06, 0.04])
    month_weights = month_weights / month_weights.sum()

    valid_student_ids = [f"STU-{1000 + i}" for i in range(1, 651)]
    prop_lookup = df_properties.set_index("property_id").to_dict("index")
    prop_ids = list(prop_lookup.keys())

    bookings_rows = []
    payment_rows = []
    pay_id_counter = 50001

    for b_idx in range(1, 1101):
        booking_id = f"BKG-{20000 + b_idx}"
        stu_id = rng.choice(valid_student_ids)
        prop_id = rng.choice(prop_ids)
        p_info = prop_lookup[prop_id]

        chosen_month = rng.choice(months, p=month_weights)
        day_offset = int(rng.integers(0, 27))
        booking_date = pd.Timestamp(chosen_month) + pd.Timedelta(days=day_offset)

        # Lease duration in weeks (multiples of 4: 44 or 52 weeks for full academic/calendar year, 24 for semester, 12 for summer)
        lease_weeks = int(rng.choice([44, 52, 24, 12], p=[0.42, 0.38, 0.14, 0.06]))
        weekly_rent = float(p_info["standard_weekly_rent_gbp"])
        gross_booking_value = round(lease_weeks * weekly_rent, 2)

        # Booking status: 84% Confirmed, 11% Cancelled, 5% Pending
        status = rng.choice(["Confirmed", "Cancelled", "Pending"], p=[0.84, 0.11, 0.05])

        # Marketing acquisition & platform processing cost allocated to this booking
        marketing_cpa_gbp = round(float(rng.uniform(35.0, 115.0)), 2)

        # Intentional dirty currency strings on ~15% of rows
        rent_str = f"£{weekly_rent:,.2f}" if rng.random() < 0.15 else str(weekly_rent)
        gbv_str = f"£{gross_booking_value:,.2f}" if rng.random() < 0.15 else str(gross_booking_value)

        # Intentional dirty status casing on ~10% of rows
        noisy_status = status
        if rng.random() < 0.10:
            noisy_status = rng.choice([status.lower(), status.upper(), f" {status} "])

        intake = "Sep 2026 Intake" if booking_date.month in [3, 4, 5, 6, 7, 8, 9] else "Jan 2026 Intake"
        check_in_date = "2026-09-12" if intake == "Sep 2026 Intake" else "2026-01-10"
        if rng.random() < 0.05:
            check_in_date = None  # 5% missing check_in_date

        bookings_rows.append(
            {
                "booking_id": booking_id,
                "student_id": stu_id,
                "property_id": prop_id,
                "booking_date": booking_date.strftime("%Y-%m-%d"),
                "academic_intake": intake,
                "check_in_date": check_in_date,
                "lease_weeks": lease_weeks,
                "weekly_rent_gbp": rent_str,
                "gross_booking_value_gbp": gbv_str,
                "marketing_cpa_gbp": marketing_cpa_gbp,
                "booking_status": noisy_status,
            }
        )

        # Generate multi-installment payments (1-to-many relationship: 1 booking -> 1, 3, or 4 installments)
        num_installments = int(rng.choice([1, 3, 4], p=[0.20, 0.50, 0.30]))
        base_inst = round(gross_booking_value / num_installments, 2)
        for inst_num in range(1, num_installments + 1):
            if inst_num < num_installments:
                inst_amt = base_inst
            else:
                # Final installment absorbs any 1p rounding remainder so installments sum to exact GBV
                inst_amt = round(gross_booking_value - base_inst * (num_installments - 1), 2)
            pay_date = booking_date + pd.Timedelta(days=30 * (inst_num - 1))
            pay_status = "Paid" if status == "Confirmed" else ("Refunded" if status == "Cancelled" else "Scheduled")
            payment_rows.append(
                {
                    "payment_id": f"PAY-{pay_id_counter}",
                    "booking_id": booking_id,
                    "installment_number": inst_num,
                    "payment_date": pay_date.strftime("%Y-%m-%d"),
                    "installment_amount_gbp": inst_amt,
                    "payment_method": rng.choice(["Bank Wire", "Credit Card", "Flywire Intl", "Direct Debit"]),
                    "payment_status": pay_status,
                }
            )
            pay_id_counter += 1

    # ---------------------------------------------------------
    # Inject Intentional Anomalies into Bookings:
    # A) 15 corrupted rows with negative or zero lease_weeks / weekly_rent
    # B) 12 bookings from internal QA test bots (STU-TEST-*)
    # C) 42 exact duplicate webhook retry rows
    # ---------------------------------------------------------
    for err_idx in range(1, 16):
        bookings_rows.append(
            {
                "booking_id": f"BKG-ERR-{err_idx}",
                "student_id": rng.choice(valid_student_ids),
                "property_id": rng.choice(prop_ids),
                "booking_date": "2026-05-18",
                "academic_intake": "Sep 2026 Intake",
                "check_in_date": "2026-09-12",
                "lease_weeks": -44 if err_idx % 2 == 0 else 0,
                "weekly_rent_gbp": "-210.00" if err_idx % 3 == 0 else "210.00",
                "gross_booking_value_gbp": "-9240.00" if err_idx % 2 == 0 else "0.00",
                "marketing_cpa_gbp": 55.0,
                "booking_status": "Confirmed",
            }
        )

    for qa_idx in range(1, 13):
        bookings_rows.append(
            {
                "booking_id": f"BKG-QA-{qa_idx}",
                "student_id": f"STU-TEST-{(qa_idx % 10) + 1}",
                "property_id": rng.choice(prop_ids),
                "booking_date": "2026-02-10",
                "academic_intake": "Sep 2026 Intake",
                "check_in_date": "2026-09-12",
                "lease_weeks": 52,
                "weekly_rent_gbp": "999.00",
                "gross_booking_value_gbp": "51948.00",
                "marketing_cpa_gbp": 0.0,
                "booking_status": "Confirmed",
            }
        )

    duplicate_samples = [bookings_rows[i].copy() for i in rng.choice(range(1100), size=42, replace=False)]
    bookings_rows.extend(duplicate_samples)

    df_bookings = pd.DataFrame(bookings_rows)
    df_bookings.to_csv(raw_dir / "bookings_raw.csv", index=False)

    df_payments = pd.DataFrame(payment_rows)
    df_payments.to_csv(raw_dir / "payment_installments_raw.csv", index=False)

    # ---------------------------------------------------------
    # 4. PROPERTY PROMOTIONS TABLE (1-to-many campaigns per property)
    # ---------------------------------------------------------
    promo_rows = []
    promo_counter = 301
    for prop_id in prop_ids:
        num_promos = int(rng.choice([1, 2, 3], p=[0.3, 0.5, 0.2]))
        for _ in range(num_promos):
            promo_rows.append(
                {
                    "promo_id": f"PRM-{promo_counter}",
                    "property_id": prop_id,
                    "campaign_name": rng.choice(
                        ["Early Bird Cashback", "Group Booking Voucher", "Free Bedding Pack", "Zero Deposit Offer"]
                    ),
                    "promo_discount_gbp": float(rng.choice([50.0, 100.0, 150.0, 200.0])),
                    "active_intake": rng.choice(["Sep 2026 Intake", "Jan 2026 Intake"]),
                }
            )
            promo_counter += 1

    df_promos = pd.DataFrame(promo_rows)
    df_promos.to_csv(raw_dir / "property_promotions_raw.csv", index=False)

    print(f"[SUCCESS] Synthetic raw datasets generated in: {raw_dir}")


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    generate_proptech_dataset(repo_root)
