# SÜREÇ RAPORU

## Adım 2 – EDA & Preprocessing

### İlk EDA, Churn Target ve RFM Kontrolleri

Adım 1’de oluşturulan müşteri bazlı analitik tablonun genel yapısını kontrol etmek, veri kalitesi ve dağılımları incelemek ve modelleme aşamalarına geçmeden önce özellikle **churn target ile RFM segmentlerinin davranışsal olarak tutarlı olup olmadığını değerlendirmek** amaçlandı.

## 1. Veri Setinin Genel Kontrolü

Adım 1 sonucunda oluşturulan `customer_features` veri seti incelendi.

**Temel bulgular:**

- Müşteri sayısı: **13.020**
- Değişken sayısı: **29**
- Eksik değer: **Yok**
- Duplicate satır: **Yok**
- Mevcut churn tanımı: Cut-off tarihinden sonraki **6 aylık hedef dönemde sipariş vermeyen müşteri = churn**
- Churn müşteri: **8.657 (%66,49)**
- Retained müşteri: **4.363 (%33,51)**

Sayısal değişkenlerin ilk incelemesinde özellikle `total_monetary`, kategori harcamaları, `total_quantity` ve `avg_basket_items` gibi değişkenlerde ortalama ile maksimum değerler arasında oldukça büyük farklar olduğu görüldü.

**Bulgu:** Bazı sayısal değişkenlerde güçlü sağa çarpıklık ve yüksek uç değerler bulunuyor.
**Yorum:** Bu değerlerin bir kısmı gerçek yüksek değerli müşterileri temsil ediyor olabilir.
**Karar:** Bu aşamada gözlemler silinmedi veya otomatik olarak baskılanmadı. Dağılım ve outlier analizinden sonra gerekli değişkenlerde capping/log transformation değerlendirilecek.

## 2. RFM Segmentleri ile Churn Arasında Beklenmeyen İlişki

İlk analizde RFM segmentlerinin churn oranlarında beklenen davranışsal sıralamanın oluşmadığı görüldü.

örneğin;

| RFM Segmenti | Churn Oranı |
| --- | --- |
| Hibernating | %29,07 |
| Loyal Customers | %69,06 |
| Champions | %74,23 |
| Can't Lose | %94,72 |
| Potential Loyalists | %94,81 |
| Need Attention | %100 |

Normal beklentinin aksine bazı güçlü/yakın dönem müşterilerinin churn oranlarının, uzun süredir aktif olmayan müşterilerden daha yüksek olması nedeniyle doğrudan modellemeye geçmek yerine bu durumun kaynağı araştırıldı.

## 3. Inter-Purchase Time – Satın Alma Döngüsü Analizi

Sabit 6 aylık churn penceresinin veri setine uygunluğunu değerlendirmek amacıyla müşterilerin ardışık siparişleri arasındaki süreler hesaplandı.

**12.346 tekrar satın alma aralığı** üzerinden elde edilen sonuçlar:

| Metrik | Süre |
| --- | --- |
| Ortalama | **261 gün** |
| Medyan | **138 gün** |
| %25 | 91 gün |
| %75 | **411 gün** |
| %90 | 634,5 gün |
| %95 | 780,75 gün |

Ayrıca:

- 180 günden uzun satın alma aralıkları: **%44,76**
- 270 günden uzun: **%36,48**
- 365 günden uzun: **%28,24**

**Bulgu:** Tekrar satın alma aralıklarının %44,76'sı 6 aydan uzun ve ortalama tekrar satın alma süresi yaklaşık 261 gün.
**Yorum:** Her müşteri için “6 ay sipariş vermedi = churn” yaklaşımı AdventureWorks satın alma davranışını tam olarak temsil etmeyebilir.
**Karar:** 6 aylık churn tanımını hemen değiştirmek yerine 6, 9 ve 12 aylık alternatif target pencereleri karşılaştırıldı.

## 4. Churn Horizon Sensitivity Analysis

Alternatif churn pencerelerinin etkisini görmek amacıyla 6, 9 ve 12 aylık target senaryoları oluşturuldu.

Her senaryoda target için yeterli gelecek veri bulunabilmesi amacıyla cut-off tarihi yeniden hesaplandı.

| Target Window | Observation Customer | Churn | Retained |
| --- | --- | --- | --- |
| 6 ay | 13.020 | **%66,49** | %33,51 |
| 9 ay | 9.711 | **%45,05** | %54,95 |
| 12 ay | 6.093 | **%16,67** | %83,33 |

İlk aşamada, ortalama satın alma süresinin yaklaşık 9 ay olması ve müşteri sayısının 12 aylık senaryoya göre daha fazla korunması nedeniyle **9 aylık pencerenin daha uygun olabileceği düşünüldü.**

Ancak bu varsayım doğrudan kabul edilmedi ve RFM segmentleri her cut-off için yeniden oluşturularak ayrıca test edildi.

## 5. RFM × Churn Horizon Kontrolü

RFM segmentleri 6, 9 ve 12 aylık senaryolar için ilgili observation dönemlerinden yeniden hesaplandı.

