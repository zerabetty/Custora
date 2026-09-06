"""
AdventureWorks Uçtan Uca Veri Bilimi ve Karar Destek Sistemi
Ana Orkestratör Pipeline (main.py)
"""

import sys
import time
from pathlib import Path
import pandas as pd

# Proje dizinini ve src paketini dinamik olarak path'e ekle
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.data_loader import run_data_loader
from src.preprocessing import (
    run_eda,
    analyze_purchase_intervals,
    compare_churn_horizons,
    compare_rfm_churn_horizons,
    analyze_temporal_customer_structure,
    analyze_numeric_distributions,
    analyze_outliers,
    evaluate_log_transform,
    analyze_feature_correlations,
    prepare_kmeans_features
)

# -----------------------------------------------------------------------------
# Global Yapılandırma ve Parametreler
# -----------------------------------------------------------------------------
DATA_PATH = BASE_DIR / "adventureworks_data.csv"
FEATURES_PATH = BASE_DIR / "customer_features.csv"
CUTOFF_DATE = pd.to_datetime("2024-12-29")  # 6 aylık hedef pencere ayrımı


def main():
    pipeline_start = time.time()
    print("=" * 70)
    print("ADVENTUREWORKS VERİ BİLİMİ & KARAR DESTEK SİSTEMİ BAŞLATILIYOR")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # ADIM 1: Veri Yükleme, Zaman Pencereleri & Analitik Tablo Çıkarımı
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 1/7] VERİ HAZIRLIĞI VE ÖZNİTELİK MÜHENDİSLİĞİ")
    customer_df = run_data_loader(
        data_path=DATA_PATH,
        output_path=FEATURES_PATH,
        cutoff_date=CUTOFF_DATE
    )

    print("\n" + "=" * 70)
    print(f"[+] Pipeline ilk aşaması başarıyla tamamlandı. (Süre: {time.time() - pipeline_start:.2f}s)")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # ADIM 2: Keşifçi Veri Analizi (EDA)
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 2/7] KEŞİFÇİ VERİ ANALİZİ")

    customer_df = run_eda(customer_df)

    print("\n>>> [AŞAMA 2B] SATIN ALMA ARALIKLARI ANALİZİ")
    transaction_df = pd.read_csv(DATA_PATH)
    purchase_intervals = analyze_purchase_intervals(transaction_df)

    # -------------------------------------------------------------------------
    # ADIM 2C: Alternatif Churn Hedef Pencerelerinin Karşılaştırılması
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 2C] CHURN PENCERESİ KARŞILAŞTIRMASI")

    churn_horizon_results = compare_churn_horizons(
        transaction_df,
        horizons=(6, 9, 12)
    )

    # -------------------------------------------------------------------------
    # ADIM 2D: RFM Segmentleri Bazında Churn Horizon Analizi
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 2D] RFM × CHURN PENCERESİ ANALİZİ")

    rfm_horizon_results, rfm_churn_pivot = compare_rfm_churn_horizons(
        transaction_df,
        horizons=(6, 9, 12)
    )

    # -------------------------------------------------------------------------
    # ADIM 2E: Zamansal Müşteri ve Cohort Yapısı
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 2E] ZAMANSAL MÜŞTERİ VE COHORT ANALİZİ")

    monthly_summary, cohort_year, order_count_distribution = (
        analyze_temporal_customer_structure(transaction_df)
    )

    # -------------------------------------------------------------------------
    # ADIM 2F: Sayısal Değişkenlerin Dağılım Analizi
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 2F] SAYISAL DAĞILIM VE SKEWNESS ANALİZİ")

    distribution_summary = analyze_numeric_distributions(customer_df)

    # -------------------------------------------------------------------------
    # ADIM 2G: Outlier / Quantile Analizi
    # -------------------------------------------------------------------------

    print("\n>>> [AŞAMA 2G] OUTLIER / QUANTILE ANALİZİ")

    outlier_summary = analyze_outliers(customer_df)

    # -------------------------------------------------------------------------
    # ADIM 2H: LOG1P DÖNÜŞÜMÜ ETKİ ANALİZİ
    # -------------------------------------------------------------------------
    
    print("\n>>> [AŞAMA 2H] LOG1P DÖNÜŞÜMÜ ETKİ ANALİZİ")

    log_transform_summary = evaluate_log_transform(customer_df)

    # -------------------------------------------------------------------------
    # ADIM 2I: FEATURE CORRELATION / REDUNDANCY ANALİZİ
    # -------------------------------------------------------------------------
    
    print("\n>>> [AŞAMA 2I] FEATURE CORRELATION / REDUNDANCY ANALİZİ")

    corr_matrix, high_corr_pairs = analyze_feature_correlations(customer_df)

    # -------------------------------------------------------------------------
    # ADIM 2J: K-MEANS FEATURE PREPROCESSING
    # -------------------------------------------------------------------------
    
    print("\n>>> [AŞAMA 2J] K-MEANS FEATURE PREPROCESSING")

    kmeans_df, kmeans_scaled_df, scaler = prepare_kmeans_features(
        customer_df
    )


if __name__ == "__main__":
    main()
