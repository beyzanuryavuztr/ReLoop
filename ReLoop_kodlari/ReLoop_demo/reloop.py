"""
ReLoop — Çekirdek: tekstil fire ontolojisi + açıklanabilir eşleştirme motoru.

Ön Değerlendirme Raporu Bölüm 6'daki iki aşamalı formülün birebir uygulamasıdır:
  Aşama 1 — Sert filtre (kontaminant lif, min. miktar, kalite tabanı, mesafe yarıçapı,
            fiyat tavanı, doğrulama şartı)
  Aşama 2 — Ağırlıklı, KADEMELİ ve AÇIKLANABİLİR skor (0–1):
    MatchScore = 0.30*f_lif + 0.20*f_lojistik + 0.15*f_miktar
               + 0.15*f_fiyat + 0.10*f_kalite + 0.10*f_guven

Tasarım ilkesi: sert filtreyi geçen her aday için hiçbir bileşen "ölü sabit" değildir;
her bileşen adayı gerçekten ayırt eder (bkz. skor dağılımı — tek nokta değil, yayılım).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from math import radians, sin, cos, asin, sqrt

# ---------------------------------------------------------------------------
# ONTOLOJİ  (lif ailesi -> alt tip -> işlem -> kontaminasyon -> kalite)
# ---------------------------------------------------------------------------
KALITE_SIRA = {"A": 3, "B": 2, "C": 1}       # sert filtre karşılaştırması için
KALITE_SKOR = {"A": 1.00, "B": 0.80, "C": 0.60}  # kademeli kalite bileşeni

# Kumaş ailesi -> tipik gramaj aralığı (g/m²)  [DMP tutarsızlık kontrolü]
GRAMAJ_ARALIK = {
    "suprem":   (120, 260),
    "denim":    (300, 460),
    "polar":    (200, 360),
    "gabardin": (200, 320),
    "poplin":   (90, 160),
}
# Kumaş ailesi -> beklenen baskın lif  [lif-kumaş çelişkisi kontrolü]
BEKLENEN_LIF = {
    "polar": "polyester", "denim": "pamuk",
    "poplin": "pamuk", "suprem": "pamuk", "gabardin": "pamuk",
}

# Mekanik geri dönüşümü bozan kontaminant eşiği
ELASTAN_UST_ESIK = 2.0   # %  (bunun üstü mekanik geri dönüşümcü için elenir)
MIN_MIKTAR_KG = 100.0
MESAFE_YARICAP_KM = 200.0   # sert filtre + lojistik normalizasyonu (ulusal lojistik yarıçapı)

# --- MEVZUAT çıpaları (gerçek, atıf verilebilir) ---
# Devlet: Atık Yönetimi Yönetmeliği (EWC/atık kodu), Sıfır Atık Yönetmeliği,
# UÇBS/TABS beyanı (ucbs.cevre.gov.tr, 19.12.2025'ten beri EÇBS yerine).
ATIK_KODU_PRECONSUMER = "04 02 22"   # işlenmiş tekstil elyafı atıkları (tehlikesiz)
DEPO_YASAL_GUN = 180                  # örnek yasal depolama/beyan penceresi (illüstratif)
# Firma: gerçek uluslararası standartlar (kabul kriterleri bunlardan TÜRETİLİR).
STANDART_ACIKLAMA = {
    "GRS": "Global Recycled Standard — ≥%20 geri dönüşüm içeriği (B2B), menşe zinciri + kimyasal kısıt",
    "OEKO-TEX": "OEKO-TEX STANDARD 100 — zararlı madde limitleri",
    "ZDHC": "ZDHC MRSL — üretimde kısıtlı kimyasallar listesi",
    "RCS": "Recycled Claim Standard — geri dönüşüm içeriği doğrulaması",
}

# Eşleştirme ağırlıkları (alan bilgisinden türetilmiş başlangıç; veri ile öğrenilecek)
AGIRLIK = {
    "lif": 0.30, "lojistik": 0.20, "miktar": 0.15,
    "fiyat": 0.15, "kalite": 0.10, "guven": 0.10,
}

# Kullanıcıya okunur bileşen adları (rapor + arayüz ile ortak sözlük)
BILESEN_ETIKET = {
    "lif": "Lif uyumu", "lojistik": "Lojistik (mesafe)", "miktar": "Miktar karşılama",
    "fiyat": "Fiyat bandı", "kalite": "Kalite", "guven": "Güven / itibar",
}


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


@dataclass
class Parti:
    """Fire partisi (Dijital Malzeme Pasaportu özeti)."""
    id: str
    fabrika: str
    lat: float
    lon: float
    sehir: str
    pamuk: float          # %
    polyester: float      # %
    elastan: float        # %
    kumas: str
    gramaj: int           # g/m²
    en_m: float           # kumaş eni (m)
    miktar_kg: float
    kalite: str           # A/B/C
    min_fiyat: float      # TL/kg (yalnız sisteme görünür — blind teklif)
    depo_gun: int
    dogrulanmis: bool = False  # NIR/lab ile doğrulanmış parti mi
    itibar: float = 0.85       # satıcı fabrikanın geçmiş teslim başarı oranı (0–1)


@dataclass
class Talep:
    """Alıcı (geri dönüşümcü) talebi."""
    id: str
    alici: str
    lat: float
    lon: float
    sehir: str
    min_pamuk: float      # %  (en az bu kadar pamuk)
    max_elastan: float    # %  (mekanik geri dönüşüm için)
    ihtiyac_kg: float
    max_fiyat: float      # TL/kg
    min_kalite: str       # A/B/C
    dogrulanmis_ister: bool = False
    # --- Firma mevzuatı (alıcının kabul kriterleri; kamusal sertifikadan TÜRETİLMİŞ
    #     temsili değerlerdir — özel sözleşme iddiası DEĞİL) ---
    firma_adi: str = ""                 # gerçek/temsili firma adı ("" → alici kullanılır)
    firma_tur: str = ""                 # ürün/rol (ör. "GRS'li geri dönüşüm ipliği")
    sertifika_ister: list[str] = field(default_factory=list)  # ["GRS","OEKO-TEX","ZDHC"]
    izlenebilirlik_ister: bool = False  # menşe zinciri / doğrulama şartı
    min_lot_kg: float = 0.0             # firma minimum parti (kg)
    kaynak: str = ""                    # firma/standart dürüstlük etiketi


# ---------------------------------------------------------------------------
# YARDIMCI: mesafe + DMP tutarsızlık kontrolü
# ---------------------------------------------------------------------------
def haversine_km(a_lat, a_lon, b_lat, b_lon) -> float:
    dlat, dlon = radians(b_lat - a_lat), radians(b_lon - a_lon)
    h = sin(dlat/2)**2 + cos(radians(a_lat))*cos(radians(b_lat))*sin(dlon/2)**2
    return 2 * 6371.0 * asin(sqrt(h))


def tutarsizlik_uyarilari(p: Parti) -> list[str]:
    """DMP oluşturulurken çalışan otomatik tutarsızlık kontrolü (Bölüm 3)."""
    u = []
    lo_hi = GRAMAJ_ARALIK.get(p.kumas)
    if lo_hi and not (lo_hi[0] <= p.gramaj <= lo_hi[1]):
        u.append(f"Gramaj {p.gramaj} g/m², '{p.kumas}' için beklenen "
                 f"{lo_hi[0]}–{lo_hi[1]} g/m² dışında")
    beklenen = BEKLENEN_LIF.get(p.kumas)
    if beklenen == "polyester" and p.pamuk > 50:
        u.append(f"'{p.kumas}' tipik olarak polyesterdir ama beyan %{p.pamuk:.0f} pamuk")
    if beklenen == "pamuk" and p.polyester > 50:
        u.append(f"'{p.kumas}' tipik olarak pamuktur ama beyan %{p.polyester:.0f} polyester")
    if abs((p.pamuk + p.polyester + p.elastan) - 100) > 0.5:
        u.append("Lif oranları toplamı %100 değil")
    return u


# ---------------------------------------------------------------------------
# EŞLEŞTİRME — AŞAMA 1: sert filtre
# ---------------------------------------------------------------------------
def sert_filtre(p: Parti, t: Talep) -> tuple[bool, str]:
    if p.elastan > min(t.max_elastan, ELASTAN_UST_ESIK):
        return False, f"elastan %{p.elastan:.1f} eşiği aşıyor"
    if p.miktar_kg < MIN_MIKTAR_KG:
        return False, f"miktar {p.miktar_kg:.0f} kg < {MIN_MIKTAR_KG:.0f} kg"
    if KALITE_SIRA[p.kalite] < KALITE_SIRA[t.min_kalite]:
        return False, f"kalite {p.kalite} < istenen {t.min_kalite}"
    if p.pamuk < t.min_pamuk:
        return False, f"pamuk %{p.pamuk:.0f} < istenen %{t.min_pamuk:.0f}"
    if p.min_fiyat > t.max_fiyat:
        return False, f"taban fiyat {p.min_fiyat:.0f} > tavan {t.max_fiyat:.0f} TL/kg"
    d = haversine_km(p.lat, p.lon, t.lat, t.lon)
    if d > MESAFE_YARICAP_KM:
        return False, f"mesafe {d:.0f} km > {MESAFE_YARICAP_KM:.0f} km"
    if t.dogrulanmis_ister and not p.dogrulanmis:
        return False, "doğrulanmış parti isteniyor"
    return True, "geçti"


# ---------------------------------------------------------------------------
# EŞLEŞTİRME — AŞAMA 2: kademeli, açıklanabilir bileşenler
# ---------------------------------------------------------------------------
def guven_skoru(itibar: float, dogrulanmis: bool, tutarli: bool) -> float:
    """
    Güven bileşeni GÖZLENEBİLİR sinyallerden türetilir (rasgele DEĞİL):
      - fabrikanın geçmiş teslim başarı oranı (itibar)      -> ağırlık 0.55
      - NIR/lab ile doğrulanmış parti mi                    -> ağırlık 0.30
      - DMP tutarsızlık uyarısı yok mu                       -> ağırlık 0.15
    Doğrulanmış + tutarlı + yüksek itibarlı satıcı ~0.99'a, düşük itibarlı
    doğrulanmamış satıcı ~0.53'e yaklaşır: bileşen adayları gerçekten ayırır.
    """
    g = 0.55 * itibar + 0.30 * (1.0 if dogrulanmis else 0.0) \
        + 0.15 * (1.0 if tutarli else 0.0)
    return round(_clamp01(g), 4)


def _f_lif(p: Parti) -> float:
    """Pamuk saflığı eksi kontaminant cezası (polyester hafif, elastan ağır)."""
    return round(_clamp01(p.pamuk/100 - 0.30*p.polyester/100 - 1.5*p.elastan/100), 4)


def _f_lojistik(d_km: float) -> float:
    return round(_clamp01(1.0 - d_km / MESAFE_YARICAP_KM), 4)


def _f_miktar(p: Parti, t: Talep) -> float:
    return round(min(1.0, p.miktar_kg / t.ihtiyac_kg), 4)


def _f_fiyat(p: Parti, t: Talep) -> float:
    """Bütçe içinde kademeli: tavana eşit ~0.50; %30+ altında ~1.00."""
    if p.min_fiyat > t.max_fiyat:
        return 0.0
    marj = (t.max_fiyat - p.min_fiyat) / t.max_fiyat
    return round(_clamp01(0.5 + 0.5 * min(1.0, marj / 0.30)), 4)


def skorla(p: Parti, t: Talep) -> dict:
    """Açıklanabilir skor: her bileşen (0–1) + ağırlıklı katkı + gerekçe verisi."""
    d = haversine_km(p.lat, p.lon, t.lat, t.lon)
    tutarli = len(tutarsizlik_uyarilari(p)) == 0
    bilesen = {
        "lif":      _f_lif(p),
        "lojistik": _f_lojistik(d),
        "miktar":   _f_miktar(p, t),
        "fiyat":    _f_fiyat(p, t),
        "kalite":   KALITE_SKOR[p.kalite],
        "guven":    guven_skoru(p.itibar, p.dogrulanmis, tutarli),
    }
    return {"parti": p, "talep": t, "mesafe_km": d,
            "bilesen": bilesen, "tutarli": tutarli}


def match_score(bilesen: dict) -> float:
    """Ağırlıklı toplam (0–1). Bileşenler kademeli olduğu için sonuç yayılım gösterir."""
    return sum(AGIRLIK[k] * bilesen[k] for k in AGIRLIK)


def katki(bilesen: dict) -> dict:
    """Her bileşenin toplam skora ağırlıklı katkısı (açıklanabilirlik için)."""
    return {k: AGIRLIK[k] * bilesen[k] for k in AGIRLIK}


def aciklama(sonuc: dict, skor: float) -> str:
    p, t, d = sonuc["parti"], sonuc["talep"], sonuc["mesafe_km"]
    b = sonuc["bilesen"]
    kismi = "" if p.miktar_kg >= t.ihtiyac_kg else \
        f"; kısmi karşılama ({p.miktar_kg:.0f}/{t.ihtiyac_kg:.0f} kg)"
    lif = "yüksek" if b["lif"] >= 0.9 else ("orta" if b["lif"] >= 0.7 else "düşük")
    return (f"%{skor*100:.0f} — lif saflığı {lif} (%{b['lif']*100:.0f}), "
            f"{d:.0f} km, güven %{b['guven']*100:.0f}{kismi}")


# ---------------------------------------------------------------------------
# ÇİFT MEVZUAT UYGUNLUĞU (devlet + firma)  — eşleştirmeden BAĞIMSIZ ek mercek
# ---------------------------------------------------------------------------
def uygunluk(p: Parti, t: Talep) -> dict:
    """Bir fire partisinin bir alıcı firmaya çift-mevzuat uygunluğu.

      • YASAL katman (devlet): UÇBS/TABS beyan tutarlılığı + atık kodu. Sağlanmazsa
        işlem hukuken açılamaz → 'ENGELLİ'.
      • FIRMA katmanı (alıcının kamusal sertifikasından TÜRETİLMİŞ temsili kriter):
        elastan tavanı, pamuk/kalite tabanı, min lot, izlenebilirlik/GRS. Karşılanmazsa
        işlem mümkün ama firma reddedebilir → 'UYARI'.

    Verdict: 'UYGUN' (tüm katmanlar) / 'UYARI' (yasal ✓, firma ✗) / 'ENGELLİ' (yasal ✗).
    """
    tutarli = len(tutarsizlik_uyarilari(p)) == 0
    yasal = [
        {"kural": "UÇBS/TABS beyanı tutarlı", "ok": tutarli,
         "detay": (f"Atık kodu {ATIK_KODU_PRECONSUMER} beyanı geçerli" if tutarli
                   else "DMP tutarsız → UÇBS/TABS beyanı reddedilir")},
        {"kural": f"Atık kodu {ATIK_KODU_PRECONSUMER} — tehlikesiz, pre-consumer",
         "ok": True,
         "detay": "İşlenmiş tekstil elyafı atığı; mekanik geri kazanıma uygun"},
    ]
    firma = [
        {"kural": f"Elastan ≤ %{t.max_elastan:.0f} (firma tavanı)",
         "ok": p.elastan <= t.max_elastan, "detay": f"parti elastan %{p.elastan:.1f}"},
        {"kural": f"Pamuk ≥ %{t.min_pamuk:.0f}", "ok": p.pamuk >= t.min_pamuk,
         "detay": f"parti pamuk %{p.pamuk:.0f}"},
        {"kural": f"Kalite ≥ {t.min_kalite}",
         "ok": KALITE_SIRA[p.kalite] >= KALITE_SIRA[t.min_kalite],
         "detay": f"parti kalite {p.kalite}"},
    ]
    if t.min_lot_kg > 0:
        firma.append({"kural": f"Min lot ≥ {t.min_lot_kg:.0f} kg",
                      "ok": p.miktar_kg >= t.min_lot_kg,
                      "detay": f"parti {p.miktar_kg:.0f} kg"})
    if t.izlenebilirlik_ister or ("GRS" in t.sertifika_ister):
        std = "GRS zinciri" if "GRS" in t.sertifika_ister else "izlenebilirlik"
        firma.append({"kural": f"Doğrulanmış menşe ({std})", "ok": p.dogrulanmis,
                      "detay": ("NIR/lab doğrulanmış" if p.dogrulanmis
                                else "yalnız beyan — doğrulama yok")})
    yasal_ok = all(k["ok"] for k in yasal)
    firma_ok = all(k["ok"] for k in firma)
    verdict = "ENGELLİ" if not yasal_ok else ("UYGUN" if firma_ok else "UYARI")
    return {"verdict": verdict, "yasal": yasal, "firma": firma,
            "yasal_ok": yasal_ok, "firma_ok": firma_ok,
            "firma_adi": t.firma_adi or t.alici, "firma_tur": t.firma_tur,
            "sertifika": list(t.sertifika_ister), "kaynak": t.kaynak}
