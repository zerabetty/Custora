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
from src.preprocessing import run_eda, analyze_purchase_intervals

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


if __name__ == "__main__":
    main()
