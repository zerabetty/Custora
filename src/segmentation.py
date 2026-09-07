from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import pandas as pd
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt


def evaluate_kmeans_clusters(kmeans_scaled_df, k_range=range(2, 11)):
    print("\n" + "=" * 70)
    print("K-MEANS - OPTIMAL K ANALİZİ")
    print("=" * 70)

    results = []

    for k in k_range:
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10
        )

        labels = model.fit_predict(kmeans_scaled_df)

        inertia = model.inertia_
        silhouette = silhouette_score(
            kmeans_scaled_df,
            labels
        )

        results.append({
            "k": k,
            "inertia": inertia,
            "silhouette_score": silhouette
        })

    results_df = pd.DataFrame(results)

    results_df["inertia"] = results_df["inertia"].round(2)
    results_df["silhouette_score"] = (
        results_df["silhouette_score"].round(4)
    )

    print("\nK değerlerine göre sonuçlar:")
    print(results_df.to_string(index=False))

    best_k = results_df.loc[
        results_df["silhouette_score"].idxmax(),
        "k"
    ]

    print(
        f"\nEn yüksek Silhouette Score'a sahip K: {int(best_k)}"
    )

    return results_df

def fit_kmeans_model(kmeans_scaled_df, n_clusters=4):
    print("\n" + "=" * 70)
    print("K-MEANS - FINAL MODEL")
    print("=" * 70)

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    cluster_labels = model.fit_predict(kmeans_scaled_df)

    cluster_counts = (
        pd.Series(cluster_labels)
        .value_counts()
        .sort_index()
    )

    cluster_percentages = (
        cluster_counts / len(cluster_labels) * 100
    ).round(2)

    cluster_summary = pd.DataFrame({
        "customer_count": cluster_counts,
        "percentage": cluster_percentages
    })

    print(f"\nSeçilen K: {n_clusters}")

    print("\nCluster dağılımları:")
    print(cluster_summary.to_string())

    return model, cluster_labels, cluster_summary

def profile_clusters(customer_df, cluster_labels):
    print("\n" + "=" * 70)
    print("K-MEANS - CLUSTER PROFILING")
    print("=" * 70)

    profiled_df = customer_df.copy()
    profiled_df["cluster"] = cluster_labels

    profile_features = [
        "recency_days",
        "total_orders",
        "total_monetary",
        "avg_monetary",
        "avg_basket_items",
        "total_quantity",
        "ratio_bikes",
        "ratio_accessories",
        "ratio_clothing",
        "ratio_components",
        "is_churn",
        "is_matured"
    ]

    cluster_profile = (
        profiled_df
        .groupby("cluster")[profile_features]
        .mean()
        .round(2)
    )

    cluster_sizes = (
        profiled_df["cluster"]
        .value_counts()
        .sort_index()
        .rename("customer_count")
    )

    cluster_profile = cluster_profile.join(cluster_sizes)

    cluster_profile["percentage"] = (
        cluster_profile["customer_count"]
        / len(profiled_df)
        * 100
    ).round(2)

    print("\nCluster profilleri:")
    print(cluster_profile.to_string())

    return profiled_df, cluster_profile

def analyze_cluster_medians(profiled_df):
    print("\n" + "=" * 70)
    print("K-MEANS - CLUSTER MEDIAN ANALİZİ")
    print("=" * 70)

    median_features = [
        "recency_days",
        "total_orders",
        "total_monetary",
        "avg_monetary",
        "avg_basket_items",
        "total_quantity"
    ]

    cluster_medians = (
        profiled_df
        .groupby("cluster")[median_features]
        .median()
        .round(2)
    )

    print("\nCluster median değerleri:")
    print(cluster_medians.to_string())

    return cluster_medians

def assign_cluster_names(profiled_df):
    print("\n" + "=" * 70)
    print("K-MEANS - BUSINESS SEGMENT İSİMLENDİRME")
    print("=" * 70)

    cluster_name_map = {
        0: "Accessory Shoppers",
        1: "Bike Buyers",
        2: "Clothing Shoppers",
        3: "High-Value Customers"
    }

    result_df = profiled_df.copy()

    result_df["kmeans_segment"] = (
        result_df["cluster"]
        .map(cluster_name_map)
    )

    segment_summary = (
        result_df["kmeans_segment"]
        .value_counts()
        .to_frame("customer_count")
    )

    segment_summary["percentage"] = (
        segment_summary["customer_count"]
        / len(result_df)
        * 100
    ).round(2)

    print("\nBusiness segment dağılımları:")
    print(segment_summary.to_string())

    return result_df, segment_summary

def visualize_clusters_pca(kmeans_scaled_df, cluster_labels):
    print("\n" + "=" * 70)
    print("K-MEANS - PCA GÖRSELLEŞTİRME")
    print("=" * 70)

    pca = PCA(n_components=2)

    pca_components = pca.fit_transform(kmeans_scaled_df)

    explained_variance = (
        pca.explained_variance_ratio_.sum() * 100
    )

    print(
        f"\nİlk 2 PCA bileşeninin açıkladığı toplam varyans: "
        f"%{explained_variance:.2f}"
    )

    pca_df = pd.DataFrame(
        pca_components,
        columns=["PC1", "PC2"]
    )

    pca_df["cluster"] = cluster_labels

    plt.figure(figsize=(10, 6))

    scatter = plt.scatter(
        pca_df["PC1"],
        pca_df["PC2"],
        c=pca_df["cluster"],
        alpha=0.5
    )

    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")
    plt.title("K-Means Customer Segments - PCA")

    plt.legend(
        *scatter.legend_elements(),
        title="Cluster"
    )

    plt.tight_layout()
    plt.savefig("kmeans_pca_clusters.png", dpi=150)
    print("\n[+] PCA kümeleme görseli kaydedildi: kmeans_pca_clusters.png")
    plt.close()

    return pca_df, pca