| RFM Segmenti | 6 Ay | 9 Ay | 12 Ay |
| --- | --- | --- | --- |
| About to Sleep | %76,60 | %38,33 | %0,00 |
| At Risk | %61,82 | %27,52 | %5,98 |
| Can't Lose | %94,72 | %81,10 | %69,05 |
| Champions | %74,23 | %64,49 | %43,23 |
| Hibernating | %29,07 | **%0,05** | %0,00 |
| Loyal Customers | %69,06 | %61,83 | %25,08 |
| Need Attention | %100 | %78,88 | %0,00 |
| New Customers | %53,60 | %40,68 | %21,00 |
| Potential Loyalists | %94,81 | **%84,76** | %9,29 |
| Promising | %60,42 | %41,10 | %0,00 |

Özellikle 9 aylık senaryoda `hibernating` müşterilerin **%99,95'inin target döneminde yeniden alışveriş yaptığı**, buna karşılık `potential_loyalists` müşterilerinin yalnızca **%15,24'ünün geri döndüğü** görüldü.

**Bulgu:** Target penceresini 6 aydan 9 veya 12 aya çıkarmak RFM–churn ilişkisindeki anomalileri ortadan kaldırmadı.
**Yorum:** Problem yalnızca churn penceresinin kısa olmasından kaynaklanmıyor olabilir. Veri setinin zamansal/cohort yapısının ve RFM skorlamasının ayrıca incelenmesi gerektiği düşünüldü.
**Karar:** 9 aylık pencereye geçme fikri bu aşamada terk edildi. 6 aylık target şimdilik **baseline churn definition** olarak korunacak.

## 6. Temporal & Cohort Analizi

Anormal churn davranışının kaynağını araştırmak amacıyla aylık sipariş/müşteri hareketleri ve müşteri cohort'ları incelendi.

Veri dönemi: **30.05.2022 – 29.06.2025** 
Özellikle 2024 ortasında müşteri ve sipariş hacminde belirgin bir değişim görüldü.

| Ay | Tekil Sipariş | Tekil Müşteri |
| --- | --- | --- |
| 2024-03 | 443 | 443 |
| 2024-04 | 426 | 426 |
| 2024-05 | 436 | 433 |
| 2024-06 | 741 | 735 |
| **2024-07** | **1.755** | **1.694** |
| 2024-08 | 1.785 | 1.723 |
| 2024-09 | 1.796 | 1.744 |
| 2024-12 | 2.053 | 1.975 |
| 2025-03 | 2.304 | 2.246 |

Bu değişim, observation ve target dönemlerinin her zaman aynı müşteri davranışı dağılımını temsil etmeyebileceğini gösteren önemli bir EDA bulgusu olarak kaydedildi.
Cohort analizi ayrıca eski müşteri gruplarının sonraki yıllarda yeniden aktif olabildiğini gösterdi.

## 7. Müşteri Sipariş Frekansı ve RFM Frequency Score Kontrolü

Tüm dönem için müşteri başına sipariş sayısı incelendi.

- **1 sipariş:** 11.649 müşteri – **%60,93**
- **2 sipariş:** 5.473 müşteri – **%28,63**
- **3 sipariş:** 1.204 müşteri – %6,30

Dolayısıyla müşterilerin yaklaşık **%89,56'sı yalnızca 1 veya 2 siparişe sahip.**

Mevcut RFM hesaplamasında frequency score:

```python
pd.qcut(
    order_agg["total_orders"].rank(method="first"),
    5,
    labels=[1, 2, 3, 4, 5]
)
```

ile oluşturuluyor.

Çok sayıda müşterinin aynı sipariş sayısına sahip olması nedeniyle `rank(method="first")`, aynı gerçek frequency değerine sahip müşterileri sıralarına göre farklı rank'lere ayırabiliyor. Bunun sonucunda davranışları aynı olan tek siparişli müşterilerin farklı RFM segmentlerine düşebildiği gözlendi.

Nitekim 9 aylık kontrolde `potential_loyalists`, `hibernating`, `at_Risk`, `new_customers`, `promising`, `need_attention`ve `about_to_sleep` gibi farklı segmentlerin ortalama sipariş sayısı **1,00** olarak bulundu.

**Bulgu:** Veri setinde frequency değişkeninin dağılımı oldukça sıkışık ve müşterilerin çoğu tek siparişli. Mevcut

```
rank(method="first") + qcut
```

yöntemi aynı sipariş frekansındaki müşterileri farklı skor gruplarına ayırabiliyor.

**Yorum:** RFM–churn ilişkisindeki beklenmeyen sonuçların bir bölümü churn tanımından değil, frequency scoring yönteminden kaynaklanıyor olabilir.
**Karar (güncellendi):** Frequency skoru `rank(method="first") + qcut` yerine gerçek sipariş adedine dayalı `pd.cut` ile yeniden tanımlandı:

```python
pd.cut(
    order_agg["total_orders"],
    bins=[0, 1, 2, 3, 5, np.inf],
    labels=[1, 2, 3, 4, 5]
)
```

