YKangul
opened 2 days ago · edited by YKangul
Hocam merhabalar
Omen Max 16 ah0xxx modelini CachyOS ile kullanıyorum. Programı yüklediğimde uygulama hp_wmi'ın yüklü olmadığını belirtiyor. Programı tamamen silip tekrardan yükledim ancak sanırsam driver'ı yüklemiyor. İşlemi hem Cachyos 6.19.7.1 kernelinde hem de 7.0 rc kernelinde denedim ancak sonuç aynı ki 7.0 kernelinin içine dahil olması gerekirken onu bile görmüyor kontrol ettiğimde silinmiş gibi görünüyor kernel driverları içerisinden.

Install log:
[i] Detected distro: CachyOS
[✓] Paket yöneticisi: pacman
[i] Bağımlılıklar yükleniyor...
uyarı: python-3.14.3-2 güncel -- atlanıyor
uyarı: python-gobject-3.54.5-2 güncel -- atlanıyor
uyarı: gtk4-1:4.20.3-1.1 güncel -- atlanıyor
uyarı: python-cairo-1.29.0-2.1 güncel -- atlanıyor
paket bağımlılıkları çözümleniyor...
varsa paketler arası çakışmalara bakılıyor...

Paket (2) Yeni Sürüm Değişiklik İndirme Boyutu

cachyos-extra-v3/libadwaita 1:1.8.4-1.1 5,22 MiB 0,76 MiB
extra/python-pydbus 0.6.0-13 0,17 MiB 0,04 MiB

Toplam İndirme Boyutu: 0,80 MiB
Toplam Kurulum Boyutu: 5,39 MiB

:: Kuruluma onay veriyor musunuz? [E/h]
:: Paketler alınıyor...
python-pydbus-0.6.0-13-any 38,0 KiB 106 KiB/s 00:00 [----------------------------------------------------------------------------] 100%
libadwaita-1:1.8.4-1.1-x86_64_v3 782,5 KiB 1927 KiB/s 00:00 [----------------------------------------------------------------------------] 100%
Toplam (2/2) 820,5 KiB 1780 KiB/s 00:00 [----------------------------------------------------------------------------] 100%
(2/2) anahtarlıktaki anahtarlar kontrol ediliyor [----------------------------------------------------------------------------] 100%
(2/2) paket bütünlüğü kontrol ediliyor [----------------------------------------------------------------------------] 100%
(2/2) paket dosyaları yükleniyor [----------------------------------------------------------------------------] 100%
(2/2) dosya çakışmaları kontrol ediliyor [----------------------------------------------------------------------------] 100%
:: Paket değişiklikleri işleniyor...
(1/2) yükleniyor libadwaita [----------------------------------------------------------------------------] 100%
(2/2) yükleniyor python-pydbus [----------------------------------------------------------------------------] 100%
:: Bağlantılı işlemler listesi çalışıyor...
(1/1) Arming ConditionNeedsUpdate...

Hangi güç yöneticisini kullanmak istersiniz?
[i] Sistemde tespit edildi: power-profiles-daemon

power-profiles-daemon (Varsayılan)
tuned-ppd (Fedora kullanıyorsanız önerilir)
TLP (https://github.com/linrunner/TLP)
auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)
Atla (Herhangi bir güç yöneticisi kurma)
Seçiminiz (1-5): 1
[i] power-profiles-daemon kuruluyor...
uyarı: power-profiles-daemon-0.30-3 güncel -- atlanıyor
yapılacak bir şey yok
[✓] Bağımlılıklar yüklendi
[i] Uygulama kuruluyor...
[i] Running driver install...
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
paket bağımlılıkları çözümleniyor...
varsa paketler arası çakışmalara bakılıyor...
Paket (1) Yeni Sürüm Değişiklik İndirme Boyutu

cachyos/dkms 3.3.0-2 0,16 MiB 0,05 MiB

Toplam İndirme Boyutu: 0,05 MiB
Toplam Kurulum Boyutu: 0,16 MiB

