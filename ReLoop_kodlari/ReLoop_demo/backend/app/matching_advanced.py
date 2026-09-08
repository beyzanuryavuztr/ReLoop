"""
İleri eşleştirme zekâsı (Dalga 3):
  • cascade         — tekstil → sınırlı downcycling → RDF (hiçbir fire yerleşimsiz kalmaz)
  • lot_merge       — küçük uyumlu lotları birleştirip tek talebi karşıla
  • pareto          — karbon/maliyet/mesafe/değer çok-amaçlı, ağırlıkla anlık sıralama + Pareto cephesi
  • forecast        — üretim planından fire tahmini + önceden alıcı bildirimi
  • rejections      — "neden eşleşmedi" (sert filtre gerekçeleri)
  • propose_weights — kabul edilen işlemlerden ağırlık öğrenme (LTR kancası; canlı ağırlığı DEĞİŞTİRMEZ)
"""
from __future__ import annotations

from . import engine_service as ES
from . import ontology
from . import pricing as P
from ._enginepath import ensure_engine_on_path
from .impact_calc import COEFF, ESLESME_ESIGI

ensure_engine_on_path()
import reloop as R  # noqa: E402


# --------------------------------------------------------------------------- #
# 1) KASKAD — hiçbir fire yerleşimsiz kalmaz
# --------------------------------------------------------------------------- #
def cascade_for_batch(b, demands) -> dict:
    best = ES.best_match_for_batch(b, demands)
    route = ontology.cascade_route(b, best["score"] if best else None)
    return {
        "batch_code": b.code,
        "textile_best": ({"demand_code": best["demand_code"], "score": best["score"]}
                         if best else None),
        "cascade": route,
    }


def cascade_summary(batches, demands) -> dict:
    """Dashboard için: kaç parti hangi kanalda yerleşti (yerleşim %100)."""
    ch = {"textile": 0, "downcycle": 0, "rdf": 0}
    routes: dict[str, int] = {}
    for b in batches:
        r = cascade_for_batch(b, demands)["cascade"]
        ch[r["channel"]] = ch.get(r["channel"], 0) + 1
        routes[r["key"]] = routes.get(r["key"], 0) + 1
    n = len(batches) or 1
    return {"total": len(batches), "channels": ch, "routes": routes,
            "placement_rate_pct": 100.0,   # kaskad sayesinde her fire bir rotaya düşer
            "textile_rate_pct": round(ch["textile"] / n * 100, 1),
            "note": ("Yerleşim %100 = her fire bir geri kazanım/enerji rotasına ATANDI (çöpe ~0); "
                     "hepsi tekstil-tekstile DEĞİL. RDF/enerji son çaredir (malzeme değil enerji geri "
                     "kazanımı). CO₂ katkısı rota-ağırlıklı hesaplanır.")}


# --------------------------------------------------------------------------- #
# 2) LOT BİRLEŞTİRME — küçük lotlar tek partiye
# --------------------------------------------------------------------------- #
def lot_merge_for_demand(d, batches, radius_km: float = 60.0) -> dict:
    """
    Talebi tek başına karşılayamayan küçük uyumlu partileri (sert filtreyi geçen,
    talebe yakın) skora göre birleştirip ihtiyacı karşılayan tek 'sanal lot' önerir.
    """
    adaylar = []
    for b in batches:
        r = ES.score_pair(b, d)
        if not r["ok"] or b.miktar_kg >= d.ihtiyac_kg:
            continue  # yalnız kısmi (küçük) lotlar birleştirilir
        if r["distance_km"] > radius_km:
            continue
        adaylar.append((r["score"], b, r))
    adaylar.sort(key=lambda x: x[0], reverse=True)

    bundle, toplam, agirlikli = [], 0.0, 0.0
    for score, b, r in adaylar:
        if toplam >= d.ihtiyac_kg:
            break
        pay = min(b.miktar_kg, d.ihtiyac_kg - toplam)
        bundle.append({"batch_code": b.code, "city": b.city, "kg": b.miktar_kg,
                       "used_kg": round(pay, 1), "score": score,
                       "kalite": b.kalite, "pamuk": b.pamuk})
        toplam += b.miktar_kg
        agirlikli += score * pay
    kullanilan = min(toplam, d.ihtiyac_kg)
    return {
        "demand_code": d.code, "need_kg": d.ihtiyac_kg,
        "bundle": bundle, "lots": len(bundle),
        "total_kg": round(toplam, 1),
        "covers": toplam >= d.ihtiyac_kg,
        "blended_score": round(agirlikli / kullanilan, 4) if kullanilan else 0.0,
        "note": "Çok sayıda küçük pre-consumer fire partisi tek tedarik lotunda birleştirildi.",
    }


