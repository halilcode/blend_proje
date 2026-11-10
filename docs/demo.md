# Demo Senaryosu

Canlı gösterim için adım adım akış (yaklaşık 6–8 dakika). Tüm demo hesaplarının parolası `demo12345`.

Ön koşul: öğrenci girişi (#27) ve grafik düzeltmesi (#28) `main`'e birleştirilmiş olmalı.

## Hazırlık (sunumdan önce)

GitHub Codespaces'te (Code → Codespaces → Create codespace on main) veya kendi bilgisayarınızda:

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py seed_demo
```

```bash
python manage.py runserver
```

Codespaces'te sağ altta çıkan **Open in Browser** ile siteyi açın. Geliştirme modunda Codespaces adresleri otomatik kabul edilir, ek ayar gerekmez.

Demo verisini sıfırlamak için (ör. prova sonrası değiştirilen notları geri almak): `db.sqlite3` dosyasını silip `migrate` ve `seed_demo` komutlarını tekrar çalıştırın.

## Demo verisi

| Kullanıcı | Rol | Ne görür |
|---|---|---|
| `elif`, `can`, `deniz`, `mert` | Öğrenci | Yalnızca kendi PO profili |
| `hoca` (Ahmet Hoca) | Öğretim üyesi | CSE 311 ve MAT 241 |
| `hoca2` (Ayşe Hoca) | Öğretim üyesi | CSE 321 |
| `bolum_baskani` | Bölüm başkanı | Bölümün tüm dersleri; PO ve katkı düzeylerini düzenler, not değiştiremez |
| `admin` | Sistem yöneticisi | Her şey |

3 ders: CSE 311 (proje dokümanındaki örnek), CSE 321, MAT 241. PO 8–11'e bilerek hiç ders bağlanmadı; "henüz puan yok" durumunu gösterir.

## Akış

### 1. Öğrenci bakışı (2 dk)

1. Ana sayfa → **Giriş yap** → `elif`.
2. PO profili grafiği: PO 1 = **85,0** ve PO 2 = **82,9**, proje dokümanındaki örnekle birebir aynı. PO 3–7 diğer derslerden geliyor.
3. Bir sütunun üzerine gelin: PO'nun adı ve puanı açılır. PO 8–11'de "Henüz puan yok" yazar, **0 değil**.
4. Aşağıdaki tablo aynı değerleri listeler.
5. *(İsteğe bağlı)* Çıkış → `deniz`: CSE 321 kısa sınavının notu henüz girilmedi. Puanlar yine hesaplanır, eksik not sıfır sayılıp ortalamayı düşürmez.

### 2. Öğretim üyesi bakışı (2–3 dk)

1. Çıkış → **Giriş yap** → `hoca` → **Yönetim paneline git**.
2. **Grades**: yalnızca CSE 311 ve MAT 241 notları görünür; CSE 321 (Ayşe Hoca'nın dersi) ne listede ne de filtre menüsünde var.
3. Elif'in **CSE 311 · Project** notunu açın, 80 → **100** yapıp kaydedin.
4. Yeni sekmede `elif` ile girin: PO 1 **85,0 → 95,0**, PO 2 **82,9 → 97,1** olur. Not girildiği anda PO puanı güncellenir.

### 3. Bölüm başkanı bakışı (1 dk)

1. `bolum_baskani` ile yönetim paneline girin.
2. **Course contributions**: her dersin PO'lara katkı düzeyi (1–5) burada düzenlenir.
3. **Grades**: bölümün üç dersinin notları görünür ama değiştirilemez (salt okunur).

### 4. Geliştirme süreci (CSE 311 için, 1–2 dk)

1. GitHub → **Issues** ve **Milestones**: story point etiketleri, Sprint 1 ve Sprint 2.
2. **Pull requests**: her iş ayrı branch'te, PR ve inceleme ile `main`'e giriyor.
3. **Actions**: her push ve PR'da testler ve migration kontrolü çalışıyor (README'deki CI rozeti).

## Sık sorulabilecek sorular

- **Puan nasıl hesaplanıyor?** Her katmanda ağırlıklı ortalama: `Σ(ağırlık × puan) ÷ Σ ağırlıklar` (`grading/scoring.py`).
- **Notu girilmemiş sınav ne oluyor?** Hesaba katılmıyor; sıfır sayılmıyor.
- **Farklı en yüksek puanlı sınavlar nasıl birleşiyor?** Notlar önce 0–100'e çevriliyor (CSE 321'deki 20 puanlık kısa sınav gibi).
- **Bir hoca başka hocanın notunu görebilir mi?** Hayır; listede, filtrede ve doğrudan bağlantıyla da açamaz (testlerle doğrulanıyor).
