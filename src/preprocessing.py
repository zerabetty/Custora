import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from src.data_loader import (
    split_time_windows,
    extract_customer_features,
)


def run_eda(customer_df):
    print("\n" + "=" * 70)
    print("EDA - VERİ SETİ GENEL KONTROL")
    print("=" * 70)

    print("\n[1] Veri seti boyutu:")
    print(customer_df.shape)

    print("\n[2] İlk 5 gözlem:")
    print(customer_df.head())

    print("\n[3] Değişken tipleri ve doluluk bilgisi:")
    customer_df.info()

    print("\n[4] Eksik değer sayıları:")
    print(customer_df.isnull().sum().sort_values(ascending=False))

    print("\n[5] Duplicate satır sayısı:")
    print(customer_df.duplicated().sum())

    print("\n[6] Sayısal değişkenlerin betimsel istatistikleri:")
    print(customer_df.describe().T)

    print("\n[7] Churn dağılımı (Toplam Portföy):")
    if "is_churn" in customer_df.columns:
        print(customer_df["is_churn"].value_counts())

        print("\nToplam Churn oranları (%):")
        print(
            customer_df["is_churn"]
            .value_counts(normalize=True)
            .mul(100)
            .round(2)
        )
        if "is_matured" in customer_df.columns:
            matured_df = customer_df[customer_df["is_matured"] == 1]
            print(f"\n[8] Olgunlaşmış Müşteri Churn Dağılımı ({len(matured_df):,} müşteri):")
            print(
                matured_df["is_churn"]
                .value_counts(normalize=True)
                .mul(100)
                .round(2)
            )
    else:
        print("is_churn değişkeni bulunamadı.")

    return customer_df

def analyze_purchase_intervals(transaction_df):
    print("\n" + "=" * 70)
    print("MÜŞTERİ SATIN ALMA ARALIKLARI ANALİZİ")
    print("=" * 70)

    df = transaction_df.copy()

    df["orderdate"] = pd.to_datetime(df["orderdate"])

    order_df = (
        df[["customerid", "salesorderid", "orderdate"]]
        .drop_duplicates()
        .sort_values(["customerid", "orderdate"])
    )

    order_df["previous_order_date"] = (
        order_df.groupby("customerid")["orderdate"].shift(1)
    )

    order_df["days_between_orders"] = (
        order_df["orderdate"] - order_df["previous_order_date"]
    ).dt.days

    intervals = order_df["days_between_orders"].dropna()

    print("\nTekrar satın alma aralığı gözlem sayısı:")
    print(len(intervals))

    print("\nSatın alma aralığı betimsel istatistikleri:")
    print(intervals.describe())

    print("\nSatın alma aralığı yüzdelikleri:")
    percentiles = intervals.quantile([0.25, 0.50, 0.75, 0.90, 0.95])
    print(percentiles)

    print("\nBelirli sürelerden daha uzun satın alma aralıkları:")

    for days in [180, 270, 365]:
        ratio = (intervals > days).mean() * 100
        print(f"{days} günden uzun: %{ratio:.2f}")

    return intervals

def compare_churn_horizons(transaction_df, horizons=(6, 9, 12)):
    print("\n" + "=" * 70)
    print("CHURN TARGET WINDOW KARŞILAŞTIRMASI")
    print("=" * 70)

    df = transaction_df.copy()
    df["orderdate"] = pd.to_datetime(df["orderdate"])

    # Ürün satırlarını tekil sipariş seviyesine indiriyoruz.
    orders = (
        df[["customerid", "salesorderid", "orderdate"]]
        .drop_duplicates()
    )

    data_start = orders["orderdate"].min()
    data_end = orders["orderdate"].max()

    results = []

    for months in horizons:

        cutoff_date = data_end - pd.DateOffset(months=months)

        observation = orders[
            (orders["orderdate"] >= data_start)
            & (orders["orderdate"] < cutoff_date)
        ]

        target = orders[
            (orders["orderdate"] >= cutoff_date)
            & (orders["orderdate"] <= data_end)
        ]

        observation_customers = set(observation["customerid"])
        target_customers = set(target["customerid"])

        churn_count = len(observation_customers - target_customers)
        retained_count = len(observation_customers & target_customers)

        total_customers = len(observation_customers)

        churn_rate = (
            churn_count / total_customers * 100
            if total_customers > 0
            else 0
        )

        retained_rate = (
            retained_count / total_customers * 100
            if total_customers > 0
            else 0
        )

        results.append(
            {
                "target_months": months,
                "cutoff_date": cutoff_date.date(),
                "observation_customers": total_customers,
                "target_customers": len(target_customers),
                "churn_count": churn_count,
                "retained_count": retained_count,
                "churn_rate": round(churn_rate, 2),
                "retained_rate": round(retained_rate, 2),
            }
        )

    results_df = pd.DataFrame(results)

    print("\n6 / 9 / 12 Aylık Churn Karşılaştırması:")
    print(results_df.to_string(index=False))

    return results_df


