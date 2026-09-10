"""
Adım 6: Segment Bazlı Ürün Tavsiye Sistemi

Observation dönemindeki sipariş-ürün eşleşmeleri kullanılarak
K-Means segmentleri bazında Market Basket Analysis için
transaction verisi hazırlanır.
"""

import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


# -------------------------------------------------------------------------
# AŞAMA 6A: Recommendation Transaction Verisinin Hazırlanması
# -------------------------------------------------------------------------

def prepare_recommendation_transactions(
    transaction_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    cutoff_date
) -> pd.DataFrame:

    print("\n" + "=" * 70)
    print("RECOMMENDATION - TRANSACTION VERİSİ HAZIRLIĞI")
    print("=" * 70)

    df = transaction_df.copy()

    # Tarih formatını garanti altına al
    df["orderdate"] = pd.to_datetime(df["orderdate"])

    # Sadece observation dönemini kullan
    df = df[df["orderdate"] < cutoff_date].copy()

    print(f"\nObservation transaction satırı : {len(df):,}")
    print(f"Observation sipariş sayısı     : {df['salesorderid'].nunique():,}")
    print(f"Observation müşteri sayısı     : {df['customerid'].nunique():,}")

    # Customer-level K-Means segmentini transaction verisine ekle
    segment_map = customer_df["kmeans_segment"]

    df["kmeans_segment"] = df["customerid"].map(segment_map)

    missing_segment = df["kmeans_segment"].isna().sum()

    print(f"\nSegment eşleşmeyen satır        : {missing_segment:,}")

    # Segment bilgisi bulunmayan kayıtları recommendation analizine alma
    df = df.dropna(subset=["kmeans_segment"])

    print("\nSegment bazında transaction yapısı:")

    segment_summary = (
        df.groupby("kmeans_segment")
        .agg(
            customers=("customerid", "nunique"),
            orders=("salesorderid", "nunique"),
            transaction_rows=("salesorderid", "size"),
            products=("productid", "nunique")
        )
        .sort_values("orders", ascending=False)
    )

    print(segment_summary)

    return df

# -------------------------------------------------------------------------
# AŞAMA 6B: Segment Bazında Sepet Yapısının Analizi
# -------------------------------------------------------------------------

def analyze_basket_structure(df: pd.DataFrame) -> pd.DataFrame:

    print("\n" + "=" * 70)
    print("SEGMENT BAZINDA SEPET YAPISI")
    print("=" * 70)

    results = []

    for segment, segment_df in df.groupby("kmeans_segment"):

        # Her siparişte kaç farklı ürün bulunduğunu hesapla
        basket_sizes = (
            segment_df.groupby("salesorderid")["productid"]
            .nunique()
        )

        total_orders = len(basket_sizes)
        multi_item_orders = (basket_sizes >= 2).sum()

        results.append({
            "segment": segment,
            "orders": total_orders,
            "avg_unique_products": basket_sizes.mean(),
            "median_unique_products": basket_sizes.median(),
            "max_unique_products": basket_sizes.max(),
            "multi_item_orders": multi_item_orders,
            "multi_item_ratio": multi_item_orders / total_orders
        })

    summary = pd.DataFrame(results)

    summary = summary.sort_values(
        "orders",
        ascending=False
    ).reset_index(drop=True)

    print(summary.round({
        "avg_unique_products": 2,
        "multi_item_ratio": 3
    }).to_string(index=False))

    return summary

# -------------------------------------------------------------------------
# AŞAMA 6C: Segment Bazlı Frequent Itemset Üretimi
# -------------------------------------------------------------------------

def generate_frequent_itemsets(df: pd.DataFrame) -> dict:

    print("\n" + "=" * 70)
    print("SEGMENT BAZINDA APRIORI - FREQUENT ITEMSETS")
    print("=" * 70)

    # Segmentlerin sepet yapıları farklı olduğu için
    # min_support değerleri segment bazında belirlenmiştir.
    support_thresholds = {
        "Accessory Shoppers": 0.01,
        "Bike Buyers": 0.005,
        "Clothing Shoppers": 0.01,
        "High-Value Customers": 0.03
    }

    frequent_itemsets_by_segment = {}

    for segment, segment_df in df.groupby("kmeans_segment"):

        print(f"\n>>> Segment: {segment}")

        basket = (
            segment_df.groupby(
                ["salesorderid", "product_name"]
            )["orderqty"]
            .sum()
            .unstack(fill_value=0)
        )

        basket = basket.gt(0)

        print(
            f"Basket boyutu: "
            f"{basket.shape[0]:,} sipariş × "
            f"{basket.shape[1]:,} ürün"
        )

        min_support = support_thresholds.get(segment, 0.01)

        print(f"Min support: {min_support:.3f}")

        frequent_itemsets = apriori(
            basket,
            min_support=min_support,
            use_colnames=True,
            max_len=3,
            low_memory=True
        )

        frequent_itemsets["length"] = (
            frequent_itemsets["itemsets"].apply(len)
        )

        frequent_itemsets = frequent_itemsets.sort_values(
            "support",
            ascending=False
        ).reset_index(drop=True)

        frequent_itemsets_by_segment[segment] = frequent_itemsets

        print(
            f"Frequent itemset sayısı: "
            f"{len(frequent_itemsets):,}"
        )

        if not frequent_itemsets.empty:

            length_counts = (
                frequent_itemsets["length"]
                .value_counts()
                .sort_index()
            )

            print("Itemset uzunluk dağılımı:")
            print(length_counts.to_string())

    return frequent_itemsets_by_segment

