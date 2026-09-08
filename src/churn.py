"""
Adım 5: Churn Tahmin Modellemesi (Supervised)
K-Means küme etiketleri ve CLTV metrikleri yeni öznitelik olarak kullanılır.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    roc_curve,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier


NUMERIC_FEATURES = [
    "recency_days",
    "customer_age_t_days",
    "total_orders",
    "total_monetary",
    "avg_monetary",
    "avg_basket_items",
    "discount_ratio",
    "ratio_bikes",
    "ratio_accessories",
    "ratio_clothing",
    "ratio_components",
    "is_matured",
    "cltv_6m",
    "exp_purchases_6m",
    "exp_average_profit",
]

CATEGORICAL_FEATURES = [
    "cluster",
    "cltv_segment",
]

TARGET = "is_churn"
RANDOM_STATE = 42
TEST_SIZE = 0.20


def prepare_churn_features(customer_df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("CHURN - ÖZNİTELİK HAZIRLIĞI")
    print("=" * 70)

    missing = [
        col for col in NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]
        if col not in customer_df.columns
    ]
    if missing:
        raise ValueError(f"Eksik kolonlar: {missing}. Adım 3 ve 4 tamamlanmış olmalı.")

    frame = customer_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]].copy()
    frame["cluster"] = frame["cluster"].astype(str)
    frame["cltv_segment"] = frame["cltv_segment"].astype(str)

    y = frame[TARGET].astype(int)
    X = pd.get_dummies(
        frame.drop(columns=[TARGET]),
        columns=CATEGORICAL_FEATURES,
        drop_first=False,
    )
    X = X.astype(float)

    print(f"\nMüşteri sayısı        : {len(frame):,}")
    print(f"Öznitelik sayısı      : {X.shape[1]}")
    print("\nSayısal feature'lar:")
    print("  " + ", ".join(NUMERIC_FEATURES))
    print("\nKategorik feature'lar (one-hot):")
    print("  " + ", ".join(CATEGORICAL_FEATURES))
    print("\nK-Means / CLTV kolonları:")
    engineered = [c for c in X.columns if c.startswith("cluster_") or c.startswith("cltv_") or c.startswith("exp_")]
    print("  " + ", ".join(engineered))

    churn_rate = y.mean() * 100
    print("\nHedef dağılımı:")
    print(f"  Churn (1)    : {(y == 1).sum():,} (%{churn_rate:.2f})")
    print(f"  Retained (0) : {(y == 0).sum():,} (%{100 - churn_rate:.2f})")
    print(
        "  Dengesizlik  : "
        f"scale_pos_weight = n_neg / n_pos = {(y == 0).sum() / (y == 1).sum():.3f}"
    )

    return X, y


def split_train_test(X: pd.DataFrame, y: pd.Series):
    print("\n" + "=" * 70)
    print("CHURN - TRAIN / TEST AYRIMI")
    print("=" * 70)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    print(f"\nTrain : {len(X_train):,}  (churn %{y_train.mean() * 100:.2f})")
    print(f"Test  : {len(X_test):,}  (churn %{y_test.mean() * 100:.2f})")
    return X_train, X_test, y_train, y_test


def _scale_pos_weight(y_train: pd.Series) -> float:
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())
    return n_neg / n_pos


def _evaluate(y_true, y_prob, model_name: str) -> dict:
    y_pred = (y_prob >= 0.50).astype(int)
    metrics = {
        "model": model_name,
        "roc_auc": roc_auc_score(y_true, y_prob),
        "f1": f1_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
    }
    return metrics


def train_logistic_regression(X_train, y_train, X_test):
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
    )
    model.fit(X_train_scaled, y_train)
    return model, model.predict_proba(X_test_scaled)[:, 1], scaler


def train_lightgbm(X_train, y_train, X_test, scale_pos_weight: float):
    model = LGBMClassifier(
        scale_pos_weight=scale_pos_weight,
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=RANDOM_STATE,
        verbosity=-1,
    )
    model.fit(X_train, y_train)
    return model, model.predict_proba(X_test)[:, 1]


def train_xgboost(X_train, y_train, X_test, scale_pos_weight: float):
    model = XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        n_estimators=300,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="auc",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model, model.predict_proba(X_test)[:, 1]


def evaluate_models(results: list[dict]) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("CHURN - MODEL KARŞILAŞTIRMA (TEST)")
    print("=" * 70)

    metrics_df = pd.DataFrame(results)
    display_df = metrics_df.copy()
    for col in ["roc_auc", "f1", "precision", "recall"]:
        display_df[col] = display_df[col].round(4)

    print("\n" + display_df.to_string(index=False))
    best_name = metrics_df.loc[metrics_df["roc_auc"].idxmax(), "model"]
    print(f"\n[+] En yüksek ROC-AUC: {best_name}")
    return metrics_df


def plot_roc_curves(y_test, probas: dict, output_path: str = "churn_roc_curves.png"):
    plt.figure(figsize=(8, 6))
    for name, y_prob in probas.items():
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        auc = roc_auc_score(y_test, y_prob)
        plt.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")

    plt.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Rastgele")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Churn Modelleri — ROC Eğrileri")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"\n[+] ROC eğrileri kaydedildi: {output_path}")


def plot_feature_importance(model, feature_names, output_path: str = "churn_feature_importance.png"):
    importances = pd.Series(model.feature_importances_, index=feature_names)
    top = importances.sort_values(ascending=True).tail(15)

    plt.figure(figsize=(8, 6))
    top.plot(kind="barh")
    plt.xlabel("Importance")
    plt.title("Churn Modeli — Öznitelik Önemi")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"[+] Öznitelik önemi kaydedildi: {output_path}")
    return importances.sort_values(ascending=False)


def score_customers(best_model, X: pd.DataFrame, scaler=None) -> pd.DataFrame:
    if scaler is not None:
        X_input = scaler.transform(X)
    else:
        X_input = X

    proba = best_model.predict_proba(X_input)[:, 1]
    scored = pd.DataFrame(
        {
            "churn_proba": proba,
            "churn_pred": (proba >= 0.50).astype(int),
        },
        index=X.index,
    )
    return scored


def run_churn_modeling(customer_df: pd.DataFrame) -> pd.DataFrame:
    """Adım 5 orkestrasyonu. Test metriklerini yazdırır, tüm müşterilere skor atar."""
    X, y = prepare_churn_features(customer_df)
    X_train, X_test, y_train, y_test = split_train_test(X, y)
    pos_weight = _scale_pos_weight(y_train)

    print("\n" + "=" * 70)
    print("CHURN - MODEL EĞİTİMİ")
    print("=" * 70)
    print(f"\nscale_pos_weight (train): {pos_weight:.3f}")
    print("SMOTE kullanılmadı; dengesizlik class_weight / scale_pos_weight ile giderildi.")

    majority_prob = np.ones(len(y_test), dtype=float)
    baseline_metrics = _evaluate(y_test, majority_prob, "Majority (her zaman churn)")

    lr_model, lr_prob, scaler = train_logistic_regression(X_train, y_train, X_test)
    lgb_model, lgb_prob = train_lightgbm(X_train, y_train, X_test, pos_weight)
    xgb_model, xgb_prob = train_xgboost(X_train, y_train, X_test, pos_weight)

    metrics = [
        baseline_metrics,
        _evaluate(y_test, lr_prob, "Logistic Regression"),
        _evaluate(y_test, lgb_prob, "LightGBM"),
        _evaluate(y_test, xgb_prob, "XGBoost"),
    ]
    metrics_df = evaluate_models(metrics)

    plot_roc_curves(
        y_test,
        {
            "Logistic Regression": lr_prob,
            "LightGBM": lgb_prob,
            "XGBoost": xgb_prob,
        },
    )

    trained = {
        "Logistic Regression": (lr_model, scaler),
        "LightGBM": (lgb_model, None),
        "XGBoost": (xgb_model, None),
    }
    comparable = metrics_df[metrics_df["model"] != "Majority (her zaman churn)"]
    best_name = comparable.loc[comparable["roc_auc"].idxmax(), "model"]
    best_model, best_scaler = trained[best_name]

    if hasattr(best_model, "feature_importances_"):
        importances = plot_feature_importance(best_model, X.columns)
        print("\nEn etkili 10 öznitelik:")
        print(importances.head(10).round(4).to_string())

        cluster_importance = importances[importances.index.str.startswith("cluster_")].sum()
        cltv_importance = importances[
            importances.index.str.contains("cltv_|exp_purchases|exp_average")
        ].sum()
        print(f"\nK-Means cluster toplam importance : {cluster_importance:.4f}")
        print(f"CLTV metrikleri toplam importance : {cltv_importance:.4f}")

    scored = score_customers(best_model, X, best_scaler)
    result = customer_df.copy()
    result["churn_proba"] = scored["churn_proba"]
    result["churn_pred"] = scored["churn_pred"]
    result["churn_model"] = best_name

    print("\nPortföy churn skoru özeti:")
    print(result["churn_proba"].describe().round(4).to_string())
    print(f"\n[+] Skorlayan model: {best_name}")

    return result
