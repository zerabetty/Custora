import pandas as pd


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

    print("\n[7] Churn dağılımı:")
    if "is_churn" in customer_df.columns:
        print(customer_df["is_churn"].value_counts())

        print("\nChurn oranları (%):")
        print(
            customer_df["is_churn"]
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