Aynı sipariş sayısına sahip müşteriler artık aynı frequency skorunu alıyor. RFM segmentleri davranışsal olarak yeniden okunabilir hale geldi.

## 8. Sayısal Değişkenlerin Dağılım ve Skewness Analizi

Modelleme öncesinde sayısal değişkenlerin dağılımları; ortalama, medyan, standart sapma, maksimum değer, skewness ve sıfır oranları üzerinden incelendi.

Özellikle parasal ve alışveriş hacmini temsil eden değişkenlerde güçlü sağa çarpıklık tespit edildi.

| Değişken | Skewness | Zero Rate |
| --- | --- | --- |
| discount_ratio | 16.81 | %97.47 |
| spend_accessories | 13.63 | %36.23 |
| spend_components | 13.34 | %95.62 |
| spend_clothing | 13.28 | %70.25 |
| spend_bikes | 11.24 | %40.35 |
| total_quantity | 11.18 | %0 |
| total_monetary | 10.93 | %0 |
| avg_basket_items | 10.34 | %0 |
| avg_monetary | 9.04 | %0 |
| total_orders | 5.19 | %0 |

Kategori bazlı harcama değişkenlerinde yüksek skewness değerlerinin önemli bir kısmının müşterilerin ilgili kategoriden hiç alışveriş yapmamasından kaynaklandığı görüldü. Örneğin müşterilerin %95,62’sinde `spend_components = 0`.

**Bulgu:** Parasal ve hacim değişkenlerinde güçlü sağa çarpıklık bulunurken kategori değişkenlerinin bir kısmında çok yüksek sıfır oranları bulunuyor.
**Yorum:** Sıfır değerler eksik veya hatalı veri değil, gerçek müşteri davranışını temsil ediyor. Bu nedenle yüksek skewness görülen her değişkene aynı preprocessing işleminin uygulanması uygun değil.
**Karar:** Otomatik dönüşüm veya outlier silme uygulanmadı. Öncelikle quantile/outlier yapısı ayrıca incelendi.

## 9. Outlier / Quantile Analizi

Yüksek skewness gösteren parasal ve alışveriş hacmi değişkenlerinde P50, P90, P95, P99, maksimum değer ve IQR sınırları karşılaştırıldı.

Öne çıkan bazı sonuçlar:

| Değişken | P50 | P95 | P99 | Max | IQR Outlier % |
| --- | --- | --- | --- | --- | --- |
| total_monetary | 819.46 | 6,753.24 | 182,358.22 | 740,601.77 | %3.88 |
| avg_monetary | 782.99 | 3,578.27 | 36,935.22 | 139,600.82 | %2.70 |
| total_quantity | 2 | 8 | 464.72 | 2,196 | %4.89 |
| avg_basket_items | 2 | 4 | 93.36 | 349.67 | %3.35 |
| spend_bikes | 782.99 | 6,021.62 | 145,732.38 | 646,813.98 | %4.03 |
| spend_clothing | 0 | 87.47 | 3,309.12 | 25,314.66 | %23.40 |
| spend_components | 0 | 0 | 26,825.73 | 167,305.14 | %4.38 |

Özellikle `spend_components` değişkeninde IQR üst sınırının **0** olması dikkat çekti. Bunun nedeni müşterilerin büyük çoğunluğunun bu kategoriden alışveriş yapmaması.

Benzer şekilde `spend_clothing` için klasik IQR yöntemi müşterilerin %23,40’ını outlier olarak tanımladı.

**Bulgu:** Klasik IQR yöntemi bazı değişkenlerde gerçek yüksek değerli müşteri davranışlarını outlier olarak işaretliyor.
**Yorum:** Bu müşterileri silmek veya agresif biçimde cap etmek, müşteri değerindeki gerçek farklılıkları kaybetmemize neden olabilir.
**Karar:** Bu aşamada IQR tabanlı capping uygulanmamasına karar verildi. Bunun yerine yüksek sağa çarpık değişkenlerde `log1p` dönüşümünün etkisi test edildi.

## 10. Log Transformation Etki Analizi

Outlier değerlerini doğrudan silmek veya baskılamak yerine `log1p` dönüşümünün dağılımlar üzerindeki etkisi ölçüldü.

| Değişken | Original Skew | Log1p Skew |
| --- | --- | --- |
| spend_accessories | 13.63 | **0.04** |
| spend_clothing | 13.28 | **1.53** |
| spend_bikes | 11.24 | **-0.24** |
| total_monetary | 10.93 | **-0.07** |
| avg_monetary | 9.04 | **-0.30** |
| spend_components | 13.34 | 4.82 |
| total_quantity | 11.18 | 3.79 |
| avg_basket_items | 10.34 | 3.96 |

Özellikle `total_monetary`, `spend_bikes`, `spend_accessories` ve `avg_monetary` değişkenlerinde log dönüşümünün sağa çarpıklığı büyük ölçüde azalttığı görüldü.

Zero-inflated değişkenlerde ise dönüşüm dağılımı iyileştirse de yüksek sıfır oranından kaynaklanan yapıyı tamamen ortadan kaldırmadı.