# -------------------------------------------------------------------------
# AŞAMA 6F: Segment Bazlı Association Rule Üretimi
# -------------------------------------------------------------------------

def generate_association_rules(
    frequent_itemsets_by_segment: dict,
    min_confidence: float = 0.20,
    min_lift: float = 1.10
) -> dict:

    print("\n" + "=" * 70)
    print("SEGMENT BAZINDA ASSOCIATION RULES")
    print("=" * 70)

    rules_by_segment = {}

    for segment, frequent_itemsets in frequent_itemsets_by_segment.items():

        print(f"\n>>> Segment: {segment}")

        if frequent_itemsets.empty:
            print("Frequent itemset bulunamadı.")
            rules_by_segment[segment] = pd.DataFrame()
            continue

        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence
        )

        # Pozitif ve anlamlı ilişkileri tut.
        # Recommendation çıktısının sade ve yorumlanabilir olması için
        # yalnızca tek ürün -> tek ürün kuralları kullanılır.
        rules = rules[
            (rules["lift"] >= min_lift) &
            (rules["antecedents"].apply(len) == 1) &
            (rules["consequents"].apply(len) == 1)
        ].copy()

        rules = rules.sort_values(
            ["lift", "confidence", "support"],
            ascending=False
        ).reset_index(drop=True)

        rules_by_segment[segment] = rules

        print(f"Rule sayısı: {len(rules):,}")

        if not rules.empty:
            print(
                rules[
                    [
                        "antecedents",
                        "consequents",
                        "support",
                        "confidence",
                        "lift"
                    ]
                ]
                .head(10)
                .to_string(index=False)
            )

    return rules_by_segment

# -------------------------------------------------------------------------
# AŞAMA 6G: Müşteri Bazlı Kişiselleştirilmiş Ürün Önerileri
# -------------------------------------------------------------------------

def generate_customer_recommendations(
    transaction_df: pd.DataFrame,
    customer_df: pd.DataFrame,
    rules_by_segment: dict,
    top_n: int = 3
) -> pd.DataFrame:

    print("\n" + "=" * 70)
    print("YÜKSEK CHURN RİSKİ + YÜKSEK CLTV MÜŞTERİ ÖNERİLERİ")
    print("=" * 70)

    # Yüksek değerli ve churn riski yüksek müşteriler
    target_customers = customer_df[
        (customer_df["is_matured"] == 1) &
        (customer_df["cltv_segment"] == "A") &
        (customer_df["churn_pred"] == 1)
    ].copy()

    print(f"\nHedef müşteri sayısı: {len(target_customers):,}")

    recommendations = []

    for customer_id, customer in target_customers.iterrows():

        segment = customer["kmeans_segment"]

        # Müşterinin observation döneminde satın aldığı ürünler
        purchased_products = set(
            transaction_df.loc[
                transaction_df["customerid"] == customer_id,
                "product_name"
            ].unique()
        )

        segment_rules = rules_by_segment.get(segment)

        if segment_rules is None or segment_rules.empty:
            continue

        customer_candidates = []

        for _, rule in segment_rules.iterrows():

            antecedent = next(iter(rule["antecedents"]))
            consequent = next(iter(rule["consequents"]))

            # Müşteri antecedent ürünü satın almış olmalı
            if antecedent not in purchased_products:
                continue

            # Daha önce aldığı ürünü tekrar önerme
            if consequent in purchased_products:
                continue

            customer_candidates.append({
                "customerid": customer_id,
                "kmeans_segment": segment,
                "cltv_segment": customer["cltv_segment"],
                "cltv_6m": customer["cltv_6m"],
                "churn_proba": customer["churn_proba"],
                "based_on_product": antecedent,
                "recommended_product": consequent,
                "support": rule["support"],
                "confidence": rule["confidence"],
                "lift": rule["lift"]
            })

        if customer_candidates:

            candidate_df = pd.DataFrame(customer_candidates)

            # Aynı ürün birden fazla yoldan önerilmişse
            # en güçlü kuralı tut
            candidate_df = (
                candidate_df
                .sort_values(
                    ["lift", "confidence", "support"],
                    ascending=False
                )
                .drop_duplicates(
                    subset=["recommended_product"]
                )
                .head(top_n)
            )

            recommendations.extend(
                candidate_df.to_dict("records")
            )

    recommendations_df = pd.DataFrame(recommendations)

    print(
        f"Öneri üretilebilen müşteri sayısı: "
        f"{recommendations_df['customerid'].nunique() if not recommendations_df.empty else 0:,}"
    )

    print(
        f"Toplam öneri sayısı: "
        f"{len(recommendations_df):,}"
    )

    if not recommendations_df.empty:

        print("\nÖrnek öneriler:")

        print(
            recommendations_df[
                [
                    "customerid",
                    "kmeans_segment",
                    "cltv_6m",
                    "churn_proba",
                    "based_on_product",
                    "recommended_product",
                    "confidence",
                    "lift"
                ]
            ]
            .head(15)
            .round({
                "cltv_6m": 2,
                "churn_proba": 3,
                "confidence": 3,
                "lift": 2
            })
            .to_string(index=False)
        )

    return recommendations_df