def compare_rfm_churn_horizons(transaction_df, horizons=(6, 9, 12)):
    print("\n" + "=" * 70)
    print("RFM SEGMENTLERİ × CHURN HORIZON KARŞILAŞTIRMASI")
    print("=" * 70)

    df = transaction_df.copy()
    df["orderdate"] = pd.to_datetime(df["orderdate"])

    data_end = df["orderdate"].max()

    all_results = []

    for months in horizons:

        cutoff_date = data_end - pd.DateOffset(months=months)

        print(
            f"\n>>> {months} aylık target "
            f"(cutoff: {cutoff_date.date()})"
        )

        # Her horizon için observation ve target yeniden oluşturulur
        obs_df, target_df = split_time_windows(
            df,
            cutoff_date
        )

        # Ege'nin mevcut feature extraction fonksiyonunu aynen kullanıyoruz
        horizon_customer_df = extract_customer_features(
            obs_df,
            target_df,
            cutoff_date
        )

        # -------------------------------------------------------------
        # SADECE 9 AYLIK SENARYO İÇİN DETAY KONTROL
        # -------------------------------------------------------------
        if months == 9:

            print("\n--- 9 AYLIK SENARYO DETAY KONTROLÜ ---")

            print("\nSegment büyüklükleri:")
            print(
                horizon_customer_df["rfm_segment"]
                .value_counts()
            )

            print("\nSegment bazında ortalama recency:")
            print(
                horizon_customer_df
                .groupby(
                    "rfm_segment",
                    observed=False
                )["recency_days"]
                .mean()
                .round(1)
                .sort_values()
            )

            print("\nSegment bazında ortalama sipariş sayısı:")
            print(
                horizon_customer_df
                .groupby(
                    "rfm_segment",
                    observed=False
                )["total_orders"]
                .mean()
                .round(2)
                .sort_values(ascending=False)
            )

            print("\nTarget'ta geri dönen müşteri sayısı:")

            target_buyers = set(
                target_df["customerid"].unique()
            )

            returned = horizon_customer_df.index.isin(
                target_buyers
            )

            return_summary = (
                horizon_customer_df
                .assign(returned=returned)
                .groupby(
                    "rfm_segment",
                    observed=False
                )["returned"]
                .agg(["count", "sum", "mean"])
                .sort_values(
                    "mean",
                    ascending=False
                )
            )

            return_summary["mean"] = (
                return_summary["mean"] * 100
            ).round(2)

            return_summary = return_summary.rename(
                columns={
                    "count": "customer_count",
                    "sum": "returned_count",
                    "mean": "return_rate_pct"
                }
            )

            print(return_summary)

        # -------------------------------------------------------------
        # RFM SEGMENTİ BAZINDA CHURN ÖZETİ
        # -------------------------------------------------------------
        segment_summary = (
            horizon_customer_df
            .groupby(
                "rfm_segment",
                observed=False
            )
            .agg(
                customer_count=("is_churn", "size"),
                churn_rate=("is_churn", "mean")
            )
            .reset_index()
        )

        segment_summary["churn_rate"] = (
            segment_summary["churn_rate"] * 100
        ).round(2)

        segment_summary["target_months"] = months
        segment_summary["cutoff_date"] = cutoff_date.date()

        all_results.append(segment_summary)

    results_df = pd.concat(
        all_results,
        ignore_index=True
    )

    # Segmentleri satır,
    # horizonları sütun haline getiriyoruz
    churn_pivot = results_df.pivot(
        index="rfm_segment",
        columns="target_months",
        values="churn_rate"
    )

    churn_pivot = churn_pivot.rename(
        columns={
            6: "churn_6m",
            9: "churn_9m",
            12: "churn_12m"
        }
    )

    print("\n" + "=" * 70)
    print("RFM SEGMENTLERİNE GÖRE CHURN ORANLARI (%)")
    print("=" * 70)

    print(churn_pivot.round(2).to_string())

    return results_df, churn_pivot