**Bulgu:** log1p, özellikle parasal değişkenlerde dağılımı önemli ölçüde iyileştiriyor.
**Yorum:** Böylece yüksek değerli müşterileri veri setinden silmeden ekstrem değerlerin uzaklık tabanlı modeller üzerindeki etkisi azaltılabilir.
**Karar:** Ham `customer_features`tablosu değiştirilmedi. Log dönüşümlerinin model ihtiyacına göre ayrı feature setleri üzerinde uygulanmasına karar verildi.

## 11. Feature Correlation / Redundancy Analizi

K-Means modeline birbirinin aynı veya çok benzer bilgileri taşıyan değişkenleri birlikte vermemek amacıyla sayısal feature’lar arasındaki korelasyonlar incelendi.

Öne çıkan yüksek korelasyonlar:

| Feature 1 | Feature 2 | Korelasyon |
| --- | --- | --- |
| total_orders | repeat_frequency | **1.000** |
| total_monetary | spend_bikes | **0.995** |
| total_monetary | total_quantity | **0.926** |
| spend_accessories | spend_clothing | **0.918** |
| total_quantity | spend_clothing | **0.918** |
| total_quantity | spend_components | **0.897** |
| total_monetary | spend_components | **0.889** |
| avg_monetary | avg_basket_items | **0.884** |
| total_monetary | avg_monetary | **0.863** |
| ratio_bikes | ratio_accessories | **-0.843** |

**Bulgu:** Birçok feature aynı müşteri davranışını yüksek oranda tekrar ediyor.

**Yorum:** Bu değişkenlerin tamamının K-Means’e verilmesi belirli davranış boyutlarının modelde birden fazla kez ağırlıklandırılmasına neden olabilir.

**Karar:** K-Means için daha küçük, davranışsal olarak yorumlanabilir ve farklı müşteri boyutlarını temsil eden bir feature set oluşturuldu. Değişkenler ana veri setinden silinmedi; yalnızca clustering feature setinden çıkarıldı.

## 12. K-Means İçin Feature Selection ve Preprocessing

EDA sonuçları doğrultusunda K-Means için aşağıdaki ilk feature set oluşturuldu:

```python
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
```

Bu feature set ile temel olarak şu müşteri boyutlarının temsil edilmesi amaçlandı:

- **Recency:** Müşterinin ne kadar yakın zamanda alışveriş yaptığı
- **Frequency:** Toplam sipariş sayısı
- **Monetary:** Toplam müşteri değeri
- **Basket Behavior:** Ortalama sepet büyüklüğü
- **Category Preference:** Bikes, Accessories, Clothing ve Components harcama tercihleri

Güçlü sağa çarpıklık nedeniyle K-Means feature setinde `total_monetary` ve `avg_basket_items` değişkenlerine `log1p`dönüşümü uygulandı.

Ardından K-Means uzaklık tabanlı bir algoritma olduğu için tüm seçili feature’lar `StandardScaler` ile standartlaştırıldı.

Ölçekleme sonrasında tüm değişkenlerde:

- Ortalama ≈ **0**
- Standart sapma ≈ **1**

elde edilerek preprocessing işleminin beklendiği şekilde çalıştığı doğrulandı.

Bununla birlikte `total_orders` ve özellikle zero-inflated `ratio_components` değişkenlerinde standartlaştırma sonrasında ekstrem değerlerin devam ettiği görüldü. Bu durum veri hatası olarak değerlendirilmedi ve bu aşamada capping uygulanmadı.

**Bulgu → Yorum → Karar**

> **Bulgu:** K-Means için seçilen feature’lar başarıyla dönüştürüldü ve ölçeklendi. Bununla birlikte bazı seyrek müşteri davranışları standartlaştırma sonrasında da ekstrem değerler oluşturuyor.
> 
> 
> **Yorum:** StandardScaler dağılımı normalleştirmez; yalnızca feature’ları ortak ölçeğe getirir. Bu nedenle bu değerlerin clustering üzerindeki etkisi model sonuçlarında ayrıca değerlendirilmelidir.
> 
> **Karar:** İlk K-Means modeli mevcut feature set ile kurulacak. Optimal K seçiminde yalnızca matematiksel skorlar değil, cluster büyüklükleri ve business interpretability de değerlendirilecek.
> 

# ADIM 3 – K-MEANS MÜŞTERİ SEGMENTASYONU

## 1. Amaç

Bu aşamada müşterilerin önceden tanımlanmış segment kurallarına bağlı kalmadan, gözlem dönemindeki davranışsal özelliklerine göre K-Means algoritması ile gruplandırılması amaçlanmıştır.

RFM segmentasyonundan farklı olarak K-Means analizinde yalnızca recency, frequency ve monetary bilgileri değil; müşterilerin sepet yapısı ve ürün kategorilerine yönelik harcama tercihleri de dikkate alınmıştır.

K-Means modeli için aşağıdaki değişkenler kullanılmıştır:

