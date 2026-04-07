import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "stage1_overview"
FIG_DIR = REPORT_DIR / "figures"

COLLOCATION_CSV = ROOT / "data" / "stage1" / "processed" / "station_collocations_full65_jansep" / "stage1_station_collocations_2018_01.csv"
BASELINE_JSONS = {
    "Jan": ROOT / "data" / "stage1" / "models" / "station_baseline_full65" / "time_split" / "metrics_summary.json",
    "Jan-Feb": ROOT / "data" / "stage1" / "models" / "station_baseline_full65_janfeb" / "time_split_jan_train_feb_test" / "metrics_summary.json",
    "Q1": ROOT / "data" / "stage1" / "models" / "station_baseline_full65_q1" / "time_split_janfeb_train_mar_test" / "metrics_summary.json",
    "Jan-Apr": ROOT / "data" / "stage1" / "models" / "station_baseline_full65_q1apr" / "time_split_janmar_train_apr_test" / "metrics_summary.json",
    "H1": ROOT / "data" / "stage1" / "models" / "station_baseline_full65_h1" / "time_split_janapr_train_mayjun_test" / "metrics_summary.json",
    "Jan-Sep": ROOT / "data" / "stage1" / "models" / "station_baseline_full65_jansep" / "time_split_janh1_train_q3_test" / "metrics_summary.json",
}
PATCH_JSONS = {
    "Q1 srcnn": ROOT / "data" / "stage1" / "models" / "stage1_patch_cnn_q1_janfebtrain_ps64_s64_v50" / "training_summary.json",
    "Q1 se-srcnn": ROOT / "data" / "stage1" / "models" / "stage1_patch_se_srcnn_q1_janfebtrain_ps64_s64_v50" / "training_summary.json",
    "Q1 sr-weather": ROOT / "data" / "stage1" / "models" / "stage1_patch_sr_weather_like_q1_janfebtrain_ps64_s64_v50" / "training_summary.json",
    "Jan-Apr srcnn+SCM": ROOT / "data" / "stage1" / "models" / "stage1_patch_cnn_scmroll15_q1apr_janmartrain_ps64_s64_v50" / "training_summary.json",
    "Jan-Apr sr-weather+SCM": ROOT / "data" / "stage1" / "models" / "stage1_patch_sr_weather_like_scmroll15_q1apr_janmartrain_ps64_s64_v50" / "training_summary.json",
    "H1 srcnn+SCM": ROOT / "data" / "stage1" / "models" / "stage1_patch_cnn_scmroll15_h1_janaprtrain_ps64_s64_v50" / "training_summary.json",
    "H1 sr-weather+SCM": ROOT / "data" / "stage1" / "models" / "stage1_patch_sr_weather_like_scmroll15_h1_janaprtrain_ps64_s64_v50" / "training_summary.json",
}


def ensure_dirs() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_monthly_coverage(df: pd.DataFrame) -> dict:
    month_counts = df.groupby(df["date"].dt.to_period("M")).size()
    month_labels = [str(item) for item in month_counts.index]
    counts = month_counts.to_list()

    plt.figure(figsize=(10, 4.8))
    ax = plt.gca()
    bars = ax.bar(month_labels, counts, color="#41729F")
    ax.set_title("Stage-1 Jan-Sep 2018 Collocation Coverage")
    ax.set_xlabel("Month")
    ax.set_ylabel("Rows")
    for bar, value in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 30, f"{value}", ha="center", va="bottom", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    out_path = FIG_DIR / "stage1_monthly_coverage.png"
    plt.savefig(out_path, dpi=180)
    plt.close()

    return {
        "path": str(out_path),
        "month_counts": dict(zip(month_labels, counts)),
    }


