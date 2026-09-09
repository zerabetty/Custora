"""
Adım 4: CLTV Tahmini (BG/NBD & Gamma-Gamma)
lifetimes kütüphanesi ile perakende sektör standardı yaklaşım.
"""

import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from lifetimes import BetaGeoFitter, GammaGammaFitter
from lifetimes.utils import ConvergenceError


WEEKLY_HORIZONS = {
    "3m": 12,
    "6m": 24,
}

CLTV_MONTHS = {
    "3m": 3,
    "6m": 6,
}

WEEKS_PER_MONTH = 4

KMEANS_SEGMENT_ORDER = [
    "Accessory Shoppers",
    "Bike Buyers",
    "Clothing Shoppers",
    "High-Value Customers",
]

CLTV_SEGMENT_ORDER = ["A", "B", "C", "D"]

BGNBD_PENALIZERS = (0.001, 0.01, 0.05, 0.1)


def _replace_with_thresholds(series: pd.Series) -> pd.Series:
    """0.01–0.99 quantile tabanlı uç değer baskılama."""
    q1 = series.quantile(0.01)
    q3 = series.quantile(0.99)
    iqr = q3 - q1
    low = q1 - 1.5 * iqr
    up = q3 + 1.5 * iqr
    return series.clip(lower=max(low, 0), upper=up)


