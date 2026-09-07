"""
AdventureWorks Uçtan Uca Veri Bilimi ve Karar Destek Sistemi
Ana Orkestratör Pipeline (main.py)
"""

import sys
import time
from pathlib import Path
import pandas as pd
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 30)
pd.set_option("display.float_format", lambda x: f"{x:.2f}")

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
from src.segmentation import (
    evaluate_kmeans_clusters,
    fit_kmeans_model,
    profile_clusters,
    analyze_cluster_medians,
    assign_cluster_names,
    visualize_clusters_pca
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

    # -------------------------------------------------------------------------
    # ADIM 3: K-Means Müşteri Segmentasyonu
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # AŞAMA 3A: Optimal K Analizi
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3A] K-MEANS OPTIMAL K ANALİZİ")

    kmeans_evaluation = evaluate_kmeans_clusters(
        kmeans_scaled_df
    )

    # -------------------------------------------------------------------------
    # AŞAMA 3B: Final K-Means Modeli ve Cluster Atama
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3B] FINAL K-MEANS MODELİ")

    kmeans_model, cluster_labels, cluster_summary = fit_kmeans_model(
        kmeans_scaled_df,
        n_clusters=4
    )

    # -------------------------------------------------------------------------
    # AŞAMA 3C: Cluster Profiling
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3C] CLUSTER PROFILING")

    customer_clustered_df, cluster_profile = profile_clusters(
        customer_df,
        cluster_labels
    )

    # -------------------------------------------------------------------------
    # AŞAMA 3D: Cluster Median Analizi
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3D] CLUSTER MEDIAN ANALİZİ")

    cluster_medians = analyze_cluster_medians(
        customer_clustered_df
    )

    # -------------------------------------------------------------------------
    # AŞAMA 3E: Business Segment İsimlendirme
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3E] BUSINESS SEGMENT İSİMLENDİRME")

    customer_clustered_df, segment_summary = assign_cluster_names(
        customer_clustered_df
    )

    # -------------------------------------------------------------------------
    # AŞAMA 3F: PCA Görselleştirme
    # -------------------------------------------------------------------------
    print("\n>>> [AŞAMA 3F] PCA GÖRSELLEŞTİRME")

    pca_df, pca_model = visualize_clusters_pca(
        kmeans_scaled_df,
        cluster_labels
    )

    # -------------------------------------------------------------------------
    # Analitik Veri Setinin Güncellenmesi (Cluster ve Segment Bilgileri ile)
    # -------------------------------------------------------------------------
    customer_clustered_df.to_csv(FEATURES_PATH, index=True)
    print(f"\n[+] Analitik müşteri tablosu (Cluster ve Segmentler ile) güncellendi: {FEATURES_PATH}")

if __name__ == "__main__":
    main()
