import argparse
import json
from collections import OrderedDict
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


BASE_PATCH_FEATURES = [
    "era5_t2m_c",
    "dem_m",
    "slope_deg",
    "imp_proxy",
    "lc_type1_majority",
    "lst_day_c",
    "lst_night_c",
    "lst_mean_c",
    "ndvi",
    "solar_incoming_w_m2",
    "valid_day",
    "valid_night",
    "valid_mean",
]


def build_feature_layout(scm_field: str) -> tuple[list[str], list[str], list[str]]:
    patch_features = BASE_PATCH_FEATURES[:8] + [scm_field] + BASE_PATCH_FEATURES[8:]
    input_features = patch_features + ["aspect_sin", "aspect_cos"]
    static_like_features = ["dem_m", scm_field]
    return patch_features, input_features, static_like_features


def choose_device(device_arg: str) -> str:
    if device_arg != "auto":
        return device_arg
    return "cuda" if torch.cuda.is_available() else "cpu"


def masked_metrics(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> dict:
    valid = mask > 0.5
    if valid.sum().item() == 0:
        return {"mae": None, "rmse": None}
    diff = pred[valid] - target[valid]
    mae = torch.mean(torch.abs(diff)).item()
    rmse = torch.sqrt(torch.mean(diff ** 2)).item()
    return {"mae": float(mae), "rmse": float(rmse)}


def normalize_feature(name: str, arr: np.ndarray) -> np.ndarray:
    out = arr.astype(np.float32, copy=True)
    if name in {"era5_t2m_c", "lst_day_c", "lst_night_c", "lst_mean_c", "scm_bootstrap_c", "scm_paperlike_c"}:
        out = np.clip(out, -40.0, 50.0) / 20.0
    elif name == "dem_m":
        out[out <= -10000.0] = np.nan
        out = np.clip(out, -100.0, 3000.0) / 1000.0
    elif name == "slope_deg":
        out = np.clip(out, 0.0, 60.0) / 45.0
    elif name == "imp_proxy":
        out = np.clip(out, 0.0, 1.0)
    elif name == "lc_type1_majority":
        out[out < 0.0] = np.nan
        out = np.clip(out, 0.0, 17.0) / 17.0
    elif name == "ndvi":
        out = np.clip(out, -0.2, 1.0)
    elif name == "solar_incoming_w_m2":
        out = np.clip(out, 0.0, 400.0) / 400.0
    elif name.startswith("valid_"):
        out = np.clip(out, 0.0, 1.0)
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def build_input_stack(day_arrays: dict, patch_features: list[str], row0: int, row1: int, col0: int, col1: int) -> np.ndarray:
    channels = []
    for name in patch_features:
        channels.append(normalize_feature(name, day_arrays[name][row0:row1, col0:col1]))

    aspect = day_arrays["aspect_deg"][row0:row1, col0:col1].astype(np.float32)
    aspect = np.deg2rad(np.nan_to_num(aspect, nan=0.0))
    channels.append(np.sin(aspect).astype(np.float32))
    channels.append(np.cos(aspect).astype(np.float32))

    return np.stack(channels, axis=0).astype(np.float32)


class PatchDataset(Dataset):
    def __init__(self, index_csv: Path, split: str, patch_features: list[str], cache_size: int = 4):
        self.df = pd.read_csv(index_csv, encoding="utf-8")
        self.df = self.df[self.df["split"] == split].reset_index(drop=True)
        self.patch_features = patch_features
        self.cache_size = cache_size
        self.day_cache: OrderedDict[str, dict] = OrderedDict()
        if self.df.empty:
            raise ValueError(f"No rows found for split={split}")

    def __len__(self) -> int:
        return len(self.df)

    def _load_day(self, row) -> dict:
        day = row["day"]
        if day in self.day_cache:
            self.day_cache.move_to_end(day)
            return self.day_cache[day]

        npz_path = Path(row["features_npz"])
        label_path = Path(row["label_tif"])
        valid_path = Path(row["valid_tif"])

        with np.load(npz_path) as data:
            arrays = {key: data[key].copy() for key in data.files}
        with rasterio.open(label_path) as ds:
            label = ds.read(1).astype(np.float32)
            label_nodata = float(ds.nodata)
        with rasterio.open(valid_path) as ds:
            valid = ds.read(1).astype(np.uint8)

        payload = {
            "arrays": arrays,
            "label": label,
            "label_nodata": label_nodata,
            "valid": valid,
        }
        self.day_cache[day] = payload
        if len(self.day_cache) > self.cache_size:
            self.day_cache.popitem(last=False)
        return payload

    def __getitem__(self, idx: int):
        row = self.df.iloc[idx]
        payload = self._load_day(row)
        row0, row1 = int(row["row0"]), int(row["row1"])
        col0, col1 = int(row["col0"]), int(row["col1"])

        x = build_input_stack(payload["arrays"], self.patch_features, row0, row1, col0, col1)
        y = payload["label"][row0:row1, col0:col1].copy()
        mask = payload["valid"][row0:row1, col0:col1].astype(np.float32)
        y = np.where(y == payload["label_nodata"], 0.0, y).astype(np.float32)

        return (
            torch.from_numpy(x),
            torch.from_numpy(y[None, ...]),
            torch.from_numpy(mask[None, ...]),
        )


class SRCNNLike(nn.Module):
    def __init__(self, in_channels: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=9, padding=4),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 32, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(32, 1, kernel_size=5, padding=2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x[:, 0:1, :, :] * 20.0
        return residual + self.net(x)


class SEBlock(nn.Module):
    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        hidden = max(channels // reduction, 8)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, hidden, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, kernel_size=1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        weight = self.fc(self.pool(x))
        return x * weight


class SESRCNN(nn.Module):
    def __init__(self, in_channels: int):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, 64, kernel_size=9, padding=4)
        self.conv2 = nn.Conv2d(64, 32, kernel_size=5, padding=2)
        self.se = SEBlock(32, reduction=8)
        self.conv3 = nn.Conv2d(32, 1, kernel_size=5, padding=2)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x[:, 0:1, :, :] * 20.0
        feat = self.relu(self.conv1(x))
        feat = self.relu(self.conv2(feat))
        feat = self.se(feat)
        return residual + self.conv3(feat)


class SRWeatherGate(nn.Module):
    def __init__(self, feat_channels: int, all_channels: int, static_channels: int):
        super().__init__()
        hidden = max(feat_channels // 2, 16)
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(all_channels + 2 * static_channels, hidden),
            nn.ReLU(inplace=True),
            nn.Linear(hidden, feat_channels),
            nn.Sigmoid(),
        )

    def forward(self, feat: torch.Tensor, all_inputs: torch.Tensor, static_inputs: torch.Tensor) -> torch.Tensor:
        avg_desc = self.avg_pool(all_inputs).flatten(1)
        max_desc = self.max_pool(static_inputs).flatten(1)
        min_desc = -self.max_pool(-static_inputs).flatten(1)
        desc = torch.cat([avg_desc, max_desc, min_desc], dim=1)
        weight = self.fc(desc).unsqueeze(-1).unsqueeze(-1)
        return feat * weight


class SRWeatherLike(nn.Module):
    def __init__(self, in_channels: int, static_indices: list[int]):
        super().__init__()
        self.static_indices = static_indices
        self.conv1 = nn.Conv2d(in_channels, 64, kernel_size=9, padding=4)
        self.conv2 = nn.Conv2d(64, 32, kernel_size=5, padding=2)
        self.conv3 = nn.Conv2d(32, 1, kernel_size=5, padding=2)
        self.relu = nn.ReLU(inplace=True)
        self.gate = SRWeatherGate(
            feat_channels=32,
            all_channels=in_channels,
            static_channels=len(static_indices),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x[:, 0:1, :, :] * 20.0
        feat = self.relu(self.conv1(x))
        feat = self.relu(self.conv2(feat))
        static_inputs = x[:, self.static_indices, :, :]
        feat = self.gate(feat, x, static_inputs)
        return residual + self.conv3(feat)


def build_model(architecture: str, in_channels: int, input_features: list[str], static_like_features: list[str]) -> nn.Module:
    if architecture == "srcnn_like":
        return SRCNNLike(in_channels=in_channels)
    if architecture == "se_srcnn":
        return SESRCNN(in_channels=in_channels)
    if architecture == "sr_weather_like":
        static_indices = [input_features.index(name) for name in static_like_features]
        return SRWeatherLike(in_channels=in_channels, static_indices=static_indices)
    raise ValueError(f"Unsupported architecture: {architecture}")


def masked_l1_loss(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    valid = mask > 0.5
    if valid.sum().item() == 0:
        return pred.new_tensor(0.0)
    return torch.mean(torch.abs(pred[valid] - target[valid]))


def run_epoch(model, loader, optimizer, device: str, train: bool) -> dict:
    model.train(train)
    total_loss = 0.0
    total_steps = 0
    preds_all = []
    targets_all = []
    masks_all = []

    for x, y, mask in loader:
        x = x.to(device)
        y = y.to(device)
        mask = mask.to(device)

        with torch.set_grad_enabled(train):
            pred = model(x)
            loss = masked_l1_loss(pred, y, mask)
            if train:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()

        total_loss += float(loss.item())
        total_steps += 1
        preds_all.append(pred.detach().cpu())
        targets_all.append(y.detach().cpu())
        masks_all.append(mask.detach().cpu())

    preds = torch.cat(preds_all, dim=0)
    targets = torch.cat(targets_all, dim=0)
    masks = torch.cat(masks_all, dim=0)
    metrics = masked_metrics(preds, targets, masks)
    metrics["loss"] = total_loss / max(total_steps, 1)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a first Stage-1 CNN baseline on bootstrap patch data.")
    parser.add_argument(
        "--patch-index",
        default="25to1/data/stage1/processed/stage1_patch_index_q1_ps64_s64_v50/stage1_patch_index.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="25to1/data/stage1/models/stage1_patch_cnn_q1_ps64_s64_v50",
    )
    parser.add_argument(
        "--architecture",
        choices=["srcnn_like", "se_srcnn", "sr_weather_like"],
        default="srcnn_like",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--cache-size", type=int, default=4)
    parser.add_argument("--scm-field", default="scm_bootstrap_c")
    args = parser.parse_args()

    patch_index = Path(args.patch_index).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    device = choose_device(args.device)
    patch_features, input_features, static_like_features = build_feature_layout(args.scm_field)
    train_ds = PatchDataset(patch_index, split="train", patch_features=patch_features, cache_size=args.cache_size)
    test_ds = PatchDataset(
        patch_index,
        split="test",
        patch_features=patch_features,
        cache_size=max(2, args.cache_size // 2),
    )

    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
    )
    test_loader = DataLoader(
        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

    in_channels = len(input_features)
    model = build_model(
        args.architecture,
        in_channels=in_channels,
        input_features=input_features,
        static_like_features=static_like_features,
    ).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    history = []
    best_rmse = None
    best_path = output_dir / "best_model.pt"

    for epoch in range(1, args.epochs + 1):
        train_metrics = run_epoch(model, train_loader, optimizer, device, train=True)
        test_metrics = run_epoch(model, test_loader, optimizer, device, train=False)
        row = {
            "epoch": epoch,
            "train": train_metrics,
            "test": test_metrics,
        }
        history.append(row)
        print(json.dumps(row, ensure_ascii=False))

        test_rmse = test_metrics["rmse"]
        if test_rmse is not None and (best_rmse is None or test_rmse < best_rmse):
            best_rmse = test_rmse
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "architecture": args.architecture,
                    "in_channels": in_channels,
                    "patch_features": input_features,
                    "scm_field": args.scm_field,
                },
                best_path,
            )

    summary = {
        "patch_index": str(patch_index),
        "architecture": args.architecture,
        "device": device,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "lr": args.lr,
        "scm_field": args.scm_field,
        "train_patches": len(train_ds),
        "test_patches": len(test_ds),
        "model_path": str(best_path),
        "history": history,
        "best_test_rmse": best_rmse,
    }

    summary_path = output_dir / "training_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"WROTE {summary_path}")


if __name__ == "__main__":
    main()
