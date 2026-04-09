import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_scm_plot(manifest: dict, output_path: Path) -> dict:
    climatology = manifest["outputs"]["climatology_365"]
    anomaly = manifest["outputs"].get("anomaly_standardized_365", [])

    doys = [item["doy"] for item in climatology]
    clim_mean = [item["mean"] for item in climatology]
    clim_min = [item["min"] for item in climatology]
    clim_max = [item["max"] for item in climatology]

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), dpi=160, sharex=True)
    axes[0].plot(doys, clim_mean, color="#1b6ca8", linewidth=2.0, label="SCM climatology mean")
    axes[0].fill_between(doys, clim_min, clim_max, color="#8ecae6", alpha=0.35, label="Daily min-max envelope")
    axes[0].set_ylabel("Temperature (C)")
    axes[0].set_title("Stage-1 Paper-like SCM Climatology (2018-2019)")
    axes[0].grid(alpha=0.25)
    axes[0].legend(loc="upper left")

    if anomaly:
        valid_counts = [item["valid_pixels"] for item in anomaly]
        clipped_mean = []
        for item in anomaly:
            mean = item["mean"]
            if mean is None:
                clipped_mean.append(np.nan)
            else:
                clipped_mean.append(float(np.clip(mean, -20.0, 20.0)))
        axes[1].plot(doys, clipped_mean, color="#c1121f", linewidth=1.8, label="Anomaly mean (clipped to [-20, 20])")
        axes[1].bar(doys, valid_counts, color="#f4a261", alpha=0.5, label="Valid pixels")
        axes[1].set_ylabel("Anomaly / valid count")
        axes[1].set_title("Anomaly-standardized SCM is numerically unstable in parts of 2018-2019")
        axes[1].grid(alpha=0.25)
        axes[1].legend(loc="upper left")

    axes[1].set_xlabel("Day of year")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)

    anomaly_extreme_days = []
    for item in anomaly:
        min_v = item.get("min")
        max_v = item.get("max")
        if min_v is None or max_v is None:
            continue
        if abs(min_v) > 1000 or abs(max_v) > 1000:
            anomaly_extreme_days.append(item["doy"])

    return {
        "climatology_mean_min": float(np.nanmin(clim_mean)),
        "climatology_mean_max": float(np.nanmax(clim_mean)),
        "anomaly_extreme_day_count": int(len(anomaly_extreme_days)),
        "anomaly_extreme_days_head": anomaly_extreme_days[:20],
    }


def build_station_plot(diagnostics: dict, output_path: Path) -> None:
    labels = ["Same-day LST", "Four-observation LST", "Linear regression"]
    rmse = [
        diagnostics["same_day_lst_mean"]["rmse"],
        diagnostics["four_obs_lst_mean"]["rmse"],
        diagnostics["linear_regression_full_train_validate"]["rmse"],
    ]
    mae = [
        diagnostics["same_day_lst_mean"]["mae"],
        diagnostics["four_obs_lst_mean"]["mae"],
        diagnostics["linear_regression_full_train_validate"]["mae"],
    ]

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    ax.bar(x - width / 2, rmse, width, label="RMSE", color="#457b9d")
    ax.bar(x + width / 2, mae, width, label="MAE", color="#e76f51")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Error (C)")
    ax.set_title("2018-2019 Stage-1 Paper-like Station-model Diagnostics")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def build_patch_plot(srcnn_summary: dict, srw_summary: dict, output_path: Path) -> None:
    labels = ["SRCNN-like", "SR-Weather-like"]
    rmse = [
        srcnn_summary["history"][-1]["test"]["rmse"],
        srw_summary["history"][-1]["test"]["rmse"],
    ]
    mae = [
        srcnn_summary["history"][-1]["test"]["mae"],
        srw_summary["history"][-1]["test"]["mae"],
    ]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
    ax.bar(x - width / 2, rmse, width, label="Test RMSE", color="#2a9d8f")
    ax.bar(x + width / 2, mae, width, label="Test MAE", color="#f4a261")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Patch error (C)")
    ax.set_title("2018 train -> 2019 test quick-run patch comparison")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    root = Path("25to1").resolve()
    report_dir = root / "reports" / "stage1_longtimeseries_2018_2019"
    figure_dir = report_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    scm_manifest = load_json(root / "data" / "stage1" / "processed" / "scm_paperlike_linear_clip_2018_2019full" / "manifest.json")
    station_diag = load_json(root / "data" / "stage1" / "models" / "modis_at_paperlike_asos64_aws_chunk420_2018_2019full" / "training_diagnostics_rerun.json")
    srcnn_summary = load_json(root / "data" / "stage1" / "models" / "stage1_patch_cnn_scmpaperlike_2018train_2019test_daily5_ps64_s64_v50" / "training_summary.json")
    srw_summary = load_json(root / "data" / "stage1" / "models" / "stage1_patch_sr_weather_like_scmpaperlike_2018train_2019test_daily5_ps64_s64_v50" / "training_summary.json")

    scm_stats = build_scm_plot(scm_manifest, figure_dir / "scm_climatology_cycle_2018_2019.png")
    build_station_plot(station_diag, figure_dir / "station_model_compare_2018_2019.png")
    build_patch_plot(srcnn_summary, srw_summary, figure_dir / "patch_model_compare_2018_2019.png")

    summary = {
        "report_dir": str(report_dir),
        "figures": {
            "scm_cycle": str((figure_dir / "scm_climatology_cycle_2018_2019.png").resolve()),
            "station_model_compare": str((figure_dir / "station_model_compare_2018_2019.png").resolve()),
            "patch_model_compare": str((figure_dir / "patch_model_compare_2018_2019.png").resolve()),
        },
        "scm_stats": scm_stats,
    }
    (report_dir / "assets_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