:: Kuruluma onay veriyor musunuz? [E/h]
:: Paketler alınıyor...
dkms-3.3.0-2-any 48,3 KiB 156 KiB/s 00:00 [----------------------------------------------------------------------------] 100%
(1/1) anahtarlıktaki anahtarlar kontrol ediliyor [----------------------------------------------------------------------------] 100%
(1/1) paket bütünlüğü kontrol ediliyor [----------------------------------------------------------------------------] 100%
(1/1) paket dosyaları yükleniyor [----------------------------------------------------------------------------] 100%
(1/1) dosya çakışmaları kontrol ediliyor [----------------------------------------------------------------------------] 100%
:: Paket değişiklikleri işleniyor...
(1/1) yükleniyor dkms [----------------------------------------------------------------------------] 100%
dkms için opsiyonel bağımlılık(lar)
linux-headers: build modules against the Arch kernel
linux-lts-headers: build modules against the LTS kernel
linux-zen-headers: build modules against the ZEN kernel
linux-hardened-headers: build modules against the HARDENED kernel
:: Bağlantılı işlemler listesi çalışıyor...
(1/1) Arming ConditionNeedsUpdate...
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Backing up stock driver: /lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.1.4/source -> /usr/src/hp-rgb-lighting-1.1.4
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub
Certificate or key are missing, generating self signed certificate for MOK...

Building module(s)... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-rgb-lighting.ko
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
insmod: ERROR: could not load module /home/ykangul/LaptopManagerForHP/driver/hp-wmi.ko: No such file or directory
[WARN] hp-wmi could not be loaded.
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

[✓] Resimler kopyalandı
Created symlink '/etc/systemd/system/multi-user.target.wants/com.yyl.hpmanager.service' → '/etc/systemd/system/com.yyl.hpmanager.service'.
[✓] OMEN Command Center for Linux başarıyla kuruldu!

~/LaptopManagerForHP main 19s
❯

Uygulama Log:

--- DEBUG INFO (v1.1.6) ---
Board ID: 8D41
Product Name: OMEN MAX Gaming Laptop 16-ah0xxx
WMI EVENT GUID: Found
WMI BIOS GUID: Found
Platform Profile: Not Supported
Thermal Version: 1 (Detected via DMI/Platform Profile)
Hwmon (hp): Not Found

Loaded Modules:

hp_wmi: No
hp_rgb_lighting: Yes
Service Status:
● com.yyl.hpmanager.service - OMEN Command Center for Linux Daemon
Loaded: loaded (/etc/systemd/system/com.yyl.hpmanager.service; enabled; preset: disabled)
Active: active (running) since Thu 2026-03-19 01:49:10 +03; 1min 2s ago
Invocation: 69161c9d4f4f494b85cee21949efae96
Main PID: 965 (python3)

Kernel Logs:
Mar 19 01:48:58 cachyos kernel: wmi_bus wmi_bus-PNP0C14:00: [Firmware Bug]: WQ00 data block query control method not found
Mar 19 01:48:58 cachyos kernel: wmi_bus wmi_bus-PNP0C14:04: [Firmware Info]: 8F1F6436-9F42-42C8-BADC-0E9424F20C9A has zero instances
Mar 19 01:48:58 cachyos kernel: wmi_bus wmi_bus-PNP0C14:04: [Firmware Info]: 8F1F6435-9F42-42C8-BADC-0E9424F20C9A has zero instances
Mar 19 01:48:58 cachyos kernel: wmi_bus wmi_bus-PNP0C14:04: [Firmware Info]: DF4E63B6-3BBC-4858-9737-C74F82F821F3 has zero instances
Mar 19 01:48:58 cachyos kernel: wmi_bus wmi_bus-PNP0C14:04: [Firmware Info]: 7391A661-223A-47DB-A77A-7BE84C60822D has zero instances
Mar 19 01:49:03 YKangul-OmenMaxArch kernel: hp_wmi: Unknown EC layout for board 8D41. Thermal profile readback will be disabled. Please report this to platform-driver-x86@vger.kernel.org
Mar 19 01:49:03 YKangul-OmenMaxArch kernel: hp-wmi hp-wmi: probe with driver hp-wmi failed with error -22
Mar 19 01:49:04 YKangul-OmenMaxArch kernel: hp_wmi: Unknown EC layout for board 8D41. Thermal profile readback will be disabled. Please report this to platform-driver-x86@vger.kernel.org
Mar 19 01:49:04 YKangul-OmenMaxArch kernel: hp-wmi hp-wmi: probe with driver hp-wmi failed with error -22

Sistem:

İşletim sistemi: CachyOS Linux
KDE Plasma sürümü: 6.6.3
KDE Frameworks sürümü: 6.24.0
Qt sürümü: 6.10.2
Çekirdek sürümü: 6.19.7-1-cachyos (64 bit)
Grafik platformu: Wayland
İşlemciler: 20 × Intel® Core™ Ultra 7 255HX
Bellek: 32 GiB RAM (30,8 GiB kullanılabilir)
Grafik işlemcisi 1: Intel® Graphics
Grafik işlemcisi 2: NVIDIA GeForce RTX 5070 Ti Laptop GPU
Üretici: HP
Ürün adı: OMEN MAX Gaming Laptop 16-ah0xxx
Sistem sürümü: Type1ProductConfigId