def analyze_temporal_customer_structure(transaction_df):
    print("\n" + "=" * 70)
    print("ZAMANSAL MÜŞTERİ VE COHORT YAPISI ANALİZİ")
    print("=" * 70)

    df = transaction_df.copy()
    df["orderdate"] = pd.to_datetime(df["orderdate"])

    # -------------------------------------------------------------
    # 1. Transaction verisini sipariş seviyesine indir
    # -------------------------------------------------------------
    orders = (
        df[["customerid", "salesorderid", "orderdate"]]
        .drop_duplicates()
        .sort_values(["customerid", "orderdate"])
        .copy()
    )

    print("\nVeri tarih aralığı:")
    print(
        orders["orderdate"].min().date(),
        "->",
        orders["orderdate"].max().date()
    )

    # -------------------------------------------------------------
    # 2. Her müşterinin ilk sipariş tarihini bul
    # -------------------------------------------------------------
    first_orders = (
        orders.groupby("customerid")["orderdate"]
        .min()
        .rename("first_order_date")
    )

    orders = orders.merge(
        first_orders,
        on="customerid",
        how="left"
    )

    # -------------------------------------------------------------
    # 3. Ay değişkenini oluştur
    # -------------------------------------------------------------
    orders["order_month"] = (
        orders["orderdate"]
        .dt.to_period("M")
    )

    orders["first_order_month"] = (
        orders["first_order_date"]
        .dt.to_period("M")
    )

    # O ay müşterinin ilk kez alışveriş yapıp yapmadığı
    orders["is_new_customer"] = (
        orders["order_month"] ==
        orders["first_order_month"]
    )

    # -------------------------------------------------------------
    # 4. Aylık sipariş ve müşteri yapısı
    # -------------------------------------------------------------
    monthly_base = (
        orders.groupby("order_month")
        .agg(
            unique_orders=("salesorderid", "nunique"),
            unique_customers=("customerid", "nunique")
        )
    )

    new_customers = (
        orders.loc[orders["is_new_customer"]]
        .groupby("order_month")["customerid"]
        .nunique()
        .rename("new_customers")
    )

    monthly_summary = (
        monthly_base
        .join(new_customers, how="left")
        .fillna({"new_customers": 0})
    )

    monthly_summary["new_customers"] = (
        monthly_summary["new_customers"].astype(int)
    )

    monthly_summary["returning_customers"] = (
        monthly_summary["unique_customers"]
        - monthly_summary["new_customers"]
    )

    monthly_summary["new_customer_rate_pct"] = (
        monthly_summary["new_customers"]
        / monthly_summary["unique_customers"]
        * 100
    ).round(2)

    monthly_summary["returning_customer_rate_pct"] = (
        monthly_summary["returning_customers"]
        / monthly_summary["unique_customers"]
        * 100
    ).round(2)

    print("\n" + "-" * 70)
    print("AYLIK MÜŞTERİ YAPISI")
    print("-" * 70)

    print(monthly_summary.to_string())

    # -------------------------------------------------------------
    # 5. İlk alışveriş yılı -> aktif olunan yıl analizi
    # -------------------------------------------------------------
    orders["first_order_year"] = (
        orders["first_order_date"].dt.year
    )

    orders["order_year"] = (
        orders["orderdate"].dt.year
    )

    cohort_year = (
        orders[
            ["customerid", "first_order_year", "order_year"]
        ]
        .drop_duplicates()
        .groupby(
            ["first_order_year", "order_year"]
        )["customerid"]
        .nunique()
        .unstack(fill_value=0)
    )

    print("\n" + "-" * 70)
    print("İLK ALIŞVERİŞ YILI × AKTİF OLUNAN YIL")
    print("-" * 70)

    print(cohort_year.to_string())

    # -------------------------------------------------------------
    # 6. Müşteri başına toplam sipariş sayısı
    # -------------------------------------------------------------
    orders_per_customer = (
        orders.groupby("customerid")["salesorderid"]
        .nunique()
    )

    order_count_distribution = (
        orders_per_customer
        .value_counts()
        .sort_index()
        .rename_axis("total_orders")
        .to_frame("customer_count")
    )

    order_count_distribution["customer_rate_pct"] = (
        order_count_distribution["customer_count"]
        / order_count_distribution["customer_count"].sum()
        * 100
    ).round(2)

    print("\n" + "-" * 70)
    print("MÜŞTERİ BAŞINA TOPLAM SİPARİŞ SAYISI")
    print("-" * 70)

    print(order_count_distribution.to_string())

    return (
        monthly_summary,
        cohort_year,
        order_count_distribution
    )

