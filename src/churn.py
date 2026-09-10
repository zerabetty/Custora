"""
Adım 5: Churn Tahmin Modellemesi (Supervised)

K-Means küme etiketleri ve CLTV metrikleri yeni öznitelik olarak kullanılır.

Model seçim süreci:
1. Mature müşteriler Train / Validation / Test olarak ayrılır.
2. Modeller Train setinde eğitilir.
3. Validation setinde karşılaştırılır ve en iyi model seçilir.
4. Seçilen model Train + Validation verisiyle yeniden eğitilir.
5. Test seti yalnızca final performans ölçümü için kullanılır.
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


# -------------------------------------------------------------------------
# SABİTLER
# -------------------------------------------------------------------------

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

# Mature müşteri evreninin %20'si final test setidir.
TEST_SIZE = 0.20

# Test ayrıldıktan sonra kalan %80'in %20'si validation olur.
# Böylece toplam dağılım yaklaşık:
# Train %64 - Validation %16 - Test %20
VALIDATION_SIZE = 0.20


# -------------------------------------------------------------------------
# AŞAMA 5A: ÖZNİTELİK HAZIRLIĞI
# -------------------------------------------------------------------------

def prepare_churn_features(customer_df: pd.DataFrame):
    print("\n" + "=" * 70)
    print("CHURN - ÖZNİTELİK HAZIRLIĞI")
    print("=" * 70)

    missing = [
        col
        for col in NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]
        if col not in customer_df.columns
    ]

    if missing:
        raise ValueError(
            f"Eksik kolonlar: {missing}. Adım 3 ve 4 tamamlanmış olmalı."
        )

    frame = customer_df[
        NUMERIC_FEATURES + CATEGORICAL_FEATURES + [TARGET]
    ].copy()

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
    engineered = [
        c
        for c in X.columns
        if c.startswith("cluster_")
        or c.startswith("cltv_")
        or c.startswith("exp_")
    ]
    print("  " + ", ".join(engineered))

    churn_rate = y.mean() * 100

    print("\nHedef dağılımı:")
    print(
        f"  Churn (1)    : {(y == 1).sum():,} "
        f"(%{churn_rate:.2f})"
    )
    print(
        f"  Retained (0) : {(y == 0).sum():,} "
        f"(%{100 - churn_rate:.2f})"
    )
    print(
        "  Dengesizlik  : "
        f"scale_pos_weight = n_neg / n_pos = "
        f"{(y == 0).sum() / (y == 1).sum():.3f}"
    )

    return X, y


# -------------------------------------------------------------------------
# AŞAMA 5B: TRAIN / VALIDATION / TEST AYRIMI
# -------------------------------------------------------------------------

def split_train_validation_test(
    X: pd.DataFrame,
    y: pd.Series,
):
    print("\n" + "=" * 70)
    print("CHURN - TRAIN / VALIDATION / TEST AYRIMI")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. Final test setini en başta ayır.
    # Bu veri model seçiminde kullanılmayacaktır.
    # -------------------------------------------------------------
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    # -------------------------------------------------------------
    # 2. Kalan veri Train ve Validation olarak ayrılır.
    # -------------------------------------------------------------
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val,
        y_train_val,
        test_size=VALIDATION_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_train_val,
    )

    print(
        f"\nTrain      : {len(X_train):,} "
        f"(churn %{y_train.mean() * 100:.2f})"
    )
    print(
        f"Validation : {len(X_val):,} "
        f"(churn %{y_val.mean() * 100:.2f})"
    )
    print(
        f"Test       : {len(X_test):,} "
        f"(churn %{y_test.mean() * 100:.2f})"
    )

    return (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test,
    )


# -------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# -------------------------------------------------------------------------

def _scale_pos_weight(y_train: pd.Series) -> float:
    n_pos = int((y_train == 1).sum())
    n_neg = int((y_train == 0).sum())

    return n_neg / n_pos


def _evaluate(
    y_true,
    y_prob,
    model_name: str,
) -> dict:
    y_pred = (y_prob >= 0.50).astype(int)

    metrics = {
        "model": model_name,
        "roc_auc": roc_auc_score(y_true, y_prob),
        "f1": f1_score(y_true, y_pred),
        "precision": precision_score(
            y_true,
            y_pred,
            zero_division=0,
        ),
        "recall": recall_score(
            y_true,
            y_pred,
            zero_division=0,
        ),
    }

    return metrics


# -------------------------------------------------------------------------
# AŞAMA 5C: MODEL EĞİTİM FONKSİYONLARI
# -------------------------------------------------------------------------

def train_logistic_regression(
    X_train,
    y_train,
    X_eval,
):
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_eval_scaled = scaler.transform(X_eval)

    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=RANDOM_STATE,
    )

    model.fit(
        X_train_scaled,
        y_train,
    )

    probability = model.predict_proba(
        X_eval_scaled
    )[:, 1]

    return model, probability, scaler


def train_lightgbm(
    X_train,
    y_train,
    X_eval,
    scale_pos_weight: float,
):
    model = LGBMClassifier(
        scale_pos_weight=scale_pos_weight,
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=RANDOM_STATE,
        verbosity=-1,
    )

    model.fit(
        X_train,
        y_train,
    )

    probability = model.predict_proba(
        X_eval
    )[:, 1]

    return model, probability


def train_xgboost(
    X_train,
    y_train,
    X_eval,
    scale_pos_weight: float,
):
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

    model.fit(
        X_train,
        y_train,
    )

    probability = model.predict_proba(
        X_eval
    )[:, 1]

    return model, probability


# -------------------------------------------------------------------------
# AŞAMA 5D: VALIDATION ÜZERİNDE MODEL KARŞILAŞTIRMA
# -------------------------------------------------------------------------

def evaluate_models(
    results: list[dict],
    dataset_name: str = "VALIDATION",
) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print(f"CHURN - MODEL KARŞILAŞTIRMA ({dataset_name})")
    print("=" * 70)

    metrics_df = pd.DataFrame(results)

    display_df = metrics_df.copy()

    for col in [
        "roc_auc",
        "f1",
        "precision",
        "recall",
    ]:
        display_df[col] = display_df[col].round(4)

    print(
        "\n"
        + display_df.to_string(index=False)
    )

    comparable = metrics_df[
        metrics_df["model"]
        != "Majority (her zaman churn)"
    ]

    best_name = comparable.loc[
        comparable["roc_auc"].idxmax(),
        "model",
    ]

    print(
        f"\n[+] En yüksek ROC-AUC: {best_name}"
    )

    return metrics_df


# -------------------------------------------------------------------------
# GÖRSELLEŞTİRME
# -------------------------------------------------------------------------

def plot_roc_curves(
    y_true,
    probas: dict,
    output_path: str = "churn_roc_curves.png",
):
    plt.figure(figsize=(8, 6))

    for name, y_prob in probas.items():
        fpr, tpr, _ = roc_curve(
            y_true,
            y_prob,
        )

        auc = roc_auc_score(
            y_true,
            y_prob,
        )

        plt.plot(
            fpr,
            tpr,
            label=f"{name} (AUC={auc:.3f})",
        )

    plt.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        color="gray",
        label="Rastgele",
    )

    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title(
        "Final Churn Modeli — Test ROC Eğrisi"
    )

    plt.legend()
    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=150,
    )

    plt.close()

    print(
        f"\n[+] ROC eğrisi kaydedildi: "
        f"{output_path}"
    )


def plot_feature_importance(
    model,
    feature_names,
    output_path: str = "churn_feature_importance.png",
):
    importances = pd.Series(
        model.feature_importances_,
        index=feature_names,
    )

    top = (
        importances
        .sort_values(ascending=True)
        .tail(15)
    )

    plt.figure(figsize=(8, 6))

    top.plot(kind="barh")

    plt.xlabel("Importance")
    plt.title(
        "Final Churn Modeli — Öznitelik Önemi"
    )

    plt.tight_layout()

    plt.savefig(
        output_path,
        dpi=150,
    )

    plt.close()

    print(
        f"[+] Öznitelik önemi kaydedildi: "
        f"{output_path}"
    )

    return importances.sort_values(
        ascending=False
    )


# -------------------------------------------------------------------------
# AŞAMA 5E: SEÇİLEN MODELİ TRAIN + VALIDATION İLE YENİDEN EĞİT
# -------------------------------------------------------------------------

def retrain_best_model(
    best_name: str,
    X_train_val: pd.DataFrame,
    y_train_val: pd.Series,
    X_test: pd.DataFrame,
):
    """
    Validation setinde seçilen modeli Train + Validation verisinin
    tamamı üzerinde yeniden eğitir ve yalnızca final Test setinde
    performans tahmini üretir.
    """

    pos_weight = _scale_pos_weight(
        y_train_val
    )

    if best_name == "Logistic Regression":
        model, test_prob, scaler = (
            train_logistic_regression(
                X_train_val,
                y_train_val,
                X_test,
            )
        )

        return model, test_prob, scaler

    if best_name == "LightGBM":
        model, test_prob = train_lightgbm(
            X_train_val,
            y_train_val,
            X_test,
            pos_weight,
        )

        return model, test_prob, None

    if best_name == "XGBoost":
        model, test_prob = train_xgboost(
            X_train_val,
            y_train_val,
            X_test,
            pos_weight,
        )

        return model, test_prob, None

    raise ValueError(
        f"Bilinmeyen model: {best_name}"
    )


# -------------------------------------------------------------------------
# AŞAMA 5F: TÜM MÜŞTERİLERİ SKORLAMA
# -------------------------------------------------------------------------

def score_customers(
    best_model,
    X: pd.DataFrame,
    scaler=None,
) -> pd.DataFrame:

    if scaler is not None:
        X_input = scaler.transform(X)
    else:
        X_input = X

    proba = best_model.predict_proba(
        X_input
    )[:, 1]

    scored = pd.DataFrame(
        {
            "churn_proba": proba,
            "churn_pred": (
                proba >= 0.50
            ).astype(int),
        },
        index=X.index,
    )

    return scored


# -------------------------------------------------------------------------
# AŞAMA 5: ANA CHURN PIPELINE
# -------------------------------------------------------------------------

def run_churn_modeling(
    customer_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Adım 5 orkestrasyonu.

    Model eğitimi yalnızca mature müşteriler üzerinde yapılır.

    Train:
        Model öğrenir.

    Validation:
        Modeller karşılaştırılır ve en iyi model seçilir.

    Test:
        Yalnızca seçilmiş final modelin bağımsız performansı ölçülür.

    Sonrasında seçilmiş model müşteri portföyüne churn skoru üretir.
    """

    X, y = prepare_churn_features(
        customer_df
    )

    # -------------------------------------------------------------
    # MATURITY FILTER
    # -------------------------------------------------------------

    matured_mask = (
        customer_df["is_matured"] == 1
    )

    n_matured = int(
        matured_mask.sum()
    )

    n_unmatured = (
        len(customer_df) - n_matured
    )

    print("\n" + "=" * 70)
    print(
        "CHURN - MODELLEME EVRENİ "
        "(MATURITY FILTER)"
    )
    print("=" * 70)

    print(
        f"Toplam portföy           : "
        f"{len(customer_df):,} müşteri"
    )

    print(
        f"Eğitim / Değerlendirme   : "
        f"{n_matured:,} olgunlaşmış müşteri "
        f"(%{n_matured / len(customer_df) * 100:.2f})"
    )

    print(
        f"İzole edilen taze kitle  : "
        f"{n_unmatured:,} taze müşteri "
        f"(%{n_unmatured / len(customer_df) * 100:.2f})"
    )

    X_matured = X[
        matured_mask
    ].copy()

    y_matured = y[
        matured_mask
    ].copy()

    # -------------------------------------------------------------
    # TRAIN / VALIDATION / TEST
    # -------------------------------------------------------------

    (
        X_train,
        X_val,
        X_test,
        y_train,
        y_val,
        y_test,
    ) = split_train_validation_test(
        X_matured,
        y_matured,
    )

    pos_weight = _scale_pos_weight(
        y_train
    )

    print("\n" + "=" * 70)
    print("CHURN - MODEL EĞİTİMİ")
    print("=" * 70)

    print(
        f"\nscale_pos_weight (train): "
        f"{pos_weight:.3f}"
    )

    print(
        "Modeller Train setinde eğitiliyor; "
        "Validation seti model seçimi için kullanılıyor."
    )

    # -------------------------------------------------------------
    # BASELINE - VALIDATION
    # -------------------------------------------------------------

    majority_prob_val = np.ones(
        len(y_val),
        dtype=float,
    )

    baseline_metrics = _evaluate(
        y_val,
        majority_prob_val,
        "Majority (her zaman churn)",
    )

    # -------------------------------------------------------------
    # 3 MODEL TRAIN'DE EĞİTİLİR, VALIDATION'DA ÖLÇÜLÜR
    # -------------------------------------------------------------

    lr_model, lr_val_prob, lr_scaler = (
        train_logistic_regression(
            X_train,
            y_train,
            X_val,
        )
    )

    lgb_model, lgb_val_prob = (
        train_lightgbm(
            X_train,
            y_train,
            X_val,
            pos_weight,
        )
    )

    xgb_model, xgb_val_prob = (
        train_xgboost(
            X_train,
            y_train,
            X_val,
            pos_weight,
        )
    )

    validation_metrics = [
        baseline_metrics,
        _evaluate(
            y_val,
            lr_val_prob,
            "Logistic Regression",
        ),
        _evaluate(
            y_val,
            lgb_val_prob,
            "LightGBM",
        ),
        _evaluate(
            y_val,
            xgb_val_prob,
            "XGBoost",
        ),
    ]

    metrics_df = evaluate_models(
        validation_metrics,
        dataset_name="VALIDATION",
    )

    # -------------------------------------------------------------
    # VALIDATION'A GÖRE EN İYİ MODELİ SEÇ
    # -------------------------------------------------------------

    comparable = metrics_df[
        metrics_df["model"]
        != "Majority (her zaman churn)"
    ]

    best_name = comparable.loc[
        comparable["roc_auc"].idxmax(),
        "model",
    ]

    print("\n" + "=" * 70)
    print("CHURN - MODEL SEÇİMİ")
    print("=" * 70)

    print(
        f"\n[+] Validation sonucuna göre "
        f"seçilen model: {best_name}"
    )

    # -------------------------------------------------------------
    # TRAIN + VALIDATION VERİLERİNİ BİRLEŞTİR
    # -------------------------------------------------------------

    X_train_val = pd.concat(
        [
            X_train,
            X_val,
        ],
        axis=0,
    )

    y_train_val = pd.concat(
        [
            y_train,
            y_val,
        ],
        axis=0,
    )

    print(
        f"[+] Final model yeniden eğitim verisi: "
        f"{len(X_train_val):,} müşteri"
    )

    # -------------------------------------------------------------
    # SEÇİLEN MODELİ TRAIN + VALIDATION ÜZERİNDE YENİDEN EĞİT
    # TEST'E İLK KEZ BURADA BAK
    # -------------------------------------------------------------

    (
        best_model,
        test_prob,
        best_scaler,
    ) = retrain_best_model(
        best_name,
        X_train_val,
        y_train_val,
        X_test,
    )

    final_test_metrics = _evaluate(
        y_test,
        test_prob,
        best_name,
    )

    print("\n" + "=" * 70)
    print("CHURN - FINAL TEST PERFORMANSI")
    print("=" * 70)

    print(
        f"\nModel     : "
        f"{final_test_metrics['model']}"
    )

    print(
        f"ROC-AUC   : "
        f"{final_test_metrics['roc_auc']:.4f}"
    )

    print(
        f"F1        : "
        f"{final_test_metrics['f1']:.4f}"
    )

    print(
        f"Precision : "
        f"{final_test_metrics['precision']:.4f}"
    )

    print(
        f"Recall    : "
        f"{final_test_metrics['recall']:.4f}"
    )

    # -------------------------------------------------------------
    # FINAL TEST ROC
    # -------------------------------------------------------------

    plot_roc_curves(
        y_test,
        {
            best_name: test_prob,
        },
    )

    # -------------------------------------------------------------
    # FEATURE IMPORTANCE
    # -------------------------------------------------------------

    if hasattr(
        best_model,
        "feature_importances_",
    ):
        importances = (
            plot_feature_importance(
                best_model,
                X.columns,
            )
        )

        print(
            "\nEn etkili 10 öznitelik:"
        )

        print(
            importances
            .head(10)
            .round(4)
            .to_string()
        )

        cluster_importance = (
            importances[
                importances.index.str.startswith(
                    "cluster_"
                )
            ].sum()
        )

        cltv_importance = (
            importances[
                importances.index.str.contains(
                    "cltv_|exp_purchases|exp_average"
                )
            ].sum()
        )

        print(
            f"\nK-Means cluster toplam importance : "
            f"{cluster_importance:.4f}"
        )

        print(
            f"CLTV metrikleri toplam importance : "
            f"{cltv_importance:.4f}"
        )

    # -------------------------------------------------------------
    # MÜŞTERİ SKORLAMA
    # -------------------------------------------------------------

    scored = score_customers(
        best_model,
        X,
        best_scaler,
    )

    result = customer_df.copy()

    result["churn_proba"] = (
        scored["churn_proba"]
    )

    result["churn_pred"] = (
        scored["churn_pred"]
    )

    result["churn_model"] = (
        best_name
    )

    print(
        "\nGenel portföy churn skoru özeti:"
    )

    print(
        result["churn_proba"]
        .describe()
        .round(4)
        .to_string()
    )

    print(
        "\nOlgunlaşmış portföy churn skoru özeti "
        "(is_matured == 1):"
    )

    print(
        result.loc[
            matured_mask,
            "churn_proba",
        ]
        .describe()
        .round(4)
        .to_string()
    )

    print(
        f"\n[+] Skorlayan final model: "
        f"{best_name}"
    )

    return result