```python
recency_days
total_orders
total_monetary
avg_basket_items
ratio_bikes
ratio_accessories
ratio_clothing
ratio_components
```

Adım 2'de yapılan dağılım ve korelasyon analizleri sonucunda yüksek derecede birbirini tekrar eden değişkenlerin aynı anda modele alınmamasına dikkat edilmiştir.

`total_monetary` ve `avg_basket_items` değişkenlerine `log1p` dönüşümü uygulanmış, ardından tüm K-Means değişkenleri `StandardScaler` ile ölçeklendirilmiştir.

Aykırı değerler otomatik olarak silinmemiş veya IQR ile baskılanmamıştır. Bunun nedeni yüksek harcama/hacim değerlerinin gerçek yüksek değerli müşteri davranışını temsil ediyor olabileceğinin değerlendirilmesidir.

## 2. Optimal Cluster Sayısının Belirlenmesi

K-Means için K=2–10 aralığı test edilmiştir.

Her K değeri için:

- Inertia
- Silhouette Score

hesaplanmıştır.

| K | Inertia | Silhouette |
| --- | --- | --- |
| 2 | 66673.20 | 0.4802 |
| 3 | 47287.51 | 0.5248 |
| **4** | **35120.67** | **0.5805** |
| 5 | 26063.23 | 0.5670 |
| 6 | 18801.36 | 0.5746 |
| 7 | 16403.53 | 0.5758 |
| 8 | 14610.06 | 0.5256 |
| 9 | 13183.01 | 0.5286 |
| 10 | 11766.59 | 0.4980 |

En yüksek Silhouette Score **K=4 için 0.5805** olarak elde edilmiştir.

K=4 yalnızca maksimum Silhouette değerine dayanarak seçilmemiş; inertia değişimi, cluster büyüklükleri ve sonraki profiling sonuçlarıyla birlikte değerlendirilmiştir.

**Karar:** Final K-Means modeli için `K=4` kullanılmıştır.

## 3. Cluster Dağılımları

K=4 ile oluşturulan model sonucunda:

| Cluster | Müşteri | Oran |
| --- | --- | --- |
| 0 | 3.778 | %29.02 |
| 1 | 7.303 | %56.09 |
| 2 | 1.405 | %10.79 |
| 3 | 534 | %4.10 |

En küçük cluster'ın dahi 534 müşteriden oluşması nedeniyle modelin yalnızca birkaç ekstrem gözlemi ayrı bir cluster'a topladığı yönünde belirgin bir bulgu görülmemiştir.

## 4. Cluster Profiling

Cluster'ların iş anlamını belirlemek amacıyla her grubun müşteri davranışları incelenmiştir.

| Cluster | Recency | Orders | Monetary | Basket Items | Bike Ratio | Accessory Ratio | Clothing Ratio | Components Ratio | Churn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 88.78 | 1.13 | 48.95 | 2.24 | 0.00 | 0.97 | 0.03 | 0.00 | 0.81 |
| 1 | 257.11 | 1.43 | 2,958.25 | 1.83 | 0.99 | 0.01 | 0.00 | 0.00 | 0.60 |
| 2 | 87.86 | 1.20 | 85.95 | 2.26 | 0.00 | 0.22 | 0.78 | 0.00 | 0.80 |
| 3 | 137.21 | 5.59 | 121,873.83 | 61.65 | 0.67 | 0.04 | 0.05 | 0.24 | 0.23 |

Modelin müşteri gruplarını yalnızca parasal değer açısından değil, **ürün kategorisi tercihlerine göre de belirgin biçimde ayırdığı** görülmüştür.

## 5. Median Kontrolü ve Outlier Kararının Doğrulanması

Özellikle Cluster 3'ün yüksek ortalama değerlerinin birkaç ekstrem müşteriden kaynaklanıp kaynaklanmadığını kontrol etmek amacıyla cluster bazında median değerleri hesaplanmıştır.

| Cluster | Recency Median | Orders Median | Monetary Median | Avg Monetary Median | Basket Median | Quantity Median |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 88 | 1 | 37.97 | 36.27 | 2.00 | 2 |
| 1 | 155 | 1 | 2,443.35 | 2,071.42 | 1.50 | 2 |
| 2 | 86 | 1 | 78.98 | 69.99 | 2.00 | 2 |
| 3 | 91 | 6 | 58,218.78 | 11,678.95 | 31.35 | 152 |

Cluster 3'te median müşterinin dahi 6 sipariş, 58 binin üzerinde toplam monetary ve 152 ürün seviyesinde olması, bu grubun birkaç ekstrem gözlemden ibaret olmadığını göstermektedir.

Bu bulgu Adım 2'de verilen **“aykırı değerleri otomatik olarak silmeme/cap uygulamama” kararını desteklemektedir.**

## 6. Business Segment İsimlendirmesi

K-Means algoritması cluster'lara iş anlamı vermemektedir. Algoritma müşterileri feature uzayındaki benzerliklerine göre `0–3` şeklinde gruplandırmıştır.

Profiling sonuçları incelendikten sonra cluster'lara aşağıdaki iş isimleri atanmıştır:

