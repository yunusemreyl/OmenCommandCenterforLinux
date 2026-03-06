# HP Laptop Manager v4.8 — Release Notes

## 🔴 Kritik Düzeltmeler

### 1. `tomllib` çökmesi düzeltildi
Python 3.10 ve altında `tomli` paketi bulunamazsa uygulama açılışta çöküyordu. Şimdi üçlü fallback: `tomllib` → `tomli` → JSON-only mod.

### 2. Fan RPM 0'da kalma riski giderildi
Custom fan modu reboot'tan sonra geri yüklendiğinde, RPM hedefleri kaydedilmediği için fanlar 0 RPM'de kalabiliyordu. Artık custom mod, boot sırasında güvenli şekilde `auto` moduna düşürülüyor.

### 3. `_find_hwmon_by_name` çökmesi düzeltildi
Fan sayfasında `/sys/class/hwmon` dizini yoksa (örn. konteyner ortamlarında) uygulama `FileNotFoundError` ile çöküyordu. Dizin varlık kontrolü eklendi.

### 4. TOML config yazımı güvenli hale getirildi
Manuel TOML yazımında özel karakterler dosyayı bozabiliyordu. Değerler artık sanitize ediliyor ve ek olarak JSON fallback dosyası da yazılıyor.

---

## 🟡 Orta Düzey Düzeltmeler

### 5. Thread-safe `save_state()`
Daemon'da `state` sözlüğü artık `copy.deepcopy()` ile kopyalandıktan sonra diske yazılıyor. Böylece eş zamanlı thread erişiminden kaynaklanan yarış koşulları önlendi.

### 6. MUX sayfası yeniden başlatma hata bildirimi
`systemctl reboot` başarısız olursa artık kullanıcıya hata mesajı gösteriliyor (eskiden sessizce başarısız oluyordu).

### 7. Sensör kategorisi çevirisi
"Diğer" kategorisi artık dil ayarına göre çevriliyor (İngilizce'de "Other").

### 8. Fan eğrisi eksen etiketleri çevirisi
"Sıcaklık (°C)" ve "Fan Hızı (%)" etiketleri artık `T()` çeviri fonksiyonu ile çevriliyor.

### 9. Güç profili tooltip çevirisi
Tasarruf, Dengeli ve Performans profil açıklamaları artık seçili dile göre gösteriliyor.

### 10. Dashboard sıcaklık birimi desteği
Dashboard sayfası artık kullanıcı tercihine göre °C veya °F gösteriyor (eskiden her zaman °C gösteriyordu).

### 11. Sürüm karşılaştırma pre-release desteği
`4.7-rc2` gibi etiketler artık doğru şekilde karşılaştırılıyor. Pre-release sürümler release sürümlerinden düşük olarak değerlendiriliyor.

---

## 🟢 Kozmetik Düzeltmeler

### 12. Bare `except` kalıpları temizlendi
`tools_page.py` dosyasındaki 6 adet `except: pass` → `except Exception: pass` olarak değiştirildi.

### 13. Tekrarlanan import temizlendi
`games_page.py` dosyasındaki gereksiz `import sys, os` satırı kaldırıldı.

### 14. Batarya sağlık yüzdesi formatı
`%85` → `85%` olarak düzeltildi (İngilizce uyumlu format).

---

## Değişen Dosyalar

| Dosya | Değişiklik |
|-------|-----------|
| `src/daemon/hp_manager_service.py` | #2, #5 — thread-safe save, custom fan fallback |
| `src/gui/main_window.py` | #1, #4 — tomllib fallback, safe TOML, versiyon 4.8 |
| `src/gui/i18n.py` | 6 yeni çeviri anahtarı |
| `src/gui/pages/fan_page.py` | #3, #7, #9 — hwmon guard, sensör i18n, tooltip i18n |
| `src/gui/pages/dashboard_page.py` | #10, #14 — temp unit, batarya % |
| `src/gui/pages/mux_page.py` | #6 — reboot hata bildirimi |
| `src/gui/pages/settings_page.py` | #11 — version compare, versiyon 4.8 |
| `src/gui/pages/tools_page.py` | #12 — bare except cleanup |
| `src/gui/pages/games_page.py` | #13 — duplicate import |
| `src/gui/widgets/fan_curve.py` | #8 — axis label i18n |
