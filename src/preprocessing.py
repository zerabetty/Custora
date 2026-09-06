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