def build_feature_relationships(df: pd.DataFrame) -> dict:
    subset = df[[
        "station_avg_temp_c",
        "era5_t2m_c",
        "lst_mean_c",
        "ndvi",
        "solar_incoming_w_m2",
    ]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(subset) > 5000:
        subset = subset.sample(5000, random_state=42)

    corr_era5 = float(df[["station_avg_temp_c", "era5_t2m_c"]].corr().iloc[0, 1])
    corr_lst = float(df[["station_avg_temp_c", "lst_mean_c"]].dropna().corr().iloc[0, 1])

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
    axes[0].scatter(subset["era5_t2m_c"], subset["station_avg_temp_c"], s=8, alpha=0.35, color="#2A9D8F")
    axes[0].set_title(f"Station vs ERA5 (r={corr_era5:.3f})")
    axes[0].set_xlabel("ERA5 T2M (C)")
    axes[0].set_ylabel("Station Avg Temp (C)")
    axes[0].grid(alpha=0.25)

    axes[1].scatter(subset["lst_mean_c"], subset["station_avg_temp_c"], s=8, alpha=0.35, color="#E76F51")
    axes[1].set_title(f"Station vs LST Mean (r={corr_lst:.3f})")
    axes[1].set_xlabel("MODIS LST Mean (C)")
    axes[1].set_ylabel("Station Avg Temp (C)")
    axes[1].grid(alpha=0.25)

    plt.tight_layout()
    out_path = FIG_DIR / "stage1_feature_relationships.png"
    plt.savefig(out_path, dpi=180)
    plt.close()

    return {
        "path": str(out_path),
        "corr_station_era5": corr_era5,
        "corr_station_lst_mean": corr_lst,
    }


def build_model_progress() -> dict:
    baseline_points = []
    for label, path in BASELINE_JSONS.items():
        data = load_json(path)
        baseline_points.append(
            {
                "label": label,
                "era5_rmse": data["baselines"]["era5_only"]["rmse"],
                "linear_rmse": data["baselines"]["linear_regression"]["rmse"],
                "test_rows": data["test_rows"],
            }
        )

    patch_points = []
    for label, path in PATCH_JSONS.items():
        data = load_json(path)
        patch_points.append(
            {
                "label": label,
                "best_test_rmse": data["best_test_rmse"],
            }
        )

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8))

    x = np.arange(len(baseline_points))
    axes[0].plot(x, [item["era5_rmse"] for item in baseline_points], marker="o", label="ERA5 only", color="#6C757D")
    axes[0].plot(x, [item["linear_rmse"] for item in baseline_points], marker="o", label="Linear regression", color="#1D3557")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels([item["label"] for item in baseline_points], rotation=25, ha="right")
    axes[0].set_ylabel("RMSE (C)")
    axes[0].set_title("Time-Split Baseline RMSE")
    axes[0].grid(alpha=0.25)
    axes[0].legend()

    patch_x = np.arange(len(patch_points))
    bars = axes[1].bar(patch_x, [item["best_test_rmse"] for item in patch_points], color="#457B9D")
    axes[1].set_xticks(patch_x)
    axes[1].set_xticklabels([item["label"] for item in patch_points], rotation=35, ha="right")
    axes[1].set_ylabel("Best Test RMSE")
    axes[1].set_title("Patch Model Best Test RMSE")
    axes[1].grid(axis="y", alpha=0.25)
    for bar, item in zip(bars, patch_points):
        axes[1].text(bar.get_x() + bar.get_width() / 2, item["best_test_rmse"] + 0.005, f"{item['best_test_rmse']:.3f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    out_path = FIG_DIR / "stage1_model_progress.png"
    plt.savefig(out_path, dpi=180)
    plt.close()

    return {
        "path": str(out_path),
        "baseline_points": baseline_points,
        "patch_points": patch_points,
    }


def feature_stats(df: pd.DataFrame) -> dict:
    stats = {}
    for col in [
        "station_avg_temp_c",
        "era5_t2m_c",
        "lst_mean_c",
        "ndvi",
        "solar_incoming_w_m2",
        "dem_m",
        "imp_proxy",
    ]:
        series = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        stats[col] = {
            "count": int(series.shape[0]),
            "mean": float(series.mean()),
            "std": float(series.std()),
            "min": float(series.min()),
            "p25": float(series.quantile(0.25)),
            "p50": float(series.quantile(0.50)),
            "p75": float(series.quantile(0.75)),
            "max": float(series.max()),
        }
    return stats


def main() -> None:
    ensure_dirs()
    df = pd.read_csv(COLLOCATION_CSV, encoding="utf-8")
    df["date"] = pd.to_datetime(df["date"])

    summary = {
        "collocation_csv": str(COLLOCATION_CSV),
        "row_count": int(len(df)),
        "station_count": int(df["station_id"].astype(str).nunique()),
        "date_min": df["date"].min().strftime("%Y-%m-%d"),
        "date_max": df["date"].max().strftime("%Y-%m-%d"),
        "feature_stats": feature_stats(df),
    }
    summary["monthly_coverage"] = build_monthly_coverage(df)
    summary["feature_relationships"] = build_feature_relationships(df)
    summary["model_progress"] = build_model_progress()

    summary_path = REPORT_DIR / "stage1_overview_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {summary_path}")
    for key in ["monthly_coverage", "feature_relationships", "model_progress"]:
        print(summary[key]["path"])


if __name__ == "__main__":
    main()
