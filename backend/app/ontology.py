"""
Çapraz sektör downcycling ontolojisi — KASKADIN temeli (#7).

Farklılaşma notu: Bu bir "genel çok-sektör platformu" DEĞİLDİR. Tekstil firesi
en yüksek değerli tekstil-tekstile rotada eşleşemezse, **hiçbir fire çöpe gitmesin**
ilkesiyle SINIRLI ve TANIMLI birkaç tekstil-komşusu downcycling rotasına düşürülür
(ticari bütünlük). Rotalar değer sırasına göre denenir; en son çare RDF/enerjidir.

Değerler TL/kg pazar-tahminidir (dürüst etiketli). CO₂ tasarrufu illüstratiftir:
malzeme geri kazanımı (tekstil) en yüksek, downcycling daha düşük, RDF esas olarak
fosil yakıt yerine enerji geri kazanımı sağlar.
"""
from __future__ import annotations

# Tekstil-tekstile eşleşme eşiği (bunun altında kaskad devreye girer)
TEXTILE_ESIK = 0.60

# Tier 2 downcycling rotaları (değer azalan sırada denenir).
# kabul(b): bir partinin (Batch benzeri) bu rotaya uygunluğunu döndürür.
DOWNCYCLE_ROUTES = [
    {
        "key": "wiping_cloth", "tier": 2,
        "label": "Endüstriyel silme bezi",
        "sector": "Temizlik / bakım",
        "value_tl_per_kg": 10.0, "co2_saving_kg_per_kg": 0.9,
        "kabul": lambda b: b.pamuk >= 60 and b.elastan <= 3,
        "note": "Pamuk ağırlıklı, düşük kontaminasyon; hadde/makine silme bezi.",
    },
    {
        "key": "automotive_felt", "tier": 2,
        "label": "Otomotiv keçe / ses yalıtımı",
        "sector": "Otomotiv",
        "value_tl_per_kg": 8.0, "co2_saving_kg_per_kg": 0.8,
        "kabul": lambda b: (b.polyester >= 30 or b.pamuk >= 40),
        "note": "Karışık/PES ağırlıklı elyaf; iğnelenmiş keçe, panel dolgusu.",
    },
    {
        "key": "insulation_felt", "tier": 2,
        "label": "Yalıtım keçesi (inşaat)",
        "sector": "İnşaat",
        "value_tl_per_kg": 6.5, "co2_saving_kg_per_kg": 0.7,
        "kabul": lambda b: True,  # karışık/kontamine lifi tolere eder
        "note": "Isı/ses yalıtım keçesi; karışık ve kontamine lifi kabul eder.",
    },
    {
        "key": "furniture_padding", "tier": 2,
        "label": "Mobilya / şilte dolgusu",
        "sector": "Mobilya",
        "value_tl_per_kg": 5.0, "co2_saving_kg_per_kg": 0.6,
        "kabul": lambda b: True,
        "note": "Dolgu elyafı; geniş kabul.",
    },
]

# Tier 3 — son çare (her zaman kabul).
RDF_ROUTE = {
    "key": "rdf", "tier": 3, "label": "RDF / enerji geri kazanımı",
    "sector": "Çimento / enerji", "value_tl_per_kg": 1.5,
    "co2_saving_kg_per_kg": 0.3,
    "note": "Malzeme geri kazanımı uygun değilse; katı atık yerine fosil yakıt ikamesi.",
}


def cascade_route(b, best_textile_score: float | None) -> dict:
    """
    Bir parti için kaskad yerleşimini döndürür.
      Tier 1: tekstil-tekstile (skor >= eşik)
      Tier 2: değer sırasına göre ilk uygun downcycling rotası
      Tier 3: RDF (son çare) — böylece HİÇBİR fire yerleşimsiz kalmaz.
    """
    if best_textile_score is not None and best_textile_score >= TEXTILE_ESIK:
        return {"tier": 1, "channel": "textile", "key": "textile",
                "label": "Tekstilden tekstile (elyaf geri kazanımı)",
                "sector": "Tekstil", "value_tl_per_kg": None,
                "co2_saving_kg_per_kg": 1.60,
                "matched_score": round(best_textile_score, 4),
                "note": "En yüksek değerli rota: açık döngü mekanik elyaf geri kazanımı."}
    for r in DOWNCYCLE_ROUTES:
        if r["kabul"](b):
            return {**{k: v for k, v in r.items() if k != "kabul"}, "channel": "downcycle"}
    return {**RDF_ROUTE, "channel": "rdf"}


def all_routes() -> list[dict]:
    """Şeffaflık: tüm rotaların kuralları (kabul lambda'sı hariç)."""
    tier1 = {"tier": 1, "channel": "textile", "key": "textile",
             "label": "Tekstilden tekstile (elyaf geri kazanımı)", "sector": "Tekstil",
             "co2_saving_kg_per_kg": 1.60, "esik": TEXTILE_ESIK}
    routes = [tier1]
    for r in DOWNCYCLE_ROUTES:
        routes.append({k: v for k, v in r.items() if k != "kabul"})
    routes.append(RDF_ROUTE)
    return routes