# --------------------------------------------------------------------------- #
# 3) PARETO — çok amaçlı (karbon/maliyet/mesafe/değer)
# --------------------------------------------------------------------------- #
def _norm(vals):
    lo, hi = min(vals), max(vals)
    if hi - lo < 1e-9:
        return [1.0 for _ in vals]
    return [(v - lo) / (hi - lo) for v in vals]


def pareto_for_demand(d, batches, w_carbon=0.25, w_cost=0.25, w_distance=0.25,
                      w_value=0.25, top=15) -> dict:
    cand = []
    for b in batches:
        r = ES.score_pair(b, d)
        if not r["ok"]:
            continue
        carbon = min(b.miktar_kg, d.ihtiyac_kg) * COEFF["co2_conservative_kg_per_kg"]
        value = r["components"]["lif"] * r["components"]["kalite"]
        # Maliyet ekseni PİYASA REFERANS fiyatını kullanır (ref_price) — satıcının gizli
        # rezervini (min_fiyat, kör teklifte kullanılır) DIŞA VERMEZ. Rezervi sızdırmak
        # kör-teklif mekanizmasını (aracı-atlama moat'ının temeli) çökertirdi.
        cand.append({"batch_code": b.code, "carbon": carbon, "cost": P.ref_price(b),
                     "distance": r["distance_km"], "value": value,
                     "base_score": r["score"], "kg": b.miktar_kg})
    if not cand:
        return {"demand_code": d.code, "ranked": [], "front": [], "weights": {}}

    nc = _norm([c["carbon"] for c in cand])         # maximize
    nk = _norm([c["cost"] for c in cand])           # minimize → 1-x
    nd = _norm([c["distance"] for c in cand])       # minimize → 1-x
    nv = _norm([c["value"] for c in cand])          # maximize
    W = w_carbon + w_cost + w_distance + w_value or 1.0
    for i, c in enumerate(cand):
        c["_obj"] = {"carbon": nc[i], "cost": 1 - nk[i], "distance": 1 - nd[i], "value": nv[i]}
        c["pareto_score"] = round(
            (w_carbon * nc[i] + w_cost * (1 - nk[i]) + w_distance * (1 - nd[i])
             + w_value * nv[i]) / W, 4)

    # Pareto cephesi: 4 amaçta (hepsi "büyük iyi" normalize) domine edilmeyenler
    def dominated(a, b):
        o1, o2 = a["_obj"], b["_obj"]
        return (all(o2[k] >= o1[k] for k in o1) and any(o2[k] > o1[k] for k in o1))
    front = [c["batch_code"] for c in cand
             if not any(dominated(c, o) for o in cand if o is not c)]

    cand.sort(key=lambda c: c["pareto_score"], reverse=True)
    ranked = [{"batch_code": c["batch_code"], "pareto_score": c["pareto_score"],
               "base_score": c["base_score"], "carbon_kg": round(c["carbon"], 0),
               "cost": c["cost"], "distance_km": c["distance"],
               "value": round(c["value"], 3), "on_front": c["batch_code"] in front}
              for c in cand[:top]]
    return {"demand_code": d.code,
            "weights": {"carbon": w_carbon, "cost": w_cost,
                        "distance": w_distance, "value": w_value},
            "ranked": ranked, "front": front}