def prepare_cltv_inputs(customer_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adım 1'de üretilen lifetimes metriklerini BG/NBD & Gamma-Gamma
    formatına (haftalık) dönüştürür.

    lifetimes konvansiyonu:
    - frequency : tekrar eden işlem sayısı (total_orders - 1)
    - recency   : ilk ve son sipariş arası süre
    - T         : müşteri yaşı (ilk sipariş → cut-off)
    - monetary  : işlem başına ortalama harcama
    """
    print("\n" + "=" * 70)
    print("CLTV - LIFETIMES VERİ YAPISI")
    print("=" * 70)

    cltv_df = pd.DataFrame(index=customer_df.index)
    cltv_df["frequency"] = customer_df["repeat_frequency"].astype(float)
    cltv_df["recency"] = customer_df["lifetimes_recency_days"] / 7
    cltv_df["T"] = customer_df["customer_age_t_days"] / 7
    cltv_df["monetary"] = customer_df["avg_monetary"].astype(float)

    n_before = len(cltv_df)
    cltv_df = cltv_df[(cltv_df["T"] > 0) & (cltv_df["monetary"] > 0)].copy()
    n_dropped = n_before - len(cltv_df)
    if n_dropped:
        print(f"\n[!] T<=0 veya monetary<=0 olan {n_dropped} müşteri model dışı bırakıldı.")

    invalid_recency = (cltv_df["recency"] > cltv_df["T"]).sum()
    if invalid_recency:
        print(f"[!] recency > T olan {invalid_recency} kayıt T değerine çekildi.")
        cltv_df.loc[cltv_df["recency"] > cltv_df["T"], "recency"] = (
            cltv_df.loc[cltv_df["recency"] > cltv_df["T"], "T"]
        )

    freq_before = cltv_df["frequency"].copy()
    mon_before = cltv_df["monetary"].copy()
    cltv_df["frequency"] = _replace_with_thresholds(cltv_df["frequency"])
    cltv_df["monetary"] = _replace_with_thresholds(cltv_df["monetary"])
    cltv_df["frequency"] = np.floor(cltv_df["frequency"]).clip(lower=0)

    n_freq_capped = int((freq_before != cltv_df["frequency"]).sum())
    n_mon_capped = int((mon_before.round(6) != cltv_df["monetary"].round(6)).sum())

    n_repeat = int((cltv_df["frequency"] > 0).sum())
    n_onetime = int((cltv_df["frequency"] == 0).sum())

    print(f"\nModellenen müşteri sayısı : {len(cltv_df):,}")
    print(f"  - Tekrar alıcı (frequency > 0) : {n_repeat:,} (%{n_repeat / len(cltv_df) * 100:.2f})")
    print(f"  - Tek siparişli (frequency = 0): {n_onetime:,} (%{n_onetime / len(cltv_df) * 100:.2f})")
    print(f"Uç değer baskılanan frequency    : {n_freq_capped:,}")
    print(f"Uç değer baskılanan monetary     : {n_mon_capped:,}")

    print("\nHaftalık CLTV girdi özeti:")
    print(cltv_df[["frequency", "recency", "T", "monetary"]].describe().round(2).to_string())

    return cltv_df


def check_gamma_gamma_assumption(cltv_df: pd.DataFrame) -> float:
    """Gamma-Gamma, frequency ile monetary arasında korelasyon olmadığını varsayar."""
    repeat_df = cltv_df[cltv_df["frequency"] > 0]
    corr = repeat_df[["frequency", "monetary"]].corr().iloc[0, 1]
    print(f"\n[+] Gamma-Gamma varsayımı — corr(frequency, monetary): {corr:.4f}")
    if abs(corr) < 0.10:
        print("    Varsayım sağlanıyor (|r| < 0.10).")
    else:
        print("    |r| >= 0.10: varsayım zayıf (B2B yüksek frekans + yüksek sepet).")
        print("    Gamma-Gamma yine de perakende standardı olarak kurulacak.")
    return float(corr)


def fit_bgnbd_model(cltv_df: pd.DataFrame) -> BetaGeoFitter:
    print("\n" + "=" * 70)
    print("CLTV - BG/NBD MODELİ")
    print("=" * 70)

    last_error = None
    for penalizer_coef in BGNBD_PENALIZERS:
        bgf = BetaGeoFitter(penalizer_coef=penalizer_coef)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                bgf.fit(cltv_df["frequency"], cltv_df["recency"], cltv_df["T"])
            print(f"\n[+] Yakınsama: penalizer_coef={penalizer_coef}")
            print(f"{bgf}")
            params = bgf.params_
            print("\nParametreler:")
            print(f"  r     : {params['r']:.4f}   (satın alma oranı şekil)")
            print(f"  alpha : {params['alpha']:.4f}   (satın alma oranı ölçek, hafta)")
            print(f"  a     : {params['a']:.4f}   (dropout Beta şekil)")
            print(f"  b     : {params['b']:.4f}   (dropout Beta şekil)")
            if params["a"] < 1e-4 and params["b"] < 1e-4:
                print("\n[!] a~0 ve b~0: model gözlem penceresinde belirgin dropout görmüyor.")
                print("    AdventureWorks'un uzun satın alma döngüsü ile uyumlu bir bulgudur.")
            return bgf
        except ConvergenceError as exc:
            last_error = exc
            print(f"[!] penalizer_coef={penalizer_coef} yakınsamadı, bir üst değere geçiliyor.")

    raise ConvergenceError(
        "BG/NBD hiçbir penalizer ile yakınsamadı."
    ) from last_error


def _expected_purchases_closed_form(bgf: BetaGeoFitter, t: float, cltv_df: pd.DataFrame) -> pd.Series:
    """Dropout yokken (a≈0, b≈0) BG/NBD, Gamma-Poisson kapalı formuna indirgenir."""
    r = float(bgf.params_["r"])
    alpha = float(bgf.params_["alpha"])
    return (r + cltv_df["frequency"]) * t / (alpha + cltv_df["T"])


def predict_expected_purchases(bgf: BetaGeoFitter, cltv_df: pd.DataFrame) -> pd.DataFrame:
    result = cltv_df.copy()
    params = bgf.params_
    no_dropout = params["a"] < 1e-4 and params["b"] < 1e-4

    for label, weeks in WEEKLY_HORIZONS.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            predicted = bgf.conditional_expected_number_of_purchases_up_to_time(
                weeks,
                result["frequency"],
                result["recency"],
                result["T"],
            )
        predicted = pd.Series(predicted, index=result.index, dtype="float64")
        non_finite = ~np.isfinite(predicted)
        n_fixed = int(non_finite.sum())
        if n_fixed or no_dropout:
            closed = _expected_purchases_closed_form(bgf, weeks, result)
            if n_fixed:
                predicted.loc[non_finite] = closed.loc[non_finite]
                print(
                    f"[!] exp_purchases_{label}: lifetimes {n_fixed:,} müşteride "
                    f"sonlu değer üretmedi; Gamma-Poisson kapalı formu kullanıldı."
                )
        result[f"exp_purchases_{label}"] = predicted.clip(lower=0)

    print("\nBeklenen işlem sayısı özeti:")
    print(result[["exp_purchases_3m", "exp_purchases_6m"]].describe().round(4).to_string())
    print("\nBeklenen işlem sayısı (ilk 5, 6 aylık sıralı):")
    print(
        result.sort_values("exp_purchases_6m", ascending=False)[
            ["frequency", "recency", "T", "exp_purchases_3m", "exp_purchases_6m"]
        ]
        .head()
        .round(4)
        .to_string()
    )
    return result


def fit_gamma_gamma_model(cltv_df: pd.DataFrame, penalizer_coef: float = 0.01) -> GammaGammaFitter:
    print("\n" + "=" * 70)
    print("CLTV - GAMMA-GAMMA MODELİ")
    print("=" * 70)

    repeat_df = cltv_df[(cltv_df["frequency"] > 0) & (cltv_df["monetary"] > 0)]
    print(f"\nGamma-Gamma eğitim kümesi: {len(repeat_df):,} tekrar alıcı müşteri")

    ggf = GammaGammaFitter(penalizer_coef=penalizer_coef)
    ggf.fit(repeat_df["frequency"], repeat_df["monetary"])

    print(f"\n{ggf}")
    params = ggf.params_
    print("\nParametreler:")
    print(f"  p : {params['p']:.4f}")
    print(f"  q : {params['q']:.4f}")
    print(f"  v : {params['v']:.4f}")
    if params["q"] <= 1:
        print("\n[!] q <= 1: popülasyon prior'ı (p*v/(q-1)) tanımsız/negatif.")
        print("    Tek siparişli müşterilerde gözlenen avg_monetary kullanılacak.")
    return ggf


def predict_expected_profit(ggf: GammaGammaFitter, cltv_df: pd.DataFrame) -> pd.DataFrame:
    result = cltv_df.copy()
    modeled = ggf.conditional_expected_average_profit(
        result["frequency"],
        result["monetary"],
    )
    modeled = pd.Series(modeled, index=result.index, dtype="float64")

    one_time = result["frequency"] == 0
    invalid = (~np.isfinite(modeled)) | (modeled <= 0)
    fallback_mask = one_time | invalid
    result["exp_average_profit"] = modeled
    result.loc[fallback_mask, "exp_average_profit"] = result.loc[fallback_mask, "monetary"]

    n_fallback = int(fallback_mask.sum())
    print(
        f"\n[+] Beklenen ortalama kâr hesaplandı. "
        f"Gözlenen monetary'ye düşülen müşteri: {n_fallback:,}"
    )
    print("\nBeklenen ortalama kâr özeti:")
    print(result[["monetary", "exp_average_profit"]].describe().round(2).to_string())
    print("\nBeklenen ortalama kâr (ilk 5):")
    print(
        result.sort_values("exp_average_profit", ascending=False)[
            ["frequency", "monetary", "exp_average_profit"]
        ]
        .head()
        .round(2)
        .to_string()
    )
    return result


def _discounted_cltv(
    bgf: BetaGeoFitter,
    cltv_df: pd.DataFrame,
    months: int,
    discount_rate: float,
) -> pd.Series:
    """
    CLTV = Σ_m [beklenen işlem_m × beklenen ortalama kâr / (1+d)^m]

    time ay cinsindendir; haftalık kalibrasyonda 1 ay = 4 hafta.
    lifetimes.customer_lifetime_value ile aynı iskonto şeması, sonlu tahmin garantisiyle.
    """
    profit = cltv_df["exp_average_profit"]
    cltv = pd.Series(0.0, index=cltv_df.index)
    prev = pd.Series(0.0, index=cltv_df.index)

    for month in range(1, months + 1):
        weeks = month * WEEKS_PER_MONTH
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cumulative = bgf.conditional_expected_number_of_purchases_up_to_time(
                weeks,
                cltv_df["frequency"],
                cltv_df["recency"],
                cltv_df["T"],
            )
        cumulative = pd.Series(cumulative, index=cltv_df.index, dtype="float64")
        non_finite = ~np.isfinite(cumulative)
        if non_finite.any():
            closed = _expected_purchases_closed_form(bgf, weeks, cltv_df)
            cumulative.loc[non_finite] = closed.loc[non_finite]
        incremental = (cumulative - prev).clip(lower=0)
        cltv = cltv + incremental * profit / ((1 + discount_rate) ** month)
        prev = cumulative

    return cltv.clip(lower=0)


def compute_cltv_values(
    bgf: BetaGeoFitter,
    cltv_df: pd.DataFrame,
    discount_rate: float = 0.01,
) -> pd.DataFrame:
    """BG/NBD ve Gamma-Gamma çıktılarını birleştirerek 3 ve 6 aylık CLTV üretir."""
    print("\n" + "=" * 70)
    print("CLTV - 3 VE 6 AYLIK DEĞERLER")
    print("=" * 70)

    result = cltv_df.copy()
    for label, months in CLTV_MONTHS.items():
        result[f"cltv_{label}"] = _discounted_cltv(bgf, result, months, discount_rate)

    print("\nCLTV özeti:")
    print(result[["cltv_3m", "cltv_6m"]].describe().round(2).to_string())

    print("\nEn yüksek 10 müşteri (6 aylık CLTV):")
    print(
        result.sort_values("cltv_6m", ascending=False)[
            [
                "frequency",
                "monetary",
                "exp_purchases_3m",
                "exp_purchases_6m",
                "exp_average_profit",
                "cltv_3m",
                "cltv_6m",
            ]
        ]
        .head(10)
        .round(2)
        .to_string()
    )
    return result


def assign_cltv_segments(cltv_df: pd.DataFrame) -> pd.DataFrame:
    """6 aylık CLTV skoruna göre A/B/C/D çeyrek segmentleri."""
    print("\n" + "=" * 70)
    print("CLTV - A/B/C/D SEGMENTASYONU")
    print("=" * 70)

    result = cltv_df.copy()
    cltv = result["cltv_6m"]

    try:
        result["cltv_segment"] = pd.qcut(cltv, 4, labels=CLTV_SEGMENT_ORDER[::-1])
    except ValueError:
        result["cltv_segment"] = pd.qcut(
            cltv.rank(method="first"),
            4,
            labels=CLTV_SEGMENT_ORDER[::-1],
        )

    result["cltv_segment"] = pd.Categorical(
        result["cltv_segment"],
        categories=CLTV_SEGMENT_ORDER,
        ordered=True,
    )
    return result


def profile_cltv_segments(customer_df: pd.DataFrame) -> pd.DataFrame:
    print("\nCLTV segment profilleri:")

    profile_cols = [
        "cltv_3m",
        "cltv_6m",
        "exp_purchases_3m",
        "exp_purchases_6m",
        "exp_average_profit",
        "repeat_frequency",
        "avg_monetary",
        "total_monetary",
        "recency_days",
        "is_churn",
    ]
    available = [c for c in profile_cols if c in customer_df.columns]

    profile = (
        customer_df.groupby("cltv_segment", observed=False)[available]
        .mean()
        .reindex(CLTV_SEGMENT_ORDER)
        .round(2)
    )
    counts = customer_df["cltv_segment"].value_counts().reindex(CLTV_SEGMENT_ORDER)
    profile.insert(0, "customer_count", counts)
    profile.insert(1, "percentage", (counts / counts.sum() * 100).round(2))

    print(profile.to_string())
    return profile


def cross_compare_cltv_kmeans(
    customer_df: pd.DataFrame,
    output_path: str = "cltv_kmeans_crosstab.png",
) -> pd.DataFrame:
    print("\n" + "=" * 70)
    print("CLTV × K-MEANS ÇAPRAZ KARŞILAŞTIRMA")
    print("=" * 70)

    if "kmeans_segment" not in customer_df.columns:
        raise ValueError("kmeans_segment bulunamadı. Önce Adım 3 K-Means tamamlanmalı.")

    scored = customer_df.dropna(subset=["cltv_segment", "kmeans_segment"]).copy()

    kmeans_cats = [s for s in KMEANS_SEGMENT_ORDER if s in scored["kmeans_segment"].unique()]
    extra = [s for s in scored["kmeans_segment"].unique() if s not in kmeans_cats]
    kmeans_cats = kmeans_cats + extra

    count_ct = pd.crosstab(
        scored["kmeans_segment"],
        scored["cltv_segment"],
    ).reindex(index=kmeans_cats, columns=CLTV_SEGMENT_ORDER, fill_value=0)

    row_pct = pd.crosstab(
        scored["kmeans_segment"],
        scored["cltv_segment"],
        normalize="index",
    ).reindex(index=kmeans_cats, columns=CLTV_SEGMENT_ORDER, fill_value=0) * 100

    print("\nÇapraz tablo (adet):")
    print(count_ct.to_string())
    print("\nSatır yüzdesi (K-Means kümesi içindeki CLTV dağılımı, %):")
    print(row_pct.round(2).to_string())

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    sns.heatmap(
        count_ct,
        annot=True,
        fmt="d",
        cmap="YlOrRd",
        ax=axes[0],
        cbar_kws={"label": "Müşteri sayısı"},
    )
    axes[0].set_title("CLTV Segment × K-Means Cluster (Adet)")
    axes[0].set_xlabel("CLTV Segment")
    axes[0].set_ylabel("K-Means Segment")

    sns.heatmap(
        row_pct,
        annot=True,
        fmt=".1f",
        cmap="YlGnBu",
        ax=axes[1],
        cbar_kws={"label": "Satır %"},
    )
    axes[1].set_title("CLTV Segment × K-Means Cluster (Satır %)")
    axes[1].set_xlabel("CLTV Segment")
    axes[1].set_ylabel("K-Means Segment")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"\n[+] Cross-tabulation heatmap kaydedildi: {output_path}")

    return count_ct


def run_cltv_modeling(customer_df: pd.DataFrame) -> pd.DataFrame:
    """Adım 4'ün uçtan uca orkestrasyonu. CLTV kolonlarını customer_df'e ekler."""
    cltv_df = prepare_cltv_inputs(customer_df)
    check_gamma_gamma_assumption(cltv_df)

    bgf = fit_bgnbd_model(cltv_df)
    cltv_df = predict_expected_purchases(bgf, cltv_df)

    ggf = fit_gamma_gamma_model(cltv_df)
    cltv_df = predict_expected_profit(ggf, cltv_df)
    cltv_df = compute_cltv_values(bgf, cltv_df)
    cltv_df = assign_cltv_segments(cltv_df)

    result = customer_df.copy()
    add_cols = [
        "exp_purchases_3m",
        "exp_purchases_6m",
        "exp_average_profit",
        "cltv_3m",
        "cltv_6m",
        "cltv_segment",
    ]
    for col in add_cols:
        result[col] = cltv_df[col]

    n_missing = result["cltv_6m"].isna().sum()
    if n_missing:
        print(f"\n[!] {n_missing} müşteriye CLTV atanamadı (geçersiz T/monetary).")

    profile_cltv_segments(result)
    cross_compare_cltv_kmeans(result)

    return result
