"""
cnn_lstm_model.py
=================

Recreation of the previous study's final CNN-LSTM (Galang et al., "Test Four" /
Model 4) in PyTorch, run on OUR data for the apples-to-apples experiment.

The experiment (Objective 1): the ONLY thing that changes between the two runs
is the feature set, so the measured difference is Sentinel-1's contribution.

    Original AgriKA : weather + NDVI            (S2 only,  3 features/step)
    Enhanced AgriKA : weather + NDVI + VV/VH    (S2 + S1,  5 features/step)

Everything else is held constant: same architecture, same real-yield target,
same leave-one-year-out protocol, same test observations. Per-sample out-of-fold
predictions for both configs are saved so the paired significance test
(Shapiro-Wilk -> paired t-test / Wilcoxon) can run on paired errors.

Architecture (faithful to the paper's Test Four table):
  GaussianNoise(0.01) -> Conv1d(64,k5)->BN->ReLU -> Conv1d(128,k5)->BN->ReLU
  -> LSTM(128, return_seq)->LayerNorm->drop -> LSTM(64)->LayerNorm->drop
  -> Dense(64)->ReLU->drop -> Dense(32)->ReLU->drop -> Linear(1)
  Adam(lr=4.5e-4, weight_decay=1e-4 for L2), StepLR(gamma=0.9), early stop.

Two documented adaptations to our shorter input (both standard, defensible):
  1. MaxPooling omitted. The paper's two pool(2) layers were sized for a long
     input sequence; on our 6-step monthly sequences they would collapse the
     temporal axis (6->3->1) and defeat the LSTM. We keep 'same' convolutions
     and feed all 6 steps to the LSTM.
  2. Recurrent dropout approximated with standard dropout on LSTM outputs -
     PyTorch's cuDNN LSTM has no Keras-style recurrent dropout.

Requires: torch, numpy, pandas, scikit-learn (for metrics/splits).

Usage
    python backend/scripts/cnn_lstm_model.py
"""
import os

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

HERE = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.abspath(os.path.join(HERE, "..", "db"))
SEQ_CSV = os.path.join(DB_DIR, "training_features_sequences.csv")
OOF_CSV = os.path.join(DB_DIR, "cnn_lstm_oof_predictions.csv")

STEPS = 6
SEED = 42

FEATURE_SETS = {
    "S2 only (original)": ["rain", "temp", "ndvi"],
    "S2+S1 (enhanced)": ["rain", "temp", "ndvi", "vv", "vh"],
}


def set_seed(s):
    np.random.seed(s)
    torch.manual_seed(s)


def load_sequences(feature_cols):
    """Return X (N, STEPS, F), y (N,), groups (year), and a key DataFrame."""
    df = pd.read_csv(SEQ_CSV)
    key_cols = ["municipality", "year", "season"]
    df = df.sort_values(key_cols + ["seq_step"])
    keys = df[key_cols + ["yield_mt_ha"]].drop_duplicates(key_cols).reset_index(drop=True)

    X = np.full((len(keys), STEPS, len(feature_cols)), np.nan, dtype=np.float32)
    idx = {tuple(r): i for i, r in enumerate(keys[key_cols].itertuples(index=False, name=None))}
    for r in df.itertuples(index=False):
        i = idx[(r.municipality, r.year, r.season)]
        step = int(r.seq_step) - 1
        for j, c in enumerate(feature_cols):
            X[i, step, j] = getattr(r, c)
    y = keys["yield_mt_ha"].to_numpy(dtype=np.float32)
    groups = keys["year"].to_numpy()
    return X, y, groups, keys


class GaussianNoise(nn.Module):
    def __init__(self, std):
        super().__init__()
        self.std = std

    def forward(self, x):
        if self.training and self.std > 0:
            return x + torch.randn_like(x) * self.std
        return x


class CNNLSTM(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.noise = GaussianNoise(0.01)
        self.conv1 = nn.Conv1d(n_features, 64, kernel_size=5, padding=2)
        self.bn1 = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 128, kernel_size=5, padding=2)
        self.bn2 = nn.BatchNorm1d(128)
        self.lstm1 = nn.LSTM(128, 128, batch_first=True)
        self.ln1 = nn.LayerNorm(128)
        self.drop1 = nn.Dropout(0.3)
        self.lstm2 = nn.LSTM(128, 64, batch_first=True)
        self.ln2 = nn.LayerNorm(64)
        self.drop2 = nn.Dropout(0.3)
        self.fc1 = nn.Linear(64, 64)
        self.dfc1 = nn.Dropout(0.3)
        self.fc2 = nn.Linear(64, 32)
        self.dfc2 = nn.Dropout(0.3)
        self.out = nn.Linear(32, 1)
        self.act = nn.ReLU()

    def forward(self, x):  # x: (B, T, F)
        x = self.noise(x)
        x = x.transpose(1, 2)                 # (B, F, T) for Conv1d
        x = self.act(self.bn1(self.conv1(x)))
        x = self.act(self.bn2(self.conv2(x)))
        x = x.transpose(1, 2)                 # (B, T, 128)
        x, _ = self.lstm1(x)
        x = self.drop1(self.ln1(x))
        x, _ = self.lstm2(x)
        x = self.drop2(self.ln2(x[:, -1, :]))  # last timestep
        x = self.dfc1(self.act(self.fc1(x)))
        x = self.dfc2(self.act(self.fc2(x)))
        return self.out(x).squeeze(-1)


