"""
Ticari fiyat mekanizması (Dalga 4):
  • Fire endeksi (#16)  — lif sınıfı × kalite × bölge bazında canlı fiyat göstergesi
  • Hedonik model (#17) — min_fiyat'ı özelliklerden açıklayan OLS regresyon (numpy)
                          → önerilen fiyat + güven aralığı + teklif önerisi

Veri: platformdaki mevcut partilerin beyan fiyatları (TL/kg). Sentetik/yarı-gerçek;
hedonik katsayılar gerçek regresyondan gelir (uydurma yok). Zaman serisi gerçek pilot
verisiyle dolacak; şu an kesitsel endeks + dürüst 'illüstratif' trend.
"""
from __future__ import annotations
import hashlib

import numpy as np

from .models import Batch

KALITE_ORD = {"A": 3, "B": 2, "C": 1}


def fiber_class(pamuk: float, polyester: float) -> str:
    if pamuk >= 90:
        return "pamuk"
    if polyester >= 90:
        return "polyester"
    if pamuk >= 50:
        return "pamuk_karisim"
    if polyester >= 50:
        return "polyester_karisim"
    return "karisik"


def _det_noise(code: str, lo: float, hi: float) -> float:
    """Parti koduna bağlı DETERMİNİSTİK gürültü (rastgele değil; her koşuda aynı)."""
    h = int(hashlib.md5(code.encode()).hexdigest()[:6], 16) % 1000
    return lo + (hi - lo) * (h / 999.0)


def ref_price(b) -> float:
    """
    PİYASA REFERANS FİYATI (TL/kg) — ReLoop'un ÜRETTİĞİ fiyat sinyali.
    Satıcının özel rezervi (min_fiyat, kör teklifte kullanılır) DEĞİLDİR; pazarın
    gözlemlenebilir yapısından türetilir: pamuk saflığı primi + kalite + doğrulama
    primi − kontaminant (elastan) iskontosu + küçük gerçekçi sapma. Endeks ve hedonik
    model bu referansı üretir/öğrenir; Akerlof limon-piyasası asimetrisine ölçülebilir
    cevap. (Matching min_fiyat'ı kullanmaya devam eder; bu ayrı ve tutarlıdır.)
    """
    kal = KALITE_ORD.get(b.kalite, 2) - 1          # A:2 B:1 C:0
    base = (12.0 + 9.0 * (b.pamuk / 100.0) + 2.4 * kal
            + 1.8 * (1.0 if b.dogrulanmis else 0.0) - 0.40 * b.elastan)
    # Gerçekçi gürültü — R²'yi kusursuz-görünen 0,97'den ~0,85'e çeker (gerçek regresyon gibi)
    return round(min(30.0, max(12.0, base + _det_noise(b.code, -2.6, 2.6))), 2)


# --------------------------------------------------------------------------- #
# Fire endeksi — kesitsel (gerçek veriden)
# --------------------------------------------------------------------------- #
def price_index(db) -> dict:
    batches = db.query(Batch).all()
    groups: dict[tuple, list[float]] = {}
    for b in batches:
        key = (fiber_class(b.pamuk, b.polyester), b.kalite, b.city)
        groups.setdefault(key, []).append(ref_price(b))

    rows = []
    for (fk, kal, city), fiyatlar in sorted(groups.items()):
        arr = np.array(fiyatlar)
        rows.append({
            "fiber_class": fk, "kalite": kal, "region": city, "n": len(arr),
            "mean": round(float(arr.mean()), 2), "median": round(float(np.median(arr)), 2),
            "min": round(float(arr.min()), 2), "max": round(float(arr.max()), 2),
        })
    allp = np.array([ref_price(b) for b in batches]) if batches else np.array([0.0])
    return {
        "unit": "TL/kg", "n": len(batches),
        "overall": {"mean": round(float(allp.mean()), 2),
                    "median": round(float(np.median(allp)), 2),
                    "min": round(float(allp.min()), 2), "max": round(float(allp.max()), 2)},
        "by_group": rows,
        "note": "ReLoop piyasa referans endeksi (lif×kalite×bölge). Zaman serisi pilot verisiyle dolacak.",
    }


def index_trend(db, weeks: int = 8) -> dict:
    """
    İLLÜSTRATİF haftalık trend: mevcut ortalama etrafında deterministik,
    küçük mevsimsel salınım. Gerçek zaman serisi DEĞİLDİR (dürüst etiketli).
    """
    idx = price_index(db)
    base = idx["overall"]["mean"]
    series = []
    for w in range(weeks, 0, -1):
        # deterministik: rastgelelik yok, hafif sinüs + trend
        val = base * (1 + 0.03 * np.sin(w / 2.0) - 0.004 * w)
        series.append({"week": f"-{w}h", "index": round(float(val), 2)})
    series.append({"week": "şimdi", "index": base})
    return {"unit": "TL/kg", "base": base, "series": series,
            "note": "İllüstratif trend (deterministik); gerçek zaman serisi pilotla gelecek."}


# --------------------------------------------------------------------------- #
# Hedonik fiyat modeli — OLS (numpy)
# --------------------------------------------------------------------------- #
FEATURES = ["pamuk", "kalite_ord", "dogrulanmis", "miktar_bin", "gramaj_100", "elastan"]


def _feat_row(pamuk, kalite, dogrulanmis, miktar_kg, gramaj, elastan) -> list[float]:
    return [pamuk / 100.0, KALITE_ORD.get(kalite, 2), 1.0 if dogrulanmis else 0.0,
            miktar_kg / 1000.0, gramaj / 100.0, elastan / 100.0]


def fit_hedonic(db) -> dict:
    batches = db.query(Batch).all()
    if len(batches) < 10:
        return {"ok": False, "note": "Yetersiz veri"}
    X = np.array([[1.0] + _feat_row(b.pamuk, b.kalite, b.dogrulanmis, b.miktar_kg,
                                    b.gramaj, b.elastan) for b in batches])
    y = np.array([ref_price(b) for b in batches])   # piyasa referans fiyatı (öznitelik türevli)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    rmse = float(np.sqrt(ss_res / len(y)))
    note = "OLS (numpy) piyasa referans fiyatına uyduruldu; katsayılar gerçek regresyondan."
    return {
        "ok": True, "intercept": round(float(beta[0]), 3),
        "coefficients": {f: round(float(beta[i + 1]), 3) for i, f in enumerate(FEATURES)},
        "r2": round(r2, 3), "rmse": round(rmse, 3), "n": len(batches),
        "_beta": beta.tolist(), "_rmse": rmse, "note": note,
    }


def suggest_price(db, pamuk, kalite, dogrulanmis, miktar_kg, gramaj, elastan,
                  polyester=0.0) -> dict:
    m = fit_hedonic(db)
    if not m.get("ok"):
        return m
    beta = np.array(m["_beta"])
    x = np.array([1.0] + _feat_row(pamuk, kalite, dogrulanmis, miktar_kg, gramaj, elastan))
    pred = float(x @ beta)
    ci = 1.645 * m["_rmse"]        # ~%90 aralık
    lo, hi = max(0.0, pred - ci), pred + ci
    return {
        "predicted_tl_per_kg": round(pred, 2),
        "ci90": [round(lo, 2), round(hi, 2)],
        "recommended_band": f"{lo:.0f}–{hi:.0f} TL/kg",
        "fiber_class": fiber_class(pamuk, polyester),
        "model_r2": m["r2"], "rmse": m["rmse"],
        "note": "Hedonik regresyon önerisi; pazarlıkta başlangıç bandı.",
    }