| Cluster | Business Segment | Müşteri | Oran |
| --- | --- | --- | --- |
| 0 | **Accessory Shoppers** | 3.778 | %29.02 |
| 1 | **Bike Buyers** | 7.303 | %56.09 |
| 2 | **Clothing Shoppers** | 1.405 | %10.79 |
| 3 | **High-Value Customers** | 534 | %4.10 |

İsimlendirmede `Champions`, `Loyal` veya `At Risk` gibi RFM/CLTV terminolojisi özellikle kullanılmamıştır. K-Means'in ortaya çıkardığı davranışsal yapı ile RFM segmentlerinin birbirine karıştırılmaması amaçlanmıştır.

# ADIM 4 – CLTV TAHMİNİ (BG/NBD & GAMMA-GAMMA)

## 1. Amaç

Bu aşamada `lifetimes` kütüphanesi ile perakende sektör standardı olan **BG/NBD + Gamma-Gamma** yaklaşımı kullanılarak müşterilerin gelecek 3 ve 6 aydaki beklenen işlem sayısı, işlem başı beklenen kârı ve tahmini CLTV değerleri üretilmiştir.

Modelleme, Adım 1'de observation penceresinden türetilen lifetimes metrikleri üzerinde kurulmuştur (data leakage yok):

| lifetimes alanı | Kaynak kolon | Tanım |
| --- | --- | --- |
| `frequency` | `repeat_frequency` | Tekrar eden işlem sayısı (`total_orders - 1`) |
| `recency` | `lifetimes_recency_days / 7` | İlk–son sipariş arası süre (hafta) |
| `T` | `customer_age_t_days / 7` | Müşteri yaşı, cut-off'a kadar (hafta) |
| `monetary` | `avg_monetary` | İşlem başına ortalama harcama |

Süreler haftaya çevrilmiş; 3 ay = 12 hafta, 6 ay = 24 hafta alınmıştır. CLTV iskontosu aylık %1 (`discount_rate=0.01`) ile uygulanmıştır.

K-Means çapraz karşılaştırmasının tüm portföyü kapsaması için tek siparişli müşteriler model dışı bırakılmamıştır.

## 2. Veri Yapısı ve Uç Değer Kararı

| Metrik | Değer |
| --- | --- |
| Modellenen müşteri | **13.020** |
| Tekrar alıcı (`frequency > 0`) | 3.883 (%29,82) |
| Tek siparişli (`frequency = 0`) | 9.137 (%70,18) |
| Frequency uç değer baskılama | 1 müşteri |
| Monetary uç değer baskılama | 7 müşteri |

K-Means'te uç değerler silinmemişti; CLTV'de **0.01–0.99 quantile + 1.5 IQR** baskılama yalnızca model kopyasına uygulandı. Ham `customer_features` değerleri değiştirilmedi.

Ortalama frequency 0,49; medyan 0. Portföyün büyük kısmı henüz tekrar satın alma üretmemiş müşterilerden oluşuyor.

## 3. BG/NBD Modeli — Beklenen İşlem Sayısı

`BetaGeoFitter.conditional_expected_number_of_purchases_up_to_time` ile 3 ve 6 aylık beklenen işlem sayıları tahmin edildi.

`penalizer_coef=0.001` ve `0.01` yakınsamadı. Bunun nedeni tek siparişli müşteri oranının %70 olması ve uzun satın alma döngüsüdür. `penalizer_coef=0.05` ile model yakınsadı:

| Parametre | Değer | Yorum |
| --- | --- | --- |
| r | 0,5140 | Satın alma oranı şekil parametresi |
| alpha | 42,77 hafta | Satın alma oranı ölçek (~10 ay) |
| a | ≈ 0 | Dropout Beta şekil |
| b | ≈ 0 | Dropout Beta şekil |

**Bulgu:** `a≈0`, `b≈0`. Model, gözlem penceresinde belirgin bir dropout süreci görmüyor.
**Yorum:** Adım 2'deki inter-purchase analizinde medyan tekrar alma süresi 138 gün, ortalama 261 gündü. Müşterilerin önemli bir kısmı henüz bir sonraki satın alma döngüsünü tamamlamamış olabilir.
**Karar:** Dropout'suz BG/NBD (Gamma-Poisson indirgenmesi) kabul edildi. `lifetimes` kütüphanesi `frequency=1` ve `a≈0` kombinasyonunda sonsuz tahmin ürettiği için bu kayıtlarda kapalı form `(r + frequency) × t / (alpha + T)` kullanıldı.

| Ufuk | Ortalama | Medyan | Min | P75 | Max |
| --- | --- | --- | --- | --- | --- |
| 3 ay | 0,14 | 0,11 | 0,03 | 0,14 | 3,11 |
| 6 ay | 0,28 | 0,23 | 0,07 | 0,28 | 6,23 |

En yüksek beklenen işlem sayısı, kısa T ve yüksek frequency'ye sahip (yakın dönemde sık alan) müşterilerdedir.

## 4. Gamma-Gamma Modeli — Beklenen Ortalama Kâr

