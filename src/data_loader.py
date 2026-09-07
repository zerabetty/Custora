"""
Adım 1: Veri Yükleme, Zaman Pencereleri Ayrımı & Analitik Tablo (Feature Extraction)
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd

# Kullanıcı tarafından tanımlanan RFM Segment Haritası
RFM_SEGMENT_MAP = {
    r"[1-2][1-2]": "hibernating",
    r"[1-2][3-4]": "at_Risk",
    r"[1-2]5": "cant_lose",
    r"3[1-2]": "about_to_sleep",
    r"33": "need_attention",
    r"[3-4][4-5]": "loyal_customers",
    r"41": "promising",
    r"51": "new_customers",
    r"[4-5][2-3]": "potential_loyalists",
    r"5[4-5]": "champions",
}


def load_and_preprocess_transactions(file_path: Path) -> pd.DataFrame:
    """Ham CSV verisini okur, veri tiplerini düzenler."""
    print(f"[*] Ham veri okunuyor: {file_path}")
    df = pd.read_csv(file_path, parse_dates=["orderdate"])
    print(f"[+] Veri okundu: {len(df):,} satır, {df['customerid'].nunique():,} tekil müşteri.")
    return df


def split_time_windows(df: pd.DataFrame, cutoff: pd.Timestamp):
    """Veriyi gözlem (feature extraction) ve hedef (churn target) pencerelerine ayırır."""
    obs_df = df[df["orderdate"] < cutoff].copy()
    target_df = df[df["orderdate"] >= cutoff].copy()

    print("\n" + "=" * 60)
    print("ZAMAN PENCERELERİ ÖZETİ (DATA LEAKAGE KORUMASI)")
    print("=" * 60)
    print(f"Cut-off Tarihi        : {cutoff.strftime('%Y-%m-%d')}")
    print(f"Gözlem Penceresi      : {obs_df['orderdate'].min().strftime('%Y-%m-%d')} - {obs_df['orderdate'].max().strftime('%Y-%m-%d')}")
    print(f"Gözlem Sipariş Sayısı : {obs_df['salesorderid'].nunique():,} adet")
    print(f"Gözlem Müşteri Sayısı : {obs_df['customerid'].nunique():,} müşteri")
    print(f"Hedef Penceresi       : {target_df['orderdate'].min().strftime('%Y-%m-%d')} - {target_df['orderdate'].max().strftime('%Y-%m-%d')}")
    print(f"Hedef Sipariş Sayısı  : {target_df['salesorderid'].nunique():,} adet")
    return obs_df, target_df


def extract_customer_features(obs_df: pd.DataFrame, target_df: pd.DataFrame, cutoff: pd.Timestamp) -> pd.DataFrame:
    """
    Gözlem penceresinden müşteri bazlı RFM, Lifetimes, sepet davranışı
    ve kategori harcama dağılımlarını çıkarır. Hedef pencereden Churn etiketler.
    """
    print("\n[*] Müşteri bazlı analitik değişkenler hesaplanıyor...")

    # 1. Müşteri İletişim ve Profil Bilgisi
    cust_profile = obs_df.groupby("customerid").agg({
        "customer_name": "first",
        "emailaddress": "first",
        "territory_name": "first",
    })

    # 2. Sipariş Düzeyinde RFM ve Lifetimes Metrikleri
    orders = obs_df.drop_duplicates(subset=["salesorderid"])
    order_agg = orders.groupby("customerid").agg(
        first_order_date=("orderdate", "min"),
        last_order_date=("orderdate", "max"),
        total_orders=("salesorderid", "count"),
        total_monetary=("order_subtotal", "sum"),
        avg_monetary=("order_subtotal", "mean"),
    )

    # Gün cinsinden zaman farkları
    order_agg["recency_days"] = (cutoff - order_agg["last_order_date"]).dt.days
    order_agg["customer_age_t_days"] = (cutoff - order_agg["first_order_date"]).dt.days
    order_agg["lifetimes_recency_days"] = (order_agg["last_order_date"] - order_agg["first_order_date"]).dt.days
    order_agg["repeat_frequency"] = order_agg["total_orders"] - 1

    # RFM Skorlama (1-5 Arası)
    order_agg["recency_score"] = pd.qcut(order_agg["recency_days"], 5, labels=[5, 4, 3, 2, 1])
    order_agg["frequency_score"] = pd.cut(
        order_agg["total_orders"],
        bins=[0, 1, 2, 3, 5, np.inf],
        labels=[1, 2, 3, 4, 5]
    ).astype(int)
    order_agg["monetary_score"] = pd.qcut(order_agg["total_monetary"], 5, labels=[1, 2, 3, 4, 5])

    # RFM Skoru ve Regex Segment Eşleştirmesi
    order_agg["rfm_score"] = order_agg["recency_score"].astype(str) + order_agg["frequency_score"].astype(str)
    order_agg["rfm_segment"] = order_agg["rfm_score"].replace(RFM_SEGMENT_MAP, regex=True)

    # 3. Satır/Sepet Kalemi Düzeyinde Davranışsal & Kategori Metrikleri
    obs_df["item_spend"] = obs_df["orderqty"] * obs_df["unitprice"] * (1 - obs_df["unitpricediscount"])
    obs_df["is_discounted"] = (obs_df["unitpricediscount"] > 0).astype(int)

    # 4 Kategori bazlı harcamaları vektörel ayırma
    for cat in ["Bikes", "Accessories", "Clothing", "Components"]:
        obs_df[f"spend_{cat.lower()}"] = np.where(obs_df["category_name"] == cat, obs_df["item_spend"], 0.0)

    detail_agg = obs_df.groupby("customerid").agg(
        total_quantity=("orderqty", "sum"),
        discount_ratio=("is_discounted", "mean"),
        spend_bikes=("spend_bikes", "sum"),
        spend_accessories=("spend_accessories", "sum"),
        spend_clothing=("spend_clothing", "sum"),
        spend_components=("spend_components", "sum"),
    )

    # 4. Tabloların Birleştirilmesi
    customer_df = cust_profile.join(order_agg).join(detail_agg)

    # Ortalama sepet büyüklüğü (ürün adedi)
    customer_df["avg_basket_items"] = (customer_df["total_quantity"] / customer_df["total_orders"]).round(2)

    # Kategori Harcama Oranları (% Dağılım)
    for cat in ["bikes", "accessories", "clothing", "components"]:
        customer_df[f"ratio_{cat}"] = (
            customer_df[f"spend_{cat}"] / customer_df["total_monetary"].replace(0, np.nan)
        ).fillna(0).round(4)

    # 5. Hedef Değişken (Supervised Target: is_churn)
    target_buyers = set(target_df["customerid"].unique())
    customer_df["is_churn"] = (~customer_df.index.isin(target_buyers)).astype(int)

    # 6. Olgunluk Filtresi (Maturity Buffer: Yaş >= 180 gün VEYA en az 2 sipariş)
    customer_df["is_matured"] = (
        (customer_df["customer_age_t_days"] >= 180) |
        (customer_df["total_orders"] >= 2)
    ).astype(int)

    return customer_df


def print_step1_report(df: pd.DataFrame):
    """Analitik tablonun dağılımlarını ve istatistiklerini raporlar."""
    print("\n" + "=" * 60)
    print("ADIM 1 ÇIKTI RAPORU & DOĞRULAMA")
    print("=" * 60)
    base_cols = ["customer_name", "emailaddress", "territory_name"]
    target_col = ["is_churn"]
    filter_col = ["is_matured"]
    engineered_cols = [c for c in df.columns if c not in base_cols and c not in target_col and c not in filter_col]

    print(f"Toplam Analitik Müşteri Sayısı : {len(df):,}")
    print(f"Toplam Sütun Sayısı             : {df.shape[1]}")
    print(f"  - Temel Profil Bilgileri      : {len(base_cols)} (İsim, E-posta, Bölge)")
    print(f"  - Türetilen Öznitelik Sayısı  : {len(engineered_cols)}")
    print(f"  - Hedef Değişken (Target)     : {len(target_col)} (is_churn)")
    print(f"  - Olgunluk Filtresi (Maturity): {len(filter_col)} (is_matured)")

    # Olgunluk Dağılımı
    matured_count = df["is_matured"].sum()
    unmatured_count = len(df) - matured_count
    print("\n[+] Müşteri Olgunluk (Maturity) Dağılımı:")
    print(f"  - Olgun Müşteriler (Yaş >= 180g veya 2+ Sipariş) : {matured_count:,} (%{matured_count / len(df) * 100:.2f})")
    print(f"  - Taze Müşteriler (Döngüsü Henüz Dolmamış)        : {unmatured_count:,} (%{unmatured_count / len(df) * 100:.2f})")

    churn_counts = df["is_churn"].value_counts()
    churn_ratios = df["is_churn"].value_counts(normalize=True) * 100
    print("\n[+] Toplam Portföy Hedef Değişken (Churn) Dağılımı:")
    print(f"  - Churn (1)     : {churn_counts.get(1, 0):,} müşteri (%{churn_ratios.get(1, 0):.2f})")
    print(f"  - Retained (0)  : {churn_counts.get(0, 0):,} müşteri (%{churn_ratios.get(0, 0):.2f})")

    # Olgun Kitlede Churn
    matured_df = df[df["is_matured"] == 1]
    mat_churn_counts = matured_df["is_churn"].value_counts()
    mat_churn_ratios = matured_df["is_churn"].value_counts(normalize=True) * 100
    print("\n[+] OLGUNLAŞMIŞ PORTFÖY Hedef Değişken (Churn) Dağılımı (Modelleme Evreni):")
    print(f"  - Churn (1)     : {mat_churn_counts.get(1, 0):,} müşteri (%{mat_churn_ratios.get(1, 0):.2f})")
    print(f"  - Retained (0)  : {mat_churn_counts.get(0, 0):,} müşteri (%{mat_churn_ratios.get(0, 0):.2f})")

    print("\n[+] RFM Segmentleri Bazında Dağılım ve Churn Oranları (Olgun Müşteri Ayrımı ile):")
    segment_summary = df.groupby("rfm_segment").agg(
        musteri_sayisi=("recency_days", "count"),
        olgun_sayisi=("is_matured", "sum"),
        ort_recency=("recency_days", "mean"),
        ort_siparis=("total_orders", "mean"),
        ort_ciro=("total_monetary", "mean"),
        toplam_churn_orani=("is_churn", "mean"),
    ).reset_index()
    
    # Olgun olanlardaki churn oranı
    mat_segment_churn = (
        df[df["is_matured"] == 1]
        .groupby("rfm_segment")["is_churn"]
        .mean()
        .rename("olgun_churn_orani")
    )
    segment_summary = segment_summary.merge(mat_segment_churn, on="rfm_segment", how="left")

    segment_summary["toplam_churn_orani"] = (segment_summary["toplam_churn_orani"] * 100).round(2)
    segment_summary["olgun_churn_orani"] = (segment_summary["olgun_churn_orani"] * 100).round(2)
    segment_summary["ort_recency"] = segment_summary["ort_recency"].round(1)
    segment_summary["ort_siparis"] = segment_summary["ort_siparis"].round(2)
    segment_summary["ort_ciro"] = segment_summary["ort_ciro"].round(2)
    segment_summary = segment_summary.sort_values(by="musteri_sayisi", ascending=False)
    print(segment_summary.to_string(index=False))


def run_data_loader(data_path: Path, output_path: Path, cutoff_date: pd.Timestamp) -> pd.DataFrame:
    """Tüm Adım 1 sürecini yürüten ana modül fonksiyonu."""
    # 1. Ham Veriyi Yükle
    df = load_and_preprocess_transactions(data_path)
    
    # 2. Zaman Pencerelerini Ayır
    obs_df, target_df = split_time_windows(df, cutoff_date)
    
    # 3. Müşteri Bazlı Analitik Veri Kümesini Çıkar
    customer_features = extract_customer_features(obs_df, target_df, cutoff_date)
    
    # 4. CSV Olarak Kaydet
    customer_features.to_csv(output_path, index=True)
    print(f"\n[+] Analitik tablo başarıyla kaydedildi: {output_path} ({os.path.getsize(output_path) / (1024 * 1024):.2f} MB)")
    
    # 5. Raporu Yazdır
    print_step1_report(customer_features)
    
    return customer_features
