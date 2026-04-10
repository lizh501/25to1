import json
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_scm_plot(manifest: dict, output_path: Path, title: str) -> dict:
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
    axes[0].set_title(title)
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
        axes[1].set_title("Anomaly-standardized SCM remains numerically unstable on part of the annual cycle")
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


def read_station_metric(payload: dict, key: str, metric: str) -> float:
    if "baselines" in payload:
        return payload["baselines"][key][metric]
    mapping = {
        "linear_regression": "linear_regression_full_train_validate",
        "random_forest": "random_forest_full_train_validate",
    }
    lookup = mapping.get(key, key)
    return payload[lookup][metric]


def build_station_plot(diagnostics: dict, output_path: Path, title: str) -> None:
    labels = ["Same-day LST", "Four-observation LST", "Linear regression", "Random forest"]
    rmse = [
        read_station_metric(diagnostics, "same_day_lst_mean", "rmse"),
        read_station_metric(diagnostics, "four_obs_lst_mean", "rmse"),
        read_station_metric(diagnostics, "linear_regression", "rmse"),
        read_station_metric(diagnostics, "random_forest", "rmse"),
    ]
    mae = [
        read_station_metric(diagnostics, "same_day_lst_mean", "mae"),
        read_station_metric(diagnostics, "four_obs_lst_mean", "mae"),
        read_station_metric(diagnostics, "linear_regression", "mae"),
        read_station_metric(diagnostics, "random_forest", "mae"),
    ]

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    ax.bar(x - width / 2, rmse, width, label="RMSE", color="#457b9d")
    ax.bar(x + width / 2, mae, width, label="MAE", color="#e76f51")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Error (C)")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def build_patch_plot(srcnn_summary: dict, srw_summary: dict, output_path: Path, title: str) -> None:
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
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build figure assets for Stage-1 long-timeseries reports.")
    parser.add_argument("--report-subdir", default="stage1_longtimeseries_2018_2019")
    parser.add_argument("--scm-manifest", required=True)
    parser.add_argument("--station-diagnostics", required=True)
    parser.add_argument("--srcnn-summary", required=True)
    parser.add_argument("--srw-summary", required=True)
    parser.add_argument("--scm-title", default="Stage-1 Paper-like SCM Climatology")
    parser.add_argument("--station-title", default="Stage-1 Paper-like Station-model Diagnostics")
    parser.add_argument("--patch-title", default="Patch-model quick-run comparison")
    parser.add_argument("--scm-figure-name", default="scm_climatology_cycle.png")
    parser.add_argument("--station-figure-name", default="station_model_compare.png")
    parser.add_argument("--patch-figure-name", default="patch_model_compare.png")
    args = parser.parse_args()

    root = Path("25to1").resolve()
    report_dir = root / "reports" / args.report_subdir
    figure_dir = report_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    scm_manifest = load_json(Path(args.scm_manifest).resolve())
    station_diag = load_json(Path(args.station_diagnostics).resolve())
    srcnn_summary = load_json(Path(args.srcnn_summary).resolve())
    srw_summary = load_json(Path(args.srw_summary).resolve())

    scm_output = figure_dir / args.scm_figure_name
    station_output = figure_dir / args.station_figure_name
    patch_output = figure_dir / args.patch_figure_name
    scm_stats = build_scm_plot(scm_manifest, scm_output, args.scm_title)
    build_station_plot(station_diag, station_output, args.station_title)
    build_patch_plot(srcnn_summary, srw_summary, patch_output, args.patch_title)

    summary = {
        "report_dir": str(report_dir),
        "figures": {
            "scm_cycle": str(scm_output.resolve()),
            "station_model_compare": str(station_output.resolve()),
            "patch_model_compare": str(patch_output.resolve()),
        },
        "scm_stats": scm_stats,
    }
    (report_dir / "assets_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