# --------------------------------------------------------------------------- #
# 4) PROAKTİF — üretim planından fire tahmini + önceden alıcı bildirimi
# --------------------------------------------------------------------------- #
def forecast(factory, demands, monthly_kg: float, fire_rate_pct: float,
             kumas: str, pamuk: float, polyester: float, elastan: float,
             gramaj: int, kalite: str = "B", top: int = 5) -> dict:
    fire_kg = round(monthly_kg * fire_rate_pct / 100.0, 0)
    # Kalıcı olmayan tahmini parti (fabrikanın konumunda)
    fp = R.Parti(id="FORECAST", fabrika=factory.name, lat=factory.lat, lon=factory.lon,
                 sehir=factory.city, pamuk=pamuk, polyester=polyester, elastan=elastan,
                 kumas=kumas, gramaj=gramaj, en_m=1.8, miktar_kg=fire_kg, kalite=kalite,
                 min_fiyat=18, depo_gun=0, dogrulanmis=False, itibar=factory.reputation)
    pre = []
    for d in demands:
        t = ES.demand_to_talep(d)
        ok, _ = R.sert_filtre(fp, t)
        if not ok:
            continue
        s = R.skorla(fp, t)
        pre.append({"demand_code": d.code, "buyer": d.buyer,
                    "score": round(R.match_score(s["bilesen"]), 4),
                    "distance_km": round(s["mesafe_km"], 1)})
    pre.sort(key=lambda x: x["score"], reverse=True)
    pre = pre[:top]
    return {
        "factory": factory.name, "monthly_kg": monthly_kg,
        "fire_rate_pct": fire_rate_pct, "forecast_fire_kg": fire_kg,
        "prematched_buyers": pre,
        "message": (f"{factory.name} için önümüzdeki dönemde ~{fire_kg:.0f} kg {kumas} "
                    f"firesi öngörülüyor; {len(pre)} alıcı önceden bilgilendirilebilir."),
    }


# --------------------------------------------------------------------------- #
# 5) "NEDEN EŞLEŞMEDİ" — sert filtre gerekçeleri
# --------------------------------------------------------------------------- #
def rejections_for_demand(d, batches, limit: int = 20) -> list[dict]:
    out = []
    for b in batches:
        ok, reason = ES.hard_filter(b, d)
        if not ok:
            out.append({"batch_code": b.code, "kumas": b.kumas,
                        "miktar_kg": b.miktar_kg, "reason": reason})
    return out[:limit]


# --------------------------------------------------------------------------- #
# 6) LTR KANCASI — kabul edilen işlemlerden ağırlık ÖNER (canlıyı değiştirmez)
# --------------------------------------------------------------------------- #
def propose_weights(accepted_components: list[dict]) -> dict:
    """
    Kabul edilen (COMPLETED) işlemlerin bileşen katkılarından ağırlık önerir.
    Sezgi: kabul edilen anlaşmalarda hangi bileşenler tutarlı biçimde yüksekse
    onlara daha çok ağırlık. Bu bir ÖNERİDİR; sonuç tutarlılığını korumak için
    canlı AGIRLIK sabitleri değiştirilmez.
    """
    keys = list(R.AGIRLIK.keys())
    if not accepted_components:
        return {"proposed": None, "current": R.AGIRLIK,
                "note": "Henüz tamamlanmış işlem yok; öğrenme için veri bekleniyor."}
    means = {k: sum(c.get(k, 0) for c in accepted_components) / len(accepted_components)
             for k in keys}
    toplam = sum(means.values()) or 1.0
    proposed = {k: round(means[k] / toplam, 3) for k in keys}
    return {"proposed": proposed, "current": R.AGIRLIK,
            "sample_size": len(accepted_components),
            "note": "Öneri; veri biriktikçe learning-to-rank ile iyileşir. "
                    "Canlı skor ağırlıkları değiştirilmedi (sonuç tutarlılığı)."}