Gamma-Gamma yalnızca **tekrar alıcı 3.883 müşteri** üzerinde eğitildi (`frequency > 0` şartı). Tüm portföy için `conditional_expected_average_profit` hesaplandı.

| Parametre | Değer |
| --- | --- |
| p | 3,1075 |
| q | 0,2081 |
| v | 2,9011 |

Tekrar alıcılarda `corr(frequency, monetary) = 0,399`. Gamma-Gamma'nın bağımsızlık varsayımı zayıf. Bunun kaynağı Cluster 3'teki B2B benzeri yüksek frekans + yüksek sepet müşterileridir.

Ayrıca `q < 1` olduğu için popülasyon prior'ı `p·v/(q-1)` negatif/tanımsızdır. Bu durumda tek siparişli 9.137 müşteride beklenen kâr, gözlenen `avg_monetary` olarak alındı. Tekrar alıcılarda Gamma-Gamma tahmini pozitif ve gözlenen monetary ile uyumlu (korelasyon ≈ 0,99).

| | monetary | exp_average_profit |
| --- | --- | --- |
| Ortalama | 2.052 | 2.318 |
| Medyan | 783 | 783 |
| P75 | 2.211 | 2.443 |
| Max | 92.331 | 123.908 |

## 5. 3 ve 6 Aylık CLTV

İki model, beklenen işlem sayısı ile beklenen ortalama kârın çarpımı ve aylık %1 iskonto ile birleştirildi:

**CLTV = Σ (beklenen işlem_ay × beklenen ortalama kâr) / (1 + 0,01)^ay**

| Ufuk | Ortalama | Medyan | P75 | Max |
| --- | --- | --- | --- | --- |
| 3 ay | 597 | 80 | 252 | 54.113 |
| 6 ay | 1.176 | 158 | 497 | 106.634 |

Tüm 13.020 müşteriye sonlu ve negatif olmayan CLTV atandı. En yüksek CLTV'ler High-Value (Cluster 3) müşterilerindedir.

## 6. CLTV Segmentleri (A / B / C / D)

6 aylık CLTV çeyrekliklerine göre 4 eşit grup oluşturuldu (`pd.qcut`).

| Segment | Müşteri | Ort. CLTV 6ay | Ort. beklenen işlem 6ay | Ort. kâr | Ort. sipariş (repeat) | Ort. recency | Churn |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A** | 3.255 | 4.341 | 0,42 | 6.663 | 1,54 | 93 gün | %70 |
| **B** | 3.255 | 295 | 0,19 | 2.242 | 0,17 | 379 gün | %49 |
| **C** | 3.255 | 60 | 0,30 | 335 | 0,25 | 169 gün | %65 |
| **D** | 3.255 | 7 | 0,22 | 32 | 0,00 | 99 gün | %82 |

**A:** Yüksek sepet + tekrar alım geçmişi olan müşteriler. Recency görece düşük (93 gün) olsa da 6 aylık churn %70. Bisiklet döngüsü uzun olduğu için “yakın dönemde aldı = elde tutuldu” varsayımı burada da bozuluyor.

**B:** Ağırlıklı olarak eski tarihli, yüksek ticket'lı bisiklet alıcıları. Recency yüksek (379 gün) ama churn en düşük (%49). Adım 2'deki 2024 hacim sıçraması / reactivation ile uyumlu: uzun aradan sonra target penceresinde geri dönen müşteriler.

**C:** Orta-düşük sepet, karışık kategori.

**D:** Neredeyse tamamı tek siparişli, düşük sepetli (aksesuar) müşteriler. En yüksek churn (%82).

## 7. CLTV × K-Means Çapraz Karşılaştırma

| K-Means Segment | A | B | C | D | Yorum |
| --- | --- | --- | --- | --- | --- |
| Accessory Shoppers | %0 | %0 | %26,0 | **%74,0** | Düşük sepet → düşük CLTV |
| Bike Buyers | %38,3 | **%43,9** | %17,8 | %0 | Yüksek ticket bisiklet, A/B'de yoğun |
| Clothing Shoppers | %0,1 | %0,1 | **%67,5** | %32,4 | Aksesuardan biraz daha değerli, yine C/D |
| High-Value Customers | **%85,6** | %9,2 | %4,5 | %0,8 | Davranışsal küme ile CLTV A neredeyse örtüşüyor |

Heatmap: `cltv_kmeans_crosstab.png`

**Bulgu:** K-Means kategorik/davranışsal ayrımı (aksesuar / bisiklet / giyim / yüksek değer), CLTV ise gelecekteki parasal değeri sıralıyor. İki yöntem birbirinin kopyası değil, tamamlayıcısı.

**Yorum:** High-Value × A kesişimi elde tutma ve VIP programı için birincil hedef; Bike Buyers × A/B çapraz satış ve servis; Accessory/Clothing × C/D düşük maliyetli aktivasyon adayı. Adım 7 aksiyon matrisi bu kırılım üzerine kurulacak.