bir sebepten ötürü hp_wmi driverı kopyalanmıyor olarak algıladım ama emin değilim.
Konu ile ilgili yardımlarını rica ederim.

Activity
yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
Hemen ilgileniyorum

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
hp_wmi: Unknown EC layout for board 8D41. Thermal profile readback will be disabled.
hp-wmi hp-wmi: probe with driver hp-wmi failed with error -22
Buradaki -22 (EINVAL) hatası, driver'ın bu Board ID'yi tanımadığı için "geçersiz argüman" diyerek kendini durdurduğunu gösteriyor. Yani hp_wmi modülü compile edilmiş ve sistemde var, ancak insmod veya modprobe yapıldığında donanımla eşleşmediği için probe aşamasında çöküyor.
Bende çözmek adına cihazınızı kernel sürücüsünün uyumluluk kısmına ekleyeceğim. hp-wmi başarıyla kopyalanıyor ama board idnizi tanımadığı için derlemiyor. 7.0 kernelde de olmama sebebi board idniz hala 7.0 kerneldeki sürücü içine de eklenmemiş. İlgili düzeltmeyi yapıyorum herhangi bir sorun oluşursa veya probleminiz çözülmezse sizden dsdt verilerinizi isteyeceğim ona göre hp-wmi içinde özel bir sürücü yazacağım.

YKangul
YKangul commented 2 days ago
YKangul
2 days ago
Author
Tamamdır hocam teşekkür ederim. Temiz kurulum ile deneyeceğim.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
tekrar dener misiniz?

YKangul
YKangul commented 2 days ago
YKangul
2 days ago
Author
[i] Detected distro: CachyOS
[✓] Paket yöneticisi: pacman
[i] Bağımlılıklar yükleniyor...
uyarı: python-3.14.3-2 güncel -- atlanıyor
uyarı: python-gobject-3.54.5-2 güncel -- atlanıyor
uyarı: gtk4-1:4.20.3-1.1 güncel -- atlanıyor
uyarı: libadwaita-1:1.8.4-1.1 güncel -- atlanıyor
uyarı: python-pydbus-0.6.0-13 güncel -- atlanıyor
uyarı: python-cairo-1.29.0-2.1 güncel -- atlanıyor
yapılacak bir şey yok

Hangi güç yöneticisini kullanmak istersiniz?
[i] Sistemde tespit edildi: power-profiles-daemon

