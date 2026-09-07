# MIUUL DSML 21.DÖNEM PROJE

**1. SQL ile Veri Çekme & Analitik Tablonun Hazırlanması:**

Veri sızıntısını (Data Leakage) önlemek için tarih ayrımı şarttır.
• AdventureWorks veritabanındaki son tarihi referans alarak veriyi ikiye ayırın:
    ◦ **Gözlem Penceresi (Feature Extraction):** K-Means, CLTV (BG/NBD) ve Churn bağımsız değişkenlerinin hesaplanacağı geçmiş dönem.
    ◦ **Hedef Penceresi (Target Window):** Son 3 veya 6 aylık dönem (Churn etiketini doğrulamak için).
• `SalesOrderHeader`, `SalesOrderDetail`, `Customer`, `Person` ve `Product` tablolarını birleştirerek müşteri bazında analitik veri setini çıkarın:
    ◦ **RFM / Lifetimes Metrikleri:** Recency, Frequency (tekrar eden işlem sayısı), Monetary (ortalama/toplam sepet tutarı), T (müşteri yaşı).
    ◦ **Sepet & Davranış:** Ortalama sepet tutarı, toplam ürün adedi, indirim kullanım oranı, kategori bazlı harcama dağılımı.
    ◦ **Hedef Değişken (Target):** Hedef penceresinde sipariş vermeyenler için `Churn = 1`, verenler için `Churn = 0`

**2. Veri Ön İşleme (Preprocessing) & Keşifçi Veri Analizi (EDA):**
• Verideki uç değerleri (Outliers) IQR veya percentile yöntemleriyle tespit edip baskılayın (özellikle Monetary ve Frequency için).
• Sağa çarpık dağılan değişkenlere `Log Transform` uygulayın.
• K-Means algoritması için sayısal değişkenleri `StandardScaler` veya `RobustScaler` ile ölçeklendirin.

**3. K-Means ile Davranışsal Müşteri Segmentasyonu (Unsupervised):**
• Optimum küme sayısını ($k$) belirlemek için **Elbow Method** (Inertia) ve **Silhouette Score** analizini birlikte uygulayın.
• Seçilen k değeriyle K-Means modelini eğitin ve her müşteriye bir segment etiketi (`Cluster_0`, `Cluster_1` vb.) atayın.
• Kümeleri görselleştirmek için **PCA (Principal Component Analysis)** ile veriyi 2 boyuta indirgeyin.
• Segmentlerin RFM ve harcama profillerini çıkararak iş etiketleri tanımlayın (örn. *Sadık Yüksek Gelirliler*, *Fırsatçı Alıcılar*, *Uyuyan Müşteriler*).

**4. CLTV Tahmini (BG/NBD & Gamma-Gamma Modellemesi):**lifetimes kütüphanesi ile perakende sektör standardı yaklaşım.
• **BG/NBD Modeli:** Müşterilerin satın alma frekansı ve recency değerlerini kullanarak gelecek 3 ve 6 aydaki beklenen işlem sayısını (`conditional_expected_number_of_purchases_up_to_time`) tahmin edin.
• **Gamma-Gamma Modeli:** Müşterilerin işlem başına bırakacağı beklenen ortalama kâr/harcama değerini (`conditional_expected_average_profit`) hesaplayın.
• İki modeli birleştirerek müşterilerin **3-6 aylık tahmini CLTV değerlerini** üretin.
• Müşterileri CLTV skorlarına göre segmentlere (A, B, C, D) ayırın ve bu segmentleri 3. adımdaki **K-Means kümeleriyle çapraz karşılaştırın (Cross-tabulation Heatmap)**.

**5. Churn Tahmin Modellemesi (Supervised):**
• K-Means küme etiketlerini (`Cluster`) ve CLTV metriklerini modele yeni öznitelikler (features) olarak ekleyin.
• Veriyi Train/Test olarak ayırın; sınıf dengesizliği varsa `scale_pos_weight` veya `SMOTE` uygulayın.
• Baseline olarak `Logistic Regression`, ana modeller olarak `LightGBM` ve `XGBoost` eğitin.
• Modelleri **ROC-AUC**, **F1-Score**, **Precision** ve **Recall** metrikleriyle değerlendirin.
• **SHAP** analizi yaparak K-Means kümelerinin ve CLTV skorunun churn olasılığı üzerindeki etkisini görselleştirin. (Bonus, bunun için Python dilinde **SHAP kütüphanesinin nasıl kurulacağını ve kodlanacağını anlamamız gerekiyor. Ekstradan istersek yaparız.**)

**6. Segment Bazlı Ürün Tavsiye Sistemi (Recommendation / Apriori):**
• `SalesOrderDetail` tablosundaki fatura-ürün eşleşmelerini kullanarak **Apriori / FP-Growth** algoritmasıyla Birliktelik Kuralı Analizi (Market Basket Analysis) kurun.
• Tüm veri seti yerine **her K-Means segmenti için ayrı ayrı** kurallar çalıştırarak segmente özel ürün kombinasyonlarını (`Support`, `Confidence`, `Lift`) çıkarın.
• *Çıktı:* Churn riski yüksek ve yüksek CLTV değerine sahip bir müşteriyi elde tutmak için ona özel tamamlayıcı ürün önerileri üretin.

**7. İş Stratejisi Matrisi & Streamlit Dashboard:**

Analizin iş değerine ve çalışan bir prototipe dönüştürülmesi.
• **Aksiyon Matrisi:** Müşterileri (Churn Riski × CLTV Seviyesi × K-Means Segmenti) kırılımında gruplayıp pazarlama ekibi için somut aksiyon planları yazın (örn. acil indirim kuponu, VIP sadakat programı, çapraz satış kampanyası). Aksiyon matrisi noktasını daha detaylı konuşalım, sunumun en göz alıcı noktası burası olacak. (Örnek istediğim çıktı aşağı yukarı şu:https://docs.google.com/spreadsheets/d/1kumEkVuj7yl86-_dDEkiGYI20SO9n3yAsEyTTchDVys/edit?usp=sharing)
• **Streamlit Prototipi:** Müşteri ID girildiğinde K-Means kümesini, churn risk puanını, beklenen CLTV değerini ve önerilen ürün listesini tek ekranda gösteren basit bir kullanıcı arayüzü hazırlayın.