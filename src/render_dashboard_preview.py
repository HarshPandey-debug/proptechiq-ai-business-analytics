#!/usr/bin/env python3
"""
render_dashboard_preview.py
---------------------------
Renders a 4-panel executive business intelligence dashboard preview (`powerbi/dashboard_preview.png`)
directly from the verified JSON metrics (`data/cleaned/verification_summary.json`).
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np


def render_dashboard(base_dir: str | Path) -> Path:
    base_path = Path(base_dir)
    summary_path = base_path / "data" / "cleaned" / "verification_summary.json"
    out_path = base_path / "powerbi" / "dashboard_preview.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    totals = data["ai_mistake_totals"]
    gbv_total = totals["verified_total_gbv_gbp"]
    rev_total = totals["verified_total_revenue_gbp"]
    prof_total = totals["verified_total_net_profit_gbp"]
    bkg_total = totals["verified_total_bookings"]
    margin_pct = round(prof_total * 100.0 / rev_total, 2)
    err_pct = totals["total_revenue_overstatement_pct"]

    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 0.8

    fig = plt.figure(figsize=(16, 10), dpi=180, facecolor="#F8FAFC")
    gs = fig.add_gridspec(3, 2, height_ratios=[0.24, 1.0, 1.0], hspace=0.38, wspace=0.25)

    # TOP HEADER & KPI RIBBON
    ax_header = fig.add_subplot(gs[0, :])
    ax_header.set_facecolor("#0F172A")
    ax_header.set_xticks([])
    ax_header.set_yticks([])
    for spine in ax_header.spines.values():
        spine.set_visible(False)

    ax_header.text(
        0.50,
        0.67,
        "CampusStay Synthetic Student Housing Marketplace — Executive BI Dashboard (Power BI Preview)",
        color="#FFFFFF",
        fontsize=14.0,
        fontweight="bold",
        ha="center",
        va="center",
        transform=ax_header.transAxes,
    )
    ax_header.text(
        0.50,
        0.26,
        f"Confirmed GBV: £{gbv_total:,.2f}   |   Recognized Revenue: £{rev_total:,.2f}   |   Net Profit: £{prof_total:,.2f} ({margin_pct:.2f}% Margin)   |   Confirmed Bookings: {bkg_total}   |   ROAS: 11.94x",
        color="#93C5FD",
        fontsize=9.3,
        fontweight="bold",
        ha="center",
        va="center",
        transform=ax_header.transAxes,
    )

    # PANEL 1: Revenue & Net Profit by City
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.set_facecolor("#FFFFFF")
    city_rows = data["city_breakdown"]
    cities = [r["city"] for r in city_rows]
    rev_k = [r["platform_revenue_gbp"] / 1000.0 for r in city_rows]
    prof_k = [r["net_profit_gbp"] / 1000.0 for r in city_rows]

    x = np.arange(len(cities))
    w = 0.36
    b1 = ax1.bar(x - w / 2, rev_k, width=w, label="Recognized Revenue (£k)", color="#1D4ED8")
    ax1.bar(x + w / 2, prof_k, width=w, label="Confirmed Net Profit (£k)", color="#0D9488")
    ax1.set_title("1. Recognized Commission Revenue & Net Profit by City (£k)", fontsize=11.5, fontweight="bold", pad=10, color="#0F172A")
    ax1.set_xticks(x)
    ax1.set_xticklabels(cities, fontsize=9.5)
    ax1.set_ylabel("GBP (£ Thousands)", fontsize=9.5)
    ax1.set_ylim(0, max(rev_k) * 1.18)
    ax1.grid(axis="y", linestyle="--", alpha=0.4)
    ax1.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bar in b1:
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 6, f"£{bar.get_height():.1f}k", ha="center", fontsize=8, color="#1E293B")

    # PANEL 2: Monthly Revenue, Profit & 3M Rolling Average
    ax2 = fig.add_subplot(gs[1, 1])
    ax2.set_facecolor("#FFFFFF")
    m_rows = data["monthly_trends"]
    months = [r["booking_month"][2:] for r in m_rows]
    m_rev = [r["monthly_revenue_gbp"] / 1000.0 for r in m_rows]
    m_prof = [r["monthly_net_profit_gbp"] / 1000.0 for r in m_rows]
    m_roll = [r["rolling_3m_avg_revenue_gbp"] / 1000.0 for r in m_rows]

    mx = np.arange(len(months))
    ax2.bar(mx, m_rev, width=0.55, color="#93C5FD", label="Monthly Revenue (£k)")
    ax2.plot(mx, m_roll, color="#1D4ED8", marker="o", linewidth=2.2, label="3M Rolling Avg Revenue (£k)")
    ax2.plot(mx, m_prof, color="#0F766E", marker="s", linestyle="--", linewidth=1.8, label="Monthly Net Profit (£k)")
    ax2.set_title("2. Monthly Revenue Seasonality & 3-Month Rolling Avg (Nov 25 – Oct 26)", fontsize=11.5, fontweight="bold", pad=10, color="#0F172A")
    ax2.set_xticks(mx)
    ax2.set_xticklabels(months, fontsize=8.5, rotation=30)
    ax2.set_ylabel("GBP (£ Thousands)", fontsize=9.5)
    ax2.set_ylim(0, max(m_rev) * 1.18)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)
    ax2.legend(frameon=False, fontsize=8.5, loc="upper left")

    # PANEL 3: Student Cohort x Study Level Segmentation
    ax3 = fig.add_subplot(gs[2, 0])
    ax3.set_facecolor("#FFFFFF")
    seg_rows = data["customer_cohort_segmentation"][:6]
    cohort_short = {"International": "Intl", "Domestic": "UK Dom"}
    seg_labels = [f"{cohort_short.get(r['student_cohort'], r['student_cohort'])} — {r['study_level'].split()[0]}" for r in seg_rows][::-1]
    seg_rev = [r["segment_revenue_gbp"] / 1000.0 for r in seg_rows][::-1]
    seg_prof = [r["segment_net_profit_gbp"] / 1000.0 for r in seg_rows][::-1]

    sy = np.arange(len(seg_labels))
    ax3.barh(sy + 0.18, seg_rev, height=0.35, color="#2563EB", label="Segment Revenue (£k)")
    ax3.barh(sy - 0.18, seg_prof, height=0.35, color="#10B981", label="Segment Net Profit (£k)")
    ax3.set_title("3. Top Customer Segments (Cohort × Study Level, £k)", fontsize=11.5, fontweight="bold", pad=10, color="#0F172A")
    ax3.set_yticks(sy)
    ax3.set_yticklabels(seg_labels, fontsize=9)
    ax3.set_xlabel("GBP (£ Thousands)", fontsize=9.5)
    ax3.set_xlim(0, max(seg_rev) * 1.18)
    ax3.grid(axis="x", linestyle="--", alpha=0.4)
    ax3.legend(frameon=False, fontsize=8.5, loc="lower right")
    for idx_v, val in enumerate(seg_rev):
        ax3.text(val + 5, idx_v + 0.18, f"£{val:.1f}k", va="center", fontsize=8, color="#1E293B")

    # PANEL 4: Manual Verification Audit — Broken AI Fan-Out vs. Verified SQL
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.set_facecolor("#FFFFFF")
    comp_rows = data["ai_mistake_comparison_by_city"]
    c_names = [r["city"] for r in comp_rows]
    ver_rev = [r["verified_revenue_gbp"] / 1000.0 for r in comp_rows]
    err_rev = [r["ai_inflated_revenue_gbp"] / 1000.0 for r in comp_rows]

    cx = np.arange(len(c_names))
    ax4.bar(cx - w / 2, ver_rev, width=w, color="#059669", label="Verified Ground Truth (£k)")
    b_err = ax4.bar(cx + w / 2, err_rev, width=w, color="#DC2626", label="Broken AI Fan-Out Query (£k)")
    ax4.set_title(f"4. Manual Verification Audit: Verified CTE vs. AI Join Fan-Out (+{err_pct:.2f}% Error)", fontsize=11.5, fontweight="bold", pad=10, color="#991B1B")
    ax4.set_xticks(cx)
    ax4.set_xticklabels(c_names, fontsize=9.5)
    ax4.set_ylabel("GBP (£ Thousands)", fontsize=9.5)
    ax4.set_ylim(0, max(err_rev) * 1.18)
    ax4.grid(axis="y", linestyle="--", alpha=0.4)
    ax4.legend(frameon=False, fontsize=8.5, loc="upper right")
    for bar in b_err:
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30, f"£{bar.get_height():.0f}k", ha="center", fontsize=8, color="#991B1B", fontweight="bold")

    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"[SUCCESS] Rendered dashboard preview to: {out_path}")
    return out_path


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    render_dashboard(repo_root)
