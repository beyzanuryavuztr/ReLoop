"""
Motor servisi — `reloop.py` çekirdeğini SARAR (tek doğruluk kaynağı).

Backend, JS arayüz ve rapor aynı formülü kullanır; bu katman ORM nesnelerini
motorun `Parti`/`Talep` dataclass'larına çevirir ve açıklanabilir skoru döndürür.
Motor mantığı burada TEKRARLANMAZ; yalnızca çağrılır.
"""
from __future__ import annotations

from ._enginepath import ensure_engine_on_path

ensure_engine_on_path()  # reloop.py'yi dev + Docker düzeninde bulup path'e ekler
import reloop as R  # noqa: E402  (tek motor doğruluk kaynağı)

# Sabitleri dışarıya aç (arayüz/rapor ile ortak sözlük)
AGIRLIK = R.AGIRLIK
BILESEN_ETIKET = R.BILESEN_ETIKET
MESAFE_YARICAP_KM = R.MESAFE_YARICAP_KM
MIN_MIKTAR_KG = R.MIN_MIKTAR_KG


def batch_to_parti(b) -> R.Parti:
    """Batch ORM → motor Parti dataclass'ı."""
    return R.Parti(
        id=b.code, fabrika=b.factory.name if b.factory else "?",
        lat=b.lat, lon=b.lon, sehir=b.city,
        pamuk=b.pamuk, polyester=b.polyester, elastan=b.elastan,
        kumas=b.kumas, gramaj=b.gramaj, en_m=b.en_m, miktar_kg=b.miktar_kg,
        kalite=b.kalite, min_fiyat=b.min_fiyat, depo_gun=b.depo_gun,
        dogrulanmis=b.dogrulanmis, itibar=b.reputation,
    )


def demand_to_talep(d) -> R.Talep:
    """Demand ORM → motor Talep dataclass'ı."""
    return R.Talep(
        id=d.code, alici=d.buyer, lat=d.lat, lon=d.lon, sehir=d.city,
        min_pamuk=d.min_pamuk, max_elastan=d.max_elastan, ihtiyac_kg=d.ihtiyac_kg,
        max_fiyat=d.max_fiyat, min_kalite=d.min_kalite,
        dogrulanmis_ister=d.dogrulanmis_ister,
    )


def inconsistencies_for(b) -> list[str]:
    """DMP tutarsızlık uyarıları (motorun `tutarsizlik_uyarilari`)."""
    return R.tutarsizlik_uyarilari(batch_to_parti(b))


def firma_talepleri() -> list:
    """Alıcı firma kayıt defterinden (seed.FIRMALAR) motor Talep nesneleri.
    Konum uygunlukta kullanılmaz; kabul kriterleri firmanın standardından gelir."""
    import seed
    out = []
    for i, (ad, tur, sehir, cert, izl, lot, elas, pamuk, kal, kaynak) in enumerate(seed.FIRMALAR, 1):
        out.append(R.Talep(
            id=f"F{i:02d}", alici=ad, lat=0.0, lon=0.0, sehir=sehir,
            min_pamuk=float(pamuk), max_elastan=float(elas), ihtiyac_kg=0.0,
            max_fiyat=0.0, min_kalite=kal, dogrulanmis_ister=izl,
            firma_adi=ad, firma_tur=tur, sertifika_ister=list(cert),
            izlenebilirlik_ister=izl, min_lot_kg=float(lot), kaynak=kaynak))
    return out


def eligibility(b) -> dict:
    """Bir partinin alıcı firma kayıt defterine çift-mevzuat uygunluğu (reloop.uygunluk).
    Yasal katman parti-düzeyinde (UÇBS/TABS beyanı); firma katmanı firma başına."""
    p = batch_to_parti(b)
    firms = [R.uygunluk(p, t) for t in firma_talepleri()]
    say = {"UYGUN": 0, "UYARI": 0, "ENGELLİ": 0}
    for u in firms:
        say[u["verdict"]] += 1
    return {"batch_code": b.code, "summary": say,
            "legal_ok": firms[0]["yasal_ok"] if firms else True,
            "firms": firms}


def hard_filter(b, d) -> tuple[bool, str]:
    return R.sert_filtre(batch_to_parti(b), demand_to_talep(d))


def score_pair(b, d) -> dict:
    """
    Açıklanabilir skor: sert filtre + kademeli bileşenler + ağırlıklı katkı.
    Dönen: {ok, reason, score, components, contributions, distance_km,
            consistent, explanation}
    """
    p, t = batch_to_parti(b), demand_to_talep(d)
    ok, reason = R.sert_filtre(p, t)
    s = R.skorla(p, t)
    score = R.match_score(s["bilesen"])
    return {
        "ok": ok,
        "reason": reason,
        "score": round(score, 4),
        "components": {k: round(v, 4) for k, v in s["bilesen"].items()},
        "contributions": {k: round(v, 4) for k, v in R.katki(s["bilesen"]).items()},
        "distance_km": round(s["mesafe_km"], 1),
        "consistent": s["tutarli"],
        "explanation": R.aciklama(s, score),
        "labels": BILESEN_ETIKET,
    }


def best_matches_for_demand(d, batches, top: int = 10) -> list[dict]:
    """Bir talep için sert filtreyi geçen partileri skora göre sırala."""
    out = []
    for b in batches:
        r = score_pair(b, d)
        if not r["ok"]:
            continue
        out.append({"batch_code": b.code, "batch_id": b.id, **r})
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:top]


def best_match_for_batch(b, demands) -> dict | None:
    """Bir parti için en yüksek skorlu talep (dashboard/dolgu için)."""
    best = None
    for d in demands:
        r = score_pair(b, d)
        if not r["ok"]:
            continue
        if best is None or r["score"] > best["score"]:
            best = {"demand_code": d.code, "demand_id": d.id, **r}
    return best