def analyze_numeric_distributions(customer_df):
    print("\n" + "=" * 70)
    print("SAYISAL DEĞİŞKENLER - DAĞILIM VE SKEWNESS ANALİZİ")
    print("=" * 70)

    # Modellemeye girmeyecek kimlik/tarih/target değişkenlerini dışarıda tutuyoruz
    exclude_cols = [
        "is_churn",
        "is_matured"
    ]

    numeric_cols = (
        customer_df
        .select_dtypes(include="number")
        .columns
        .difference(exclude_cols)
        .tolist()
    )

    results = []

    for col in numeric_cols:
        series = customer_df[col].dropna()

        results.append({
            "variable": col,
            "mean": series.mean(),
            "median": series.median(),
            "std": series.std(),
            "min": series.min(),
            "max": series.max(),
            "skewness": series.skew(),
            "zero_rate_pct": (series.eq(0).mean() * 100)
        })

    distribution_df = pd.DataFrame(results)

    distribution_df["mean"] = distribution_df["mean"].round(2)
    distribution_df["median"] = distribution_df["median"].round(2)
    distribution_df["std"] = distribution_df["std"].round(2)
    distribution_df["min"] = distribution_df["min"].round(2)
    distribution_df["max"] = distribution_df["max"].round(2)
    distribution_df["skewness"] = distribution_df["skewness"].round(2)
    distribution_df["zero_rate_pct"] = (
        distribution_df["zero_rate_pct"].round(2)
    )

    distribution_df["skew_level"] = pd.cut(
        distribution_df["skewness"].abs(),
        bins=[-1, 0.5, 1, float("inf")],
        labels=[
            "low",
            "moderate",
            "high"
        ]
    )

    distribution_df = distribution_df.sort_values(
        "skewness",
        key=lambda x: x.abs(),
        ascending=False
    )

    print("\nSayısal değişkenlerin dağılım özeti:")
    print(distribution_df.to_string(index=False))

    return distribution_df

def analyze_outliers(customer_df):
    print("\n" + "=" * 70)
    print("OUTLIER / QUANTILE ANALİZİ")
    print("=" * 70)

    candidate_cols = [
        "total_monetary",
        "avg_monetary",
        "total_quantity",
        "avg_basket_items",
        "spend_bikes",
        "spend_accessories",
        "spend_clothing",
        "spend_components"
    ]

    results = []

    for col in candidate_cols:
        series = customer_df[col].dropna()

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        outlier_count = (
            (series < lower_bound) |
            (series > upper_bound)
        ).sum()

        results.append({
            "variable": col,
            "p50": series.quantile(0.50),
            "p90": series.quantile(0.90),
            "p95": series.quantile(0.95),
            "p99": series.quantile(0.99),
            "max": series.max(),
            "iqr_upper_bound": upper_bound,
            "iqr_outlier_count": outlier_count,
            "iqr_outlier_pct": outlier_count / len(series) * 100
        })

    outlier_df = pd.DataFrame(results)

    numeric_round_cols = [
        "p50", "p90", "p95", "p99", "max",
        "iqr_upper_bound", "iqr_outlier_pct"
    ]

    outlier_df[numeric_round_cols] = (
        outlier_df[numeric_round_cols].round(2)
    )

    print(outlier_df.to_string(index=False))

    return outlier_df

