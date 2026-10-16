# Changelog

## Unreleased

- **Sürücü**: casper-wmi fork'u 1.2.0'a yükseltildi; `install.sh` eski
  1.1.0 DKMS kaydını kaldırıp yenisini kuruyor (aynı sürüm numarasıyla DKMS
  eski modülü yerinde bırakırdı).
- **Özellik**: Köşe/kenar şerit LED'leri (bölge `0x07`) artık ayrı bir
  multicolor LED aygıtı: `casper::corner_backlight` (`brightness` 0/1 +
  `multi_intensity` R G B). `led_control` üzerinden yapılan bölge 7
  yazmaları da bu aygıtın durumuna yansıyor.
- **Özellik**: Aydınlatma sayfasında "Köşe LED'leri" kartı (hazır renkler,
  özel renk, hex, aç/kapa); klavye önizlemesi köşe rengini çerçeve olarak
  gösteriyor. CLI: `--set-led corner 00FF00`. Köşe durumu profillere ve
  açılışta geri yüklemeye dahil.
- **Düzeltme**: Köşe LED'leri kapalıyken EC ilk komutu yutuyor; sürücü
  (ve eski sürücüde uygulama) açarken komutu 150 ms arayla iki kez gönderiyor.
  EXCALIBUR G900'de doğrulandı.
- **Düzeltme**: `priv-write-helper` efekt nibble'ı taşıyan LED komutlarını
  reddediyordu (polkit yolunda efektler çalışmıyordu); bölge 7 de kabul ediliyor.
- **Düzeltme**: LED backend'de eksik `subprocess` importu (polkit yolunda
  `NameError`) ve son efektin hiç geri yüklenmemesi.

## 1.1.0 (2026-08-24)

- **Özellik**: Çift sürücü desteği — uygulama artık hem klasik `led_control`
  arayüzünü hem de multicolor LED sınıfını (`casper:rgb:kbd_zoned_backlight-*`)
  otomatik algılayıp kullanıyor. Hangi casper-wmi türevi sürücü kuruluysa çalışır.
- **Özellik**: Güç planı iki yoldan biri üzerinden: hwmon `pwm1` veya
  `/sys/firmware/acpi/platform_profile` (kernel API).
- **Özellik**: LED efektleri (Normal / Yanıp Sönme / Solma / Kalp Atışı /
  Tekrar / Rastgele / Ambilight) — multicolor arayüzde.
- **Düzeltme**: İzin hatalarında Polkit fallback (LED, efekt, güç planı) —
  grup üyeliği beklemadan çalışır.
- **Düzeltme**: Tek satır kurulum artık casper-keyboard-rgb kurulumlarına
  dokunmuyor (yan yana kurulum desteklenir).

## 1.0.1 (2026-08-23)
## 1.0.1 (2026-08-23)

- **Düzeltme**: Güç planı yazma izni — pwm1 root'a ait olduğundan GUI'de
  "permission hatası" veriyordu; Polkit + doğrulamalı `priv-write-helper`
  devreye girdi (helper artık LED ve güç planını tek noktadan yönetiyor).
- **Arayüz**: Klavye önizlemede kesik bölge çizgileri kaldırıldı; her bölge
  artık tuş kümesini saran yuvarlak bir çerçeveyle vurgulanıyor.
- **Özellik**: "Işıkları kapat" yanına akıllı "Işıkları aç" düğmesi eklendi
  (kapatınca renkler hatırlanır, açınca son parlaklıkla geri gelir).
- **Özellik**: Çok dilli arayüz — İngilizce (varsayılan) ve Türkçe.
  Kenar çubuğundaki dil seçici veya `--lang en|tr`; dil tercihi
  `~/.config/excalibur-center/settings.json` içinde saklanır.

## 1.0.0 (2026-08-23)

İlk sürüm — öncül açık kaynak [casper-wmi](https://github.com/Mustafa-eksi/casper-wmi)
sürücüsü ve klavye RGB kontrol uygulamaları temiz alınarak yeniden yazıldı.

### Sürücü (casper-wmi v1.1.0, upstream v1.0.0'a göre)

- **Düzeltme**: DMI listesinde olmayan modellerde (örn. EXCALIBUR G770)
  fan hızının okunması NULL pointer dereference ile okuyan süreci
  öldürüyordu. İşaretçi artık güvenli bir varsayılana işaret ediyor.
- **Özellik**: Güç planı artık sysfs üzerinden erişilebilir — upstream'de
  `HWMON_PWM_INPUT` tanımlanmadığı için read/write handler'ları ölü koddan
  ibaretti; artık `/sys/class/hwmon/hwmonX/pwm1` üzerinden plan okunup
  yazılabiliyor.
- G770 DMI tablosuna eklendi.

### Uygulama

- Windows Control Center'ından esinlenen sekmeli arayüz: Aydınlatma /
  Performans / Profiller
- Canlı klavye önizlemesi: tıklanabilir bölgeler, gerçek zamanlı renk yansıtma
- Güç planları ve canlı fan izleme (2 sn)
- Profil kaydet/uygula/sil + açılışta otomatik geri yükleme
- Tam CLI (`--status`, `--set-led`, `--set-plan`, `--restore`)
- Debian/Mint için tek komutluk kurulum betiği
