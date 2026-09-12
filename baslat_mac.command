#!/bin/bash
# =============================================================================
#  ReLoop — macOS BAŞLATICI   (ÇİFT TIKLA çalışır; komut yazmak YOK)
#  Ne yapar:  Python'u bulur → sanal ortam kurar → bağımlılıkları yükler →
#             backend'i başlatır → tarayıcıda arayüzü açar.
#  Tek adres: http://127.0.0.1:8000/app  (10 sekme de canlı gelir)
#  KAPATMAK için: bu pencerede  Ctrl+C  ya da pencereyi kapat.
#
#  İlk açılışta macOS "geliştirici doğrulanamadı" derse:
#     bu dosyaya SAĞ TIKLA → Aç → çıkan uyarıda tekrar "Aç".  (bir kez)
# =============================================================================

# --- Hata olursa pencere kapanmasın; kullanıcı mesajı okusun ---
bitir_hata() {
  echo ""
  echo "  ============================================================"
  echo "  ⚠  Bir sorun oluştu. Yukarıdaki mesaja bakın."
  echo "  Yardım gerekirse bu pencerenin ekran görüntüsünü paylaşın."
  echo "  ============================================================"
  echo ""
  read -n 1 -s -r -p "Kapatmak için bir tuşa basın..."
  echo ""
  exit 1
}

# Script nerede duruyorsa oraya geç (çift tıklamada da doğru klasör).
cd "$(dirname "$0")" || bitir_hata
PROJ="$(pwd)"
echo "ReLoop klasörü: $PROJ"

# İndirilen dosyalardaki 'karantina' bayrağını temizle (Görüntü Zekâsı modeli vb.)
xattr -dr com.apple.quarantine "$PROJ" >/dev/null 2>&1 || true

# --- Python 3.9+ bul (birçok konumda dener, en yenisini seçer) ---
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3.9 python3 \
            /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info>=(3,9) else 1)' >/dev/null 2>&1; then
      PY="$cand"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo ""
  echo "  HATA: Uygun bir Python 3 bulunamadı (3.9 veya üstü gerekli)."
  echo ""
  echo "  Kurulum (biri yeterli):"
  echo "    • https://www.python.org/downloads/  adresinden indir-kur, sonra bu dosyayı yeniden çift tıkla."
  echo "    • ya da Terminal'de:  brew install python"
  echo ""
  bitir_hata
fi
echo "Python: $("$PY" --version 2>&1)  ($PY)"

cd backend || bitir_hata

# --- Sanal ortam (ilk açılışta bir kez, ~1-2 dk) ---
if [ ! -d ".venv" ]; then
  echo ""
  echo ">> İlk kurulum: sanal ortam oluşturuluyor (bir kez)..."
  "$PY" -m venv .venv || { echo "  Sanal ortam kurulamadı."; bitir_hata; }
fi

VENV_PY=".venv/bin/python"
[ -x "$VENV_PY" ] || { echo "  Sanal ortam bozuk (.venv silip tekrar deneyin)."; bitir_hata; }

# --- Bağımlılıklar (kurulu değilse yükle) ---
if ! "$VENV_PY" -c "import fastapi, uvicorn, sqlalchemy, reportlab, qrcode, numpy" >/dev/null 2>&1; then
  echo ">> Bağımlılıklar yükleniyor (bir kez, ~1-2 dk)..."
  "$VENV_PY" -m pip install --upgrade pip >/dev/null 2>&1
  if ! "$VENV_PY" -m pip install -r requirements.txt; then
    echo ""
    echo "  Bağımlılıklar yüklenemedi (internet bağlantısını kontrol edin)."
    bitir_hata
  fi
fi

# --- Boş bir port bul (8000 doluysa 8001...) ---
PORT="$("$VENV_PY" - <<'PYEOF'
import socket
for p in (8000, 8001, 8002, 8003, 8010, 8080):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); print(p); break
    except OSError:
        pass
    finally:
        s.close()
else:
    print(8000)
PYEOF
)"
[ -z "$PORT" ] && PORT=8000
URL="http://127.0.0.1:${PORT}/app"

echo ""
echo ">> Backend başlatılıyor..."
echo ">> Arayüz:   ${URL}"
echo ">> API/Swagger:  http://127.0.0.1:${PORT}/docs"
echo ""

# uvicorn'u arka planda başlat
"$VENV_PY" -m uvicorn app.main:app --host 127.0.0.1 --port "${PORT}" &
SERVER_PID=$!

# Sunucu ölürse pencere de temiz kapansın
trap 'kill $SERVER_PID 2>/dev/null' EXIT

# /health 200 dönene kadar bekle (~30 sn), sonra tarayıcıyı aç
OPENED=0
for i in $(seq 1 60); do
  if curl -fs "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    open "${URL}" && OPENED=1
    break
  fi
  # sunucu erken öldüyse durma
  kill -0 $SERVER_PID 2>/dev/null || break
  sleep 0.5
done

echo ""
echo "======================================================================"
if [ "$OPENED" = "1" ]; then
  echo "  ✅ ReLoop çalışıyor — tarayıcıda açıldı."
else
  echo "  ✅ ReLoop çalışıyor. Tarayıcı otomatik açılmadıysa şu adresi elle açın:"
fi
echo ""
echo "        ${URL}"
echo ""
echo "  KAPATMAK için: bu pencerede Ctrl+C yapın ya da pencereyi kapatın."
echo "======================================================================"

# Sunucu süreci bitene kadar pencereyi açık tut
wait $SERVER_PID