**Karar:** CLTV skorları ve A/B/C/D etiketleri analitik tabloya (`exp_purchases_3m`, `exp_purchases_6m`, `exp_average_profit`, `cltv_3m`, `cltv_6m`, `cltv_segment`) yazıldı. Adım 5 churn modeline feature olarak eklenecek.

# ADIM 5 – CHURN TAHMİN MODELLEMESİ

## 1. Amaç

Observation penceresindeki davranışsal metriklerin yanına Adım 3 K-Means küme etiketleri ve Adım 4 CLTV metrikleri eklenerek, 6 aylık hedef penceredeki churn (`is_churn`) tahmin edilmiştir.

Model eğitimi ve değerlendirmesi, Adım 2'de tespit edilen yapay churn gürültüsünü önlemek amacıyla **yalnızca döngüsünü tamamlamış olgun müşteriler (`is_matured == 1`)** üzerinde gerçekleştirilmiştir.

## 2. Öznitelikler ve Modelleme Evreni

| Grup | Değişkenler |
| --- | --- |
| Davranış | `recency_days`, `customer_age_t_days`, `total_orders`, `total_monetary`, `avg_monetary`, `avg_basket_items`, `discount_ratio`, kategori oranları (`ratio_bikes`, `ratio_accessories`, `ratio_clothing`, `ratio_components`) |
| K-Means | `cluster` (one-hot: 0–3) |
| CLTV | `cltv_6m`, `exp_purchases_6m`, `exp_average_profit`, `cltv_segment` (one-hot: A–D) |

Toplam 22 öznitelik. `is_matured` bir feature olarak modele verilmemiş; modelleme evrenini filtrelemek için kullanılmıştır.

| Evren | Müşteri Sayısı | Churn Oranı (%) | Retained Oranı (%) |
| --- | --- | --- | --- |
| Toplam Portföy | 13.020 | %66,49 | %33,51 |
| **Olgunlaşmış Evren (`is_matured == 1`)** | **7.001** | **%49,85** | **%50,15** |
| İzole Edilen Taze Kitle (`is_matured == 0`) | 6.019 | %85,84 | %14,16 |

Olgunlaşmış kitle doğal **50/50 sınıf dengesine** sahiptir.
* **Train (%80, stratify):** 5.600 müşteri (Churn: %49,86)
* **Test (%20, stratify):** 1.401 müşteri (Churn: %49,82)
* **Dengesizlik Parametresi:** `scale_pos_weight = n_neg / n_pos = 1,006` ($\approx 1,0$). Yapay ağırlıklandırmaya veya SMOTE'a gerek kalmadan dengeli eğitim sağlanmıştır.

## 3. Model Sonuçları (Test)

| Model | ROC-AUC | F1 | Precision | Recall |
| --- | --- | --- | --- | --- |
| Majority (her zaman churn) | 0,500 | 0,665 | 0,498 | 1,000 |
| Logistic Regression (baseline) | 0,799 | 0,766 | 0,789 | 0,745 |
| **LightGBM** | **0,929** | **0,859** | **0,887** | **0,832** |
| XGBoost | 0,928 | 0,860 | 0,879 | 0,842 |

ROC Eğrileri: `churn_roc_curves.png`

**Karar:** Final skorlayıcı **LightGBM** (ROC-AUC: **0,9294**). Ağaç modelleri birbirine çok yakındır ve baseline modelin belirgin biçimde üzerindedir. Model olgun kitlede hem yüksek hassasiyet (%88,7) hem yüksek yakalama (%83,2) üretmektedir.

## 4. K-Means ve CLTV’nin Etkisi

LightGBM öznitelik öneminde (split sayısı) öne çıkan değişkenler:

| Öznitelik | Importance |
| --- | --- |
| `recency_days` | 1.464 |
| `customer_age_t_days` | 1.280 |
| `cltv_6m` | 1.036 |
| `total_monetary` | 859 |
| `exp_purchases_6m` | 789 |
| `exp_average_profit` | 756 |
| `avg_monetary` | 731 |
| `ratio_clothing` | 619 |

Görsel: `churn_feature_importance.png`

**Bulgu:** CLTV metrikleri (`cltv_6m`, `exp_purchases_6m`, `exp_average_profit`) toplam 2.643 importance ile modelin en ağırlıklı öznitelik grubunu oluşturmaktadır.

## 5. Portföy Skorları

LightGBM tüm müşterilere `churn_proba` ve 0,50 eşiğinde `churn_pred` atamıştır.

| Metrik | Genel Portföy (13.020 Müşteri) | Olgunlaşmış Portföy (7.001 Müşteri) |
| --- | --- | --- |
| Ortalama Olasılık | **%66** (Gerçek %66,49 ile tam uyumlu) | **%50** (Gerçek %49,85 ile tam uyumlu) |
| Medyan Olasılık | %85 | %38 |
| Çeyreklikler (P25 / P75) | %30 / %93 | %8 / %96 |

Skorlar `customer_features.csv` içine yazılmıştır. Adım 7'deki aksiyon matrisi ve Streamlit dashboard bu skorları doğrudan kullanacaktır.