def standardize(train, *others):
    """Per-feature z-score using train mean/std (NaN-aware); NaN -> 0 (mean)."""
    flat = train.reshape(-1, train.shape[-1])
    mean = np.nanmean(flat, axis=0)
    std = np.nanstd(flat, axis=0)
    std[std == 0] = 1.0

    def apply(a):
        z = (a - mean) / std
        return np.nan_to_num(z, nan=0.0).astype(np.float32)

    return (apply(train), *[apply(o) for o in others])


def train_one(Xtr, ytr, Xva, yva, n_features, max_epochs=500, patience=60):
    set_seed(SEED)
    model = CNNLSTM(n_features)
    opt = torch.optim.Adam(model.parameters(), lr=4.5e-4, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=25, gamma=0.9)
    loss_fn = nn.MSELoss()

    Xtr_t, ytr_t = torch.tensor(Xtr), torch.tensor(ytr)
    Xva_t, yva_t = torch.tensor(Xva), torch.tensor(yva)
    n, bs = len(Xtr), 16
    best_val, best_state, wait = float("inf"), None, 0

    for _ in range(max_epochs):
        model.train()
        perm = torch.randperm(n)
        for k in range(0, n, bs):
            b = perm[k:k + bs]
            if len(b) < 2:  # BatchNorm needs >1 sample
                continue
            opt.zero_grad()
            loss = loss_fn(model(Xtr_t[b]), ytr_t[b])
            loss.backward()
            opt.step()
        sched.step()
        model.eval()
        with torch.no_grad():
            vloss = loss_fn(model(Xva_t), yva_t).item()
        if vloss < best_val - 1e-5:
            best_val, best_state, wait = vloss, {k: v.clone() for k, v in model.state_dict().items()}, 0
        else:
            wait += 1
            if wait >= patience:
                break
    if best_state:
        model.load_state_dict(best_state)
    return model


def run_config(name, feature_cols):
    X, y, groups, keys = load_sequences(feature_cols)
    years = np.unique(groups)
    oof = np.full(len(y), np.nan, dtype=np.float32)
    rng = np.random.RandomState(SEED)

    gkf = GroupKFold(n_splits=len(years))
    for tr, te in gkf.split(X, y, groups):
        # inner validation split (15%) for early stopping
        perm = rng.permutation(len(tr))
        n_val = max(8, int(0.15 * len(tr)))
        va_idx, tr_idx = tr[perm[:n_val]], tr[perm[n_val:]]
        Xtr, Xva, Xte = standardize(X[tr_idx], X[va_idx], X[te])
        model = train_one(Xtr, y[tr_idx], Xva, y[va_idx], len(feature_cols))
        model.eval()
        with torch.no_grad():
            oof[te] = model(torch.tensor(Xte)).numpy()
        print(f"    year {groups[te][0]} done", flush=True)

    rmse = float(np.sqrt(mean_squared_error(y, oof)))
    mae = float(mean_absolute_error(y, oof))
    r2 = float(r2_score(y, oof))
    print(f"  [{name}] RMSE {rmse:.3f} | MAE {mae:.3f} | R2 {r2:.3f}")
    return oof, (rmse, mae, r2), keys, y


def main():
    print(f"CNN-LSTM (recreated Test Four) | torch {torch.__version__} | leave-one-year-out\n")
    results = {}
    oofs = {}
    keys_ref = y_ref = None
    for name, cols in FEATURE_SETS.items():
        print(f"Running: {name}  (features: {cols})")
        oof, metrics, keys, y = run_config(name, cols)
        results[name] = metrics
        oofs[name] = oof
        keys_ref, y_ref = keys, y
        print()

    # Comparison table
    print(f"{'config':<22}{'RMSE':>8}{'MAE':>8}{'R2':>8}")
    print("-" * 46)
    for name, (rmse, mae, r2) in results.items():
        print(f"{name:<22}{rmse:>8.3f}{mae:>8.3f}{r2:>8.3f}")

    # Save paired OOF predictions for the significance test
    out = keys_ref[["municipality", "year", "season"]].copy()
    out["actual"] = y_ref
    out["pred_s2_only"] = oofs["S2 only (original)"]
    out["pred_s2_s1"] = oofs["S2+S1 (enhanced)"]
    out["abserr_s2_only"] = np.abs(out["actual"] - out["pred_s2_only"])
    out["abserr_s2_s1"] = np.abs(out["actual"] - out["pred_s2_s1"])
    out.to_csv(OOF_CSV, index=False)
    print(f"\nsaved paired OOF predictions -> {OOF_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