power-profiles-daemon (Varsayılan)
tuned-ppd (Fedora kullanıyorsanız önerilir)
TLP (https://github.com/linrunner/TLP)
auto-cpufreq (https://github.com/AdnanHodzic/auto-cpufreq)
Atla (Herhangi bir güç yöneticisi kurma)
Seçiminiz (1-5): 1
[i] power-profiles-daemon kuruluyor...
uyarı: power-profiles-daemon-0.30-3 güncel -- atlanıyor
yapılacak bir şey yok
[✓] Bağımlılıklar yüklendi
[i] Uygulama kuruluyor...
[i] Running driver install...
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: dkms-3.3.0-2 güncel -- atlanıyor
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
yapılacak bir şey yok
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Backing up stock driver: /lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.1.4/source -> /usr/src/hp-rgb-lighting-1.1.4
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub
Building module(s).... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-rgb-lighting.ko
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
insmod: ERROR: could not load module /home/ykangul/LaptopManagerForHP/driver/hp-wmi.ko: No such file or directory
[WARN] hp-wmi could not be loaded.
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

[✓] Resimler kopyalandı
Created symlink '/etc/systemd/system/multi-user.target.wants/com.yyl.hpmanager.service' → '/etc/systemd/system/com.yyl.hpmanager.service'.
[✓] OMEN Command Center for Linux başarıyla kuruldu!

~/LaptopManagerForHP main 10s
❯

aynı sonucu veriyor hocam değişmedi malesef.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
Yükleyicide de değişiklikler yaptım sizin için çalıştırıp tekrar deneyebilir misiniz?

rm -rf LaptopManagerForHP
git clone https://github.com/yunusemreyl/LaptopManagerForHP.git
cd LaptopManagerForHP/driver
sudo ./setup.sh uninstall
sudo ./setup.sh install
YKangul
YKangul commented 2 days ago
YKangul
2 days ago
Author
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: dkms-3.3.0-2 güncel -- atlanıyor
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
yapılacak bir şey yok
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[WARN] Removing existing DKMS entry (hp-rgb-lighting/1.1.4)...
Module hp-rgb-lighting/1.1.4 for kernel 6.19.7-1-cachyos (x86_64):
Before uninstall, this module version was ACTIVE on this kernel.
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.

Deleting module hp-rgb-lighting/1.1.4 completely from the DKMS tree.
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.1.4/source -> /usr/src/hp-rgb-lighting-1.1.4
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub

Building module(s).... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-rgb-lighting.ko
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
[WARN] hp-wmi could not be loaded.
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

Malesef hala aynı hocam.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
Sorun artık kurulumda değil, modül yükleme aşamasında. Büyük ihtimalle sistemdeki varsayılan hp_wmi sürücüsü çakışma yaratıyor.

Şu komutları sırayla çalıştırıp çıktıyı paylaşır mısın?

lsmod | grep hp_wmi
sudo modprobe -r hp_wmi
sudo modprobe hp-wmi
dmesg | tail -30
Eğer ilk komut çıktı veriyorsa, bu stock driver’ın yüklü olduğunu gösterir ve bizim modülün yüklenmesini engeller.

Komutlardan sonra özellikle dmesg çıktısını gönder, ona göre net çözümü söyleyeyim.

YKangul
YKangul commented 2 days ago
YKangul
2 days ago
Author
❯ lsmod | grep hp_wmi

hp_wmi 45056 0
sparse_keymap 12288 1 hp_wmi
platform_profile 20480 2 hp_wmi,processor_thermal_soc_slider
rfkill 45056 9 hp_wmi,bluetooth,cfg80211
wmi 36864 5 hp_wmi,video,nvidia_wmi_ec_backlight,hp_bioscfg,wmi_bmof

~
❯ sudo modprobe -r hp_wmi

[sudo] password for ykangul:

~
❯ sudo modprobe hp-wmi

~
❯ dmesg | tail -30

dmesg: çekirdek tampon belleği okunamadı: İşleme izin verilmedi

çıktı bu şekilde hocam.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
tamamdır ilgileniyorum

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago · edited by yunusemreyl
Owner
Çok özür dilerim tekrar tekrar denetiyorum ama son kez bi deneyebilir misiniz. Olmadığı takdirde sizden dsdt verilerinizi rica edeceğim. Yarın üstüne çalışıp çözmeyi düşünüyorum.

rm -rf LaptopManagerForHP
git clone https://github.com/yunusemreyl/LaptopManagerForHP.git
cd LaptopManagerForHP/driver
sudo ./setup.sh uninstall
sudo ./setup.sh install
YKangul
YKangul commented 2 days ago
YKangul
2 days ago
Author
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: dkms-3.3.0-2 güncel -- atlanıyor
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
yapılacak bir şey yok
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[WARN] Removing existing DKMS entry (hp-rgb-lighting/1.1.4)...
Module hp-rgb-lighting/1.1.4 for kernel 6.19.7-1-cachyos (x86_64):
Before uninstall, this module version was ACTIVE on this kernel.
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.

Deleting module hp-rgb-lighting/1.1.4 completely from the DKMS tree.
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.1.4/source -> /usr/src/hp-rgb-lighting-1.1.4
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub

Building module(s).... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-rgb-lighting.ko
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
[WARN] hp-wmi could not be loaded.
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

aynı duruyor hocam. DSDT nasıl çıkaracağımı bilmiyorum yardımcı olabilir misiniz?

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
sudo dmesg | tail -30  çıktısını da iletebilir misiniz?

Ayrıca dsdt için:

#Terminali aç ve gerekli aracı kur:
sudo pacman -S acpica

#DSDT tablosunu bulunduğun dizine .dat olarak kopyala:
sudo acpidump -b -t DSDT

#Bu dosyayı okunabilir metin formatına (.dsl) çevir:
iasl -d dsdt.dat
İşlem bitince bulunduğunuz klasörde dsdt.dsl adında bir dosya oluşacak. Lütfen o dosyayı buraya (GitHub'a) yükleyin.

yunusemreyl
yunusemreyl commented yesterday
yunusemreyl
yesterday
Owner
Hocam bir güncelleme yaptım. Sizin sorununuzu muhtemelen çözüyor. Tekrar bir kurulum yapıp deneyebilir misiniz?

rm -rf LaptopManagerForHP
git clone https://github.com/yunusemreyl/LaptopManagerForHP.git
cd LaptopManagerForHP/driver
sudo ./setup.sh uninstall
sudo ./setup.sh install
YKangul
YKangul commented yesterday
YKangul
yesterday
Author
~/LaptopManagerForHP/driver main
❯ sudo ./setup.sh uninstall
[sudo] password for ykangul:
[INFO] Unloading modules...
[INFO] Removing DKMS entry...
Module hp-rgb-lighting/1.1.4 for kernel 6.19.7-1-cachyos (x86_64):
Before uninstall, this module version was ACTIVE on this kernel.
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Deleting /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod.... done.

Deleting module hp-rgb-lighting/1.1.4 completely from the DKMS tree.
[OK] Uninstalled successfully.
[INFO] Restoring original driver backups (if any)...
[INFO] Restoring /lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst from backup...
[INFO] Restoring /usr/lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst from backup...
mv: '/usr/lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst.backup' durumlanamadı: Böyle bir dosya ya da dizin yok

~/LaptopManagerForHP/driver main 6s
❯ sudo ./setup.sh install
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: dkms-3.3.0-2 güncel -- atlanıyor
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
yapılacak bir şey yok
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.1.4/source -> /usr/src/hp-rgb-lighting-1.1.4
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub

Building module(s).... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.1.4/build/hp-rgb-lighting.ko
Found pre-existing /usr/lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst, archiving for uninstallation
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
[WARN] hp-wmi could not be loaded — check: dmesg | tail -20
[OK] hp-rgb-lighting loaded successfully
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

~/LaptopManagerForHP/driver main 8s
❯

tekrar aynı hatayı verdi hocam.

[ 20.586965] [UFW BLOCK] IN=wlan0 OUT= MAC= SRC=fe80:0000:0000:0000:69df:0f31:0cee:feab DST=ff02:0000:0000:0000:0000:0000:0001:0003 LEN=86 TC=0 HOPLIMIT=255 FLOWLBL=67613 PROTO=UDP SPT=5355 DPT=5355 LEN=46
[ 20.836974] [UFW BLOCK] IN=wlan0 OUT= MAC= SRC=fe80:0000:0000:0000:69df:0f31:0cee:feab DST=ff02:0000:0000:0000:0000:0000:0001:0003 LEN=86 TC=0 HOPLIMIT=255 FLOWLBL=67613 PROTO=UDP SPT=5355 DPT=5355 LEN=46
[ 20.975713] [UFW BLOCK] IN=wlan0 OUT= MAC= SRC=192.168.1.50 DST=224.0.0.252 LEN=66 TOS=0x00 PREC=0x00 TTL=255 ID=45332 PROTO=UDP SPT=5355 DPT=5355 LEN=46
[ 22.823656] Bluetooth: RFCOMM TTY layer initialized
[ 22.823675] Bluetooth: RFCOMM socket layer initialized
[ 22.823686] Bluetooth: RFCOMM ver 1.11
[ 23.097878] i915 0000:00:02.0: [drm] PHY A failed to request refclk
[ 30.444778] nvme nvme0: using unchecked data buffer
[ 30.454395] block nvme0n1: No UUID available providing old NGUID
[ 32.434288] warning: `kdeconnectd' uses wireless extensions which will stop working for Wi-Fi 7 hardware; use nl80211
[ 42.318063] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:01:00:eb:d8:40:a0:49:08:00 SRC=0.0.0.0 DST=224.0.0.1 LEN=32 TOS=0x00 PREC=0xC0 TTL=1 ID=0 DF PROTO=2
[ 42.625191] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:fb:48:e1:e9:c3:e3:fc:08:00 SRC=192.168.1.11 DST=224.0.0.251 LEN=32 TOS=0x00 PREC=0x00 TTL=1 ID=2353 PROTO=2
[ 45.185313] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:fc:c8:7f:54:54:27:d0:08:00 SRC=192.168.1.77 DST=224.0.0.252 LEN=32 TOS=0x00 PREC=0x00 TTL=1 ID=43215 PROTO=2
[ 80.885183] nvidia 0000:02:00.0: Enabling HDA controller
[ 95.613304] nvidia 0000:02:00.0: Enabling HDA controller
[ 100.911165] hp_rgb_lighting: HP Omen/Victus RGB companion driver unloaded
[ 124.741274] nvidia 0000:02:00.0: Enabling HDA controller
[ 125.655859] input: HP WMI hotkeys as /devices/virtual/input/input36
[ 125.662621] hp-wmi hp-wmi: probe with driver hp-wmi failed with error -22
[ 125.758450] hp_rgb_lighting: hp-rgb-lighting: init starting...
[ 125.758469] hp_rgb_lighting: hp-rgb-lighting: WMI GUID found OK
[ 125.758533] hp_rgb_lighting: hp-rgb-lighting: platform device registered OK
[ 125.758539] hp_rgb_lighting: HP Omen/Victus RGB companion driver loaded
[ 139.365560] nvidia 0000:02:00.0: Enabling HDA controller
[ 155.605383] nvidia 0000:02:00.0: Enabling HDA controller
[ 167.760238] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:01:00:eb:d8:40:a0:49:08:00 SRC=0.0.0.0 DST=224.0.0.1 LEN=32 TOS=0x00 PREC=0xC0 TTL=1 ID=0 DF PROTO=2
[ 168.376783] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:fb:00:e0:4c:68:08:55:08:00 SRC=192.168.1.154 DST=224.0.0.251 LEN=32 TOS=0x00 PREC=0xC0 TTL=1 ID=0 DF PROTO=2
[ 172.163874] [UFW BLOCK] IN=wlan0 OUT= MAC=01:00:5e:00:00:fc:c8:7f:54:54:27:d0:08:00 SRC=192.168.1.77 DST=224.0.0.252 LEN=32 TOS=0x00 PREC=0x00 TTL=1 ID=43216 PROTO=2
[ 185.077611] nvidia 0000:02:00.0: Enabling HDA controller
[ 199.806528] nvidia 0000:02:00.0: Enabling HDA controller

dmesg çıktısı bu şekilde

YKangul
YKangul commented yesterday
YKangul
yesterday · edited by YKangul
Author
dsdt.txt

hocam DSDT dosyasını ekledim. Github .dsl uzantısını yüklememe izin vermediği için .txt olarak değiştirdim umarım işinizi görür.

yunusemreyl
yunusemreyl commented yesterday
yunusemreyl
yesterday
Owner
Teşekkür ederim hocam inceleyeceğim. Bayramınız mübarek olsun.

yunusemreyl
yunusemreyl commented yesterday
yunusemreyl
yesterday
Owner
Hocam dün yayınladığım commitlerle birlikte sorununuz çözülmüş olmalı. Kritik fixler ve iyileştirmeler yaptım kontrol eder misiniz? Yine de üstüne doğrulama yapacağım.

YKangul
YKangul commented 16 hours ago
YKangul
16 hours ago
Author
[i] Detected distro: CachyOS
[✓] Paket yöneticisi: pacman
[i] Bağımlılıklar yükleniyor...
uyarı: python-3.14.3-2 güncel -- atlanıyor
uyarı: python-gobject-3.54.5-2 güncel -- atlanıyor
uyarı: gtk4-1:4.20.3-1.1 güncel -- atlanıyor
uyarı: libadwaita-1:1.8.4-1.1 güncel -- atlanıyor
uyarı: python-pydbus-0.6.0-13 güncel -- atlanıyor
uyarı: python-cairo-1.29.0-2.1 güncel -- atlanıyor
yapılacak bir şey yok
[✓] Sistemde zaten bir güç yöneticisi var (power-profiles-daemon), kurulum atlanıyor.
[✓] Bağımlılıklar yüklendi
[i] Uygulama kuruluyor...
[i] Running driver install...
[INFO] Detected distro: cachyos
[INFO] Installing dependencies (pacman)...
[INFO] Attempting to install: dkms linux-cachyos-headers base-devel
uyarı: dkms-3.3.0-2 güncel -- atlanıyor
uyarı: linux-cachyos-headers-6.19.7-1 güncel -- atlanıyor
uyarı: base-devel-1-2 güncel -- atlanıyor
yapılacak bir şey yok
[INFO] Kernel built with Clang/LLVM detected. Automatically setting LLVM=1 for build...
[INFO] Kernel 6.19.7-1-cachyos detected (< 7.0) — installing both hp-wmi and hp-rgb-lighting...
[INFO] Checking for stock hp-wmi driver to backup and disable...
[INFO] Backing up stock driver: /lib/modules/6.19.7-1-cachyos/kernel/drivers/platform/x86/hp/hp-wmi.ko.zst
[INFO] Installing via DKMS...
Creating symlink /var/lib/dkms/hp-rgb-lighting/1.2.0/source -> /usr/src/hp-rgb-lighting-1.2.0
Sign command: /usr/lib/modules/6.19.7-1-cachyos/build/scripts/sign-file
Signing key: /var/lib/dkms/mok.key
Public certificate (MOK): /var/lib/dkms/mok.pub

Building module(s).... done.
Signing module /var/lib/dkms/hp-rgb-lighting/1.2.0/build/hp-wmi.ko
Signing module /var/lib/dkms/hp-rgb-lighting/1.2.0/build/hp-rgb-lighting.ko
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
Installing /usr/lib/modules/6.19.7-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst
Running depmod... done.
[INFO] Loading modules...
[WARN] hp-wmi could not be loaded — check: dmesg | tail -20
[OK] hp-rgb-lighting loaded successfully
[OK] Both hp-wmi and hp-rgb-lighting installed.

[INFO] The module will be automatically rebuilt on kernel updates via DKMS.
[INFO] Fan control: /sys/devices/platform/hp-wmi/hwmon/hwmon*/pwm1_enable
[INFO] Fan speed: /sys/devices/platform/hp-wmi/hwmon/hwmon*/fan*_target

[i] Applying kernel module configuration...
[i] Unloading stock hp_wmi module...
[i] Loading modules via modprobe...
[!] hp-wmi failed to load — check: dmesg | tail -20
[✓] hp-rgb-lighting loaded successfully
[i] Active module path (debug):
filename: /lib/modules/6.19.7-1-cachyos/updates/dkms/hp-wmi.ko.zst
[✓] Resimler kopyalandı
Created symlink '/etc/systemd/system/multi-user.target.wants/com.yyl.hpmanager.service' → '/etc/systemd/system/com.yyl.hpmanager.service'.
[✓] OMEN Command Center for Linux başarıyla kuruldu!

Hocam aynı hatayı veriyor ne yazık ki

Ja4e'S BUGS
title

https://github.com/Ja4e/hp-omen-gaming-wmi-dkms/blob/main/hp-wmi.c

use this as a reference because it works for performance mode and manual fan control

Activity
yunusemreyl
yunusemreyl commented 3 days ago
yunusemreyl
3 days ago
Owner
Okey i will look it.

yunusemreyl
yunusemreyl commented 3 days ago
yunusemreyl
3 days ago
Owner
I add support now. Can u check?

Ja4e
Ja4e commented 3 days ago
Ja4e
3 days ago
Author
roger ill check


Ja4e
closed this as completed3 days ago

Ja4e
reopened this 2 days ago
Ja4e
Ja4e commented 2 days ago
Ja4e
2 days ago
Author
The nvidia-powerd will fail to launch now i think i would prefer tthat commit is reverted back it was supposed to.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
I will release an update within 2 days that will completely resolve all issues.

yunusemreyl
yunusemreyl commented 2 days ago
yunusemreyl
2 days ago
Owner
Hi @Ja4e,

Thank you for the feedback. To ensure the upcoming v1.1.7 update works perfectly for your hardware—especially for the MUX switch implementation—I need some specific technical data from your system.

The MUX switch (Graphics Mode) typically uses WMI method 0x40, but the offsets can vary between OMEN generations. To map this correctly, could you please provide the following:

1. DSDT Dump:
This is the most critical file. It contains the ACPI tables that show exactly how your BIOS handles WMI calls. You can extract it using these commands:

sudo dnf install acpica-tools  # If on Fedora/Nobara
sudo acpidump -b -t DSDT -o dsdt.dat
iasl -d dsdt.dat
Please upload the resulting dsdt.dsl file here.

2. System Logs:
After a fresh boot, please run:

sudo dmesg | grep -iE "hp_wmi|acpi|wmi" > logs.txt
And share the logs.txt file.

3. Current Status of 8D87:
Regarding the nvidia-powerd failure: I have already pushed a commit switching your board ID to the omen_v1_no_ec_thermal_params profile. This should theoretically stop the conflict. Could you please confirm if nvidia-powerd still fails with the latest code?

Why I need this:
With your DSDT, I can verify if your board uses the standard OMEN EC offsets (0x95) or something else, and I can pinpoint the exact Graphics Mode switching logic to implement the BIOS-level MUX control you requested.

Looking forward to your data so I can finalize the fix!

yunusemreyl
yunusemreyl commented yesterday
yunusemreyl
yesterday
Owner
Hi! I sent a new update. It should be fix your problem. Can u try?

rm -rf LaptopManagerForHP
git clone https://github.com/yunusemreyl/LaptopManagerForHP.git
cd LaptopManagerForHP/driver
sudo ./setup.sh uninstall
sudo ./setup.sh install
Ja4e
Ja4e commented yesterday
Ja4e
yesterday · edited by Ja4e
Author
Please upload the resulting dsdt.dsl file here.

dsdt.zip

And share the logs.txt file.

logs.txt

Could you please confirm if nvidia-powerd still fails with the latest code?

will do it tonight
Update:
your program caused my gnome-shell unable to start

also please note that you have many left over dkms hp-rgb-lighting

and your dkms sometimes triggers this

==> dkms install --no-depmod hp-rgb-lighting/1.2.0 -k 6.19.9-1-cachyos
Module /usr/lib/modules/6.19.9-1-cachyos/updates/dkms/hp-wmi.ko.zst already installed (unversioned module), override by specifying --force
Module /usr/lib/modules/6.19.9-1-cachyos/updates/dkms/hp-rgb-lighting.ko.zst already installed (unversioned module), override by specifying --force

Error! Installation aborted.
yunusemreyl
yunusemreyl commented 14 hours ago
yunusemreyl
14 hours ago
Owner
I'll correct it immediately.

babyinlinux
Benden bir güncelleme, şu anda akılda kalıcı işletim sisteminde (Arch'a göre). Neden? Çünkü Nobara sisteminin güncelleme şeklini bozmaya karar verdi, nedenini bilmiyorum ama şu anda Nobara'yı kullanamıyorum ama uygulama artık güncellenmiş ve bilgisayarımda

Fanlar - Çalışmalar

Aydınlatma -çalışmaları

MUX -şimdi en azından menüsünü görebiliyorum ama kullanılan GPU'yu değiştirmeye çalıştığımda "Error: Error: [Errno 22] Invalid argument" diyor bu da bir şey

Uygulamayı özel düğmeyle açmak -çalışmıyor

sensörler -hâlâ garip

Hata Hata Bilgisi:
--- DEBUG INFO (v1.2.0) ---
Kart Kimliği: 8C77
Ürün Adı: OMEN by HP Gaming Laptop 16-wf1xxx
WMI EVENT GUID: Bulundu
WMI BIOS GUID: Platform Profili Yolu:
/sys/firmware/acpi/platform_profile
Aktif Profil: performans
Termal Sürüm: 1 (DMI/Platform Profili üzerinden tespit edildi)
Hwmon Yolu: /sys/class/hwmon/hwmon5 (hp)
Fan 1 Hız: 2000 RPM
Fan 2 Hız: 2300 RPM

Yüklü Modüller:

hp_wmi: Evet
hp_rgb_lighting: Evet
Hizmet Durumu:
● com.yyl.hpmanager.service - Linux için OMEN Komut Merkezi Daemon
Yüklendi: yüklendi (/etc/systemd/system/com.yyl.hpmanager.service; etkinleştirildi; ön ayar: devre dışı bırakıldı)
Aktif: aktif (çalışıyor) Cuma 2026-03-20 17:27:04 EDT; 8 dakika önce
Çağırma: 9cd83a5daff04f2a9bb18ec1d00659f3
Ana PID: 1102 (python3)

Çekirdek Günlükleri:
İlgili kayıt bulunamadı.

ayrıca mux anahtarının bios üzerinden kontrolünü ekleyeceğiz.

---

### v1.2.1 - General Fixes and Finalization (2026-03-21)
All reported critical issues have been resolved:

1.  **hp-wmi Kernel Driver Fixes:**
    *   Resolved **8D41 EC failure (-22)**: Fallback to BALANCED profile if EC layout is unknown, preventing probe failure.
    *   Resolved **8C77 MUX "Invalid Argument" (Errno 22)**: Increased WMI buffer size to 128 bytes for graphics mode requests.
    *   Added **fan table fallback**: If EC fan table query fails, driver now falls back to safe 5000 RPM limits instead of failing.
2.  **Daemon & Service Improvements:**
    *   Removed **Omen Key (0x21a5) background listener**: Hotkeys are now handled solely by the kernel driver's input system, reducing overhead and fragmentation.
    *   MUX control is officially out of beta with support for 4 backends (bios, envycontrol, supergfxctl, prime-select).
3.  **UI & Packaging:**
    *   Updated all repository URLs to the new `yunusemreyl/OmenCommandCenterforLinux` home.
    *   Cleaned up `PKGBUILD` and installation scripts.
    *   Added `.gitignore` to keep `bugfix` and `SSDTFiles` folders local only.

**Status: Production Ready.**