def evaluate_log_transform(customer_df):
    print("\n" + "=" * 70)
    print("LOG1P DÖNÜŞÜMÜ - ÖNCESİ / SONRASI SKEWNESS")
    print("=" * 70)

    candidate_cols = [
        "total_monetary",
        "avg_monetary",
        "total_quantity",
        "avg_basket_items",
        "spend_bikes",
        "spend_accessories",
        "spend_clothing",
        "spend_components"
    ]

    results = []

    for col in candidate_cols:
        series = customer_df[col].dropna()

        original_skew = series.skew()
        log_series = np.log1p(series)
        log_skew = log_series.skew()

        results.append({
            "variable": col,
            "original_skew": original_skew,
            "log1p_skew": log_skew,
            "absolute_improvement":
                abs(original_skew) - abs(log_skew)
        })

    log_test_df = pd.DataFrame(results)

    log_test_df[
        ["original_skew", "log1p_skew", "absolute_improvement"]
    ] = log_test_df[
        ["original_skew", "log1p_skew", "absolute_improvement"]
    ].round(2)

    log_test_df = log_test_df.sort_values(
        "absolute_improvement",
        ascending=False
    )

    print(log_test_df.to_string(index=False))

    return log_test_df

def analyze_feature_correlations(customer_df):
    print("\n" + "=" * 70)
    print("FEATURE CORRELATION / REDUNDANCY ANALİZİ")
    print("=" * 70)

    numeric_df = customer_df.select_dtypes(include="number").copy()

    # Target ve filtre analiz dışında tutuluyor
    numeric_df = numeric_df.drop(
        columns=["is_churn", "is_matured"],
        errors="ignore"
    )

    corr_matrix = numeric_df.corr()

    high_corr_pairs = []

    columns = corr_matrix.columns

    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            corr_value = corr_matrix.iloc[i, j]

            if abs(corr_value) >= 0.70:
                high_corr_pairs.append({
                    "feature_1": columns[i],
                    "feature_2": columns[j],
                    "correlation": round(corr_value, 3)
                })

    high_corr_df = pd.DataFrame(high_corr_pairs)

    if not high_corr_df.empty:
        high_corr_df["abs_correlation"] = (
            high_corr_df["correlation"].abs()
        )

        high_corr_df = (
            high_corr_df
            .sort_values("abs_correlation", ascending=False)
            .drop(columns="abs_correlation")
        )

        print("\n|Correlation| >= 0.70 olan değişken çiftleri:")
        print(high_corr_df.to_string(index=False))
    else:
        print("\n0.70 üzerinde korelasyon bulunan değişken çifti yok.")

    return corr_matrix, high_corr_df

def prepare_kmeans_features(customer_df):
    print("\n" + "=" * 70)
    print("K-MEANS FEATURE PREPROCESSING")
    print("=" * 70)

    kmeans_features = [
        "recency_days",
        "total_orders",
        "total_monetary",
        "avg_basket_items",
        "ratio_bikes",
        "ratio_accessories",
        "ratio_clothing",
        "ratio_components"
    ]

    kmeans_df = customer_df[kmeans_features].copy()

    # Güçlü sağa çarpık ve pozitif değişkenler
    log_cols = [
        "total_monetary",
        "avg_basket_items"
    ]

    for col in log_cols:
        kmeans_df[col] = np.log1p(kmeans_df[col])

    # K-Means uzaklık tabanlı olduğu için ölçekleme
    scaler = StandardScaler()

    scaled_array = scaler.fit_transform(kmeans_df)

    kmeans_scaled_df = pd.DataFrame(
        scaled_array,
        columns=kmeans_features,
        index=customer_df.index
    )

    print("\nK-Means için seçilen feature'lar:")
    print(kmeans_features)

    print("\nLog1p uygulanan feature'lar:")
    print(log_cols)

    print("\nScaled feature özeti:")
    print(
        kmeans_scaled_df
        .agg(["mean", "std", "min", "max"])
        .round(2)
        .to_string()
    )

    return kmeans_df, kmeans_scaled_df, scaler