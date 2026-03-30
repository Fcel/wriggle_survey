# Wriggle Survey — EXE Derleme Rehberi

## Ön Koşullar

```bash
pip install pyinstaller
pip install -r requirements.txt
```

## Derleme

Proje klasöründe:

```bash
pyinstaller WriggleSurvey.spec
```

Çıktı: `dist/WriggleSurvey/` klasörü içinde `WriggleSurvey.exe`

## Dağıtım

`dist/WriggleSurvey/` klasörünün tamamını zip'leyip paylaş.
Kullanıcı zip'i açıp `WriggleSurvey.exe`'ye çift tıklar.

## İlk Açılış

1. Lisans anahtarı dialog ekranı açılır
2. Kullanıcı kendine verilen `WRS-XXXXX-XXXXX-XXXXX` kodunu girer
3. Kod doğrulanırsa aktivasyon `%APPDATA%\WriggleSurvey\activation.dat` dosyasına kaydedilir
4. Sonraki açılışlarda dialog çıkmaz, doğrudan uygulama başlar
