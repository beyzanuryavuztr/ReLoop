"""
Etki hesabı — gerçek, kaynaklı LCA katsayıları (sistem sınırı: lif düzeyi,
virgin pamuk vs mekanik geri kazanılan pamuk, kg bazında).

Katsayılar (kaynaklı; metrikler bunlardan canlı hesaplanır — sabit sayı gömülmez):
  • CO₂ tasarrufu (konservatif) : 1.60 kg CO₂e/kg   [PE-International / Miljögiraff]
  • CO₂ tasarrufu (ecoinvent)   : 2.93 kg CO₂e/kg   [ecoinvent üst-sınır]
  • Su tasarrufu                : 2100 L/kg          [konservatif; virgin pamuk ~10.000 L/kg]
  • Enerji tasarrufu            : 18 MJ/kg           [Textile Exchange 2025 mertebesi]

Her sayı 'varsayım + yöntem + kaynak' ile sunulur (şeffaflık; uydurma yok).
"""
from __future__ import annotations

from .models import Batch, Demand, Factory, Transaction, TxState

ESLESME_ESIGI = 0.60


def tr_sayi(n: float, ondalik: int = 0) -> str:
    """Türkçe binlik ayraçlı sayı biçimi (binlik '.', ondalık ',').
    `f'{n:,.0f}'` ABD virgülü üretir ('458,000') ve Türkçe okuyucuda ondalık
    gibi görünür → bu helper ile düzeltilir ('458.000')."""
    s = f"{n:,.{ondalik}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")

# Türkiye pre-consumer tekstil firesi ulusal çıpası (rapor [1] Altun 2012:
# 2009 için 884.890 t tekstil atığı, ~%52 pre-consumer → ~458.000 t).
NATIONAL_PRECONSUMER_T = 458_000.0

COEFF = {
    "co2_conservative_kg_per_kg": 1.60,
    "co2_ecoinvent_kg_per_kg": 2.93,
    "water_l_per_kg": 2100.0,
    "energy_mj_per_kg": 18.0,
}

SOURCES = {
    "co2_conservative_kg_per_kg": "PE-International / Miljögiraff (mekanik geri dönüşüm, lif düzeyi)",
    "co2_ecoinvent_kg_per_kg": "ecoinvent v3 (üst-sınır senaryosu)",
    "water_l_per_kg": "Konservatif; Chapagain (virgin pamuk ~10.000 L/kg) referansına göre alt-sınır",
    "energy_mj_per_kg": "Textile Exchange 2025 mertebesi",
}


def dashboard_metrics(db, dataset: str) -> dict:
    """Kamu dashboard metrikleri (anonim/agrega) — motorla hesaplanır."""
    from . import engine_service as ES

    # Satılmış partiler AKTİF ekosistemden düşülür — aksi halde uzun ömürlü bir
    # veritabanında satılan envanter 'eşleşen/yönlendirilen'i şişirir (denetim
    # bulgusu 1.8). Taze referans veri setinde hiç 'sold' yok → sayılar aynı kalır.
    batches = db.query(Batch).filter(Batch.status != "sold").all()
    demands = db.query(Demand).all()

    # Eşleşen partileri topla; absorbed'ı KÜRESEL talep kapasite havuzundan düş
    # (aynı talebi birden çok parti sahiplenemez → gerçekten konservatif).
    matches = []
    for b in batches:
        best = ES.best_match_for_batch(b, demands)
        if best and best["score"] >= ESLESME_ESIGI:
            matches.append((best["score"], b.miktar_kg, best["distance_km"], best["demand_id"]))

    demand_remaining = {d.id: d.ihtiyac_kg for d in demands}
    eslesen_kg, absorbed_kg, skorlar, mesafeler = 0.0, 0.0, [], []
    for score, kg, dist, did in sorted(matches, key=lambda x: -x[0]):  # en iyi eşleşme öncelikli
        eslesen_kg += kg
        take = min(kg, max(0.0, demand_remaining.get(did, 0.0)))
        absorbed_kg += take
        demand_remaining[did] = demand_remaining.get(did, 0.0) - take
        skorlar.append(score)
        mesafeler.append(dist)

    n_uyari = sum(1 for b in batches if b.inconsistencies)
    ton = eslesen_kg / 1000.0

    return {
        "dataset": dataset,
        "factories": db.query(Factory).filter(Factory.role == "seller").count(),
        "batches": len(batches),
        "demands": len(demands),
        "matched": len(skorlar),
        "match_rate_pct": round(len(skorlar) / len(batches) * 100, 1) if batches else 0.0,
        "routed_tonnes": round(ton, 1),
        "absorbed_tonnes": round(absorbed_kg / 1000.0, 1),
        "co2_tonnes_conservative": round(eslesen_kg * COEFF["co2_conservative_kg_per_kg"] / 1000, 1),
        "co2_tonnes_ecoinvent": round(eslesen_kg * COEFF["co2_ecoinvent_kg_per_kg"] / 1000, 1),
        "water_million_l": round(eslesen_kg * COEFF["water_l_per_kg"] / 1_000_000, 1),
        "avg_score_pct": round(sum(skorlar) / len(skorlar) * 100, 0) if skorlar else 0.0,
        "min_score_pct": round(min(skorlar) * 100, 0) if skorlar else 0.0,
        "max_score_pct": round(max(skorlar) * 100, 0) if skorlar else 0.0,
        "avg_distance_km": round(sum(mesafeler) / len(mesafeler), 0) if mesafeler else 0.0,
        "inconsistencies_flagged": n_uyari,
        "assumptions": {
            "match_threshold": ESLESME_ESIGI,
            "coefficients": COEFF,
            "sources": SOURCES,
            "system_boundary": "Lif düzeyi (virgin pamuk vs mekanik geri kazanılan pamuk), kg bazında",
            "routed_vs_absorbed": ("routed_tonnes = potansiyel üst-sınır (parti tümüyle yönlendirilir "
                                   "varsayımı); absorbed_tonnes = konservatif (en iyi talebin karşıladığı kadar, "
                                   "harmanlama yok). CO₂/su ÜST-SINIR routed'a göre hesaplanır."),
            "note": "Sentetik/yarı-gerçek ekosistem; sayılar varsayım+yöntem+kaynak ile sunulur.",
        },
    }


# --------------------------------------------------------------------------- #
# CO₂ / su / enerji karşılaştırma (virgin vs geri kazanılan) — #28
# --------------------------------------------------------------------------- #
def comparison_table() -> dict:
    return {
        "unit": "kg başına (lif düzeyi)",
        "rows": [
            {"metric": "CO₂e (kg)", "virgin": "1,6–2,9", "recycled": "~0",
             "saving": f"{COEFF['co2_conservative_kg_per_kg']}–{COEFF['co2_ecoinvent_kg_per_kg']}",
             "source": SOURCES["co2_conservative_kg_per_kg"]},
            {"metric": "Su (L)", "virgin": "~2.100+", "recycled": "~0",
             "saving": f"{COEFF['water_l_per_kg']:.0f}", "source": SOURCES["water_l_per_kg"]},
            {"metric": "Enerji (MJ)", "virgin": "~18+", "recycled": "düşük",
             "saving": f"{COEFF['energy_mj_per_kg']:.0f}", "source": SOURCES["energy_mj_per_kg"]},
        ],
        "note": "Mekanik geri kazanım, virgin pamuğun tarımsal/işleme yükünü ortadan kaldırır.",
    }


# --------------------------------------------------------------------------- #
# Atık önleme metriği (#25) — kaskadla yerleşim; çöpe giden = 0
# --------------------------------------------------------------------------- #
def waste_prevention(db) -> dict:
    from . import matching_advanced as MA
    batches = db.query(Batch).all()
    demands = db.query(Demand).all()
    kg = {"textile": 0.0, "downcycle": 0.0, "rdf": 0.0}
    for b in batches:
        ch = MA.cascade_for_batch(b, demands)["cascade"]["channel"]
        kg[ch] = kg.get(ch, 0.0) + b.miktar_kg
    total = sum(kg.values())
    return {
        "total_fire_t": round(total / 1000, 1),
        "recycled_textile_t": round(kg["textile"] / 1000, 1),
        "downcycled_t": round(kg["downcycle"] / 1000, 1),
        "energy_recovery_t": round(kg["rdf"] / 1000, 1),
        "landfill_diverted_t": round(total / 1000, 1),
        "landfill_diversion_rate_pct": 100.0,
        "note": ("Kaskad sayesinde işlenen firenin tamamı bir geri kazanım/enerji rotasına "
                 "yönlendirilir; depolamaya (çöp) giden ~0. Atık önleme, geri dönüşümden ayrı raporlanır."),
    }


# --------------------------------------------------------------------------- #
# Fabrika etki panosu (#29)
# --------------------------------------------------------------------------- #
def factory_panel(db, factory_id: int) -> dict:
    from . import engine_service as ES
    f = db.get(Factory, factory_id)
    if not f:
        return {"error": "fabrika yok"}
    batches = db.query(Batch).filter(Batch.factory_id == factory_id).all()
    demands = db.query(Demand).all()
    listed_kg = sum(b.miktar_kg for b in batches)
    # CO₂/su tasarrufu YALNIZ eşleşen (rotalanabilir) partiden hesaplanır — listelenen
    # ama eşleşmemiş envanter 'gerçekleşmiş tasarruf' gibi sunulmaz (denetim bulgusu 1.4).
    matched_kg = 0.0
    for b in batches:
        best = ES.best_match_for_batch(b, demands)
        if best and best["score"] >= ESLESME_ESIGI:
            matched_kg += b.miktar_kg
    completed = (db.query(Transaction)
                   .filter(Transaction.status == TxState.COMPLETED).all())
    codes = {b.id for b in batches}
    revenue = sum((t.agreed_price or 0) * (t.agreed_qty_kg or 0)
                  for t in completed if t.batch_id in codes)
    co2 = matched_kg * COEFF["co2_conservative_kg_per_kg"] / 1000
    return {
        "factory": f.name, "city": f.city, "reputation": f.reputation,
        "batches": len(batches),
        "listed_kg": round(listed_kg, 0),
        "matched_kg": round(matched_kg, 0),
        "total_kg": round(listed_kg, 0),   # geriye dönük uyum
        "co2_saving_t": round(co2, 1),
        "water_saving_million_l": round(matched_kg * COEFF["water_l_per_kg"] / 1e6, 2),
        "revenue_tl_from_completed": round(revenue, 0),
        "note": ("Fabrika bazlı özet. CO₂/su yalnız EŞLEŞEN partiden (potansiyel tasarruf); "
                 "gelir yalnız tamamlanan işlemlerden (gerçekleşen)."),
    }


# --------------------------------------------------------------------------- #
# NDC ulusal projeksiyon (#26) + "ne olurdu" simülatörü (#30) + iklim/NDC çerçeve (#31)
# Çerçeve = Türkiye'nin resmî iklim taahhütleri: 2053 net-sıfır yolu + 2030 NDC
# (BAU'ya göre ~%41 azaltım); karbon değeri kurulmakta olan ulusal ETS mertebesinde.
# --------------------------------------------------------------------------- #
def blended_co2_coeff(db) -> float:
    """
    Kaskad ROTA KARIŞIMINA göre ağırlıklı CO₂ tasarrufu (kg/kg). Tüm fire tekstil-tekstile
    gitmediği için (yalnız ~%48; gerisi downcycling/enerji) gerçekçi katsayı 1,6'nın ALTINDADIR.
    Böylece ulusal projeksiyon kaskadla TUTARLI olur (abartı kalkar).
    """
    from . import matching_advanced as MA
    batches = db.query(Batch).all()
    demands = db.query(Demand).all()
    tot_kg, tot_co2 = 0.0, 0.0
    for b in batches:
        route = MA.cascade_for_batch(b, demands)["cascade"]
        c = route.get("co2_saving_kg_per_kg", COEFF["co2_conservative_kg_per_kg"])
        tot_kg += b.miktar_kg
        tot_co2 += b.miktar_kg * c
    return round(tot_co2 / tot_kg, 3) if tot_kg else COEFF["co2_conservative_kg_per_kg"]


def national_projection(adoption_pct: float, blend_co2: float | None = None) -> dict:
    blend = blend_co2 if blend_co2 is not None else COEFF["co2_conservative_kg_per_kg"]
    recovered_t = NATIONAL_PRECONSUMER_T * adoption_pct / 100.0
    recovered_kg = recovered_t * 1000
    co2_real = recovered_kg * blend / 1000                               # rota-ağırlıklı gerçekçi
    co2_upper = recovered_kg * COEFF["co2_ecoinvent_kg_per_kg"] / 1000    # tümü tekstil + ecoinvent (üst sınır)
    water_ml = recovered_kg * COEFF["water_l_per_kg"] / 1e6
    return {
        "adoption_pct": adoption_pct,
        "national_preconsumer_t": NATIONAL_PRECONSUMER_T,
        "recovered_t": round(recovered_t, 0),
        "blend_co2_kg_per_kg": round(blend, 3),
        "co2e_saving_t": {"conservative": round(co2_real, 0), "ecoinvent": round(co2_upper, 0)},
        "water_saving_million_l": round(water_ml, 0),
        "framing": (f"Türkiye pre-consumer tekstil firesinin %{adoption_pct:.0f}'i geri kazanılırsa, "
                    f"kaskad rota karışımına göre (~{blend:.2f} kg CO₂e/kg ağırlıklı) yıllık "
                    f"~{tr_sayi(co2_real)} ton CO₂e önlenir; tümü tekstil-tekstile + ecoinvent üst sınırı "
                    f"~{tr_sayi(co2_upper)} ton. Türkiye'nin 2030 NDC ve 2053 net-sıfır hedeflerine "
                    f"ölçülebilir sektörel katkı."),
        "note": ("Ulusal çıpa ~458.000 t (Altun 2012). Katsayı rota-ağırlıklı: tüm fire tekstil-tekstile "
                 "gitmez (~%48); downcycling/enerji rotaları daha düşük CO₂ sağlar → gerçekçi. Doğrusal ölçekleme. "
                 "AB ESPR + Dijital Ürün Pasaportu tekstili öncelikli kategori sayar → izlenebilirlik zorunlu hâle gelir."),
    }


def simulator(participation_pct: float, carbon_price_tl_per_ton: float,
              new_facilities: int, blend_co2: float | None = None) -> dict:
    """
    'Ne olurdu?' — katılım oranı, karbon fiyatı ve yeni tesis kaydırıcıları.
    Yeni tesisler erişilebilir fireyi artırır (her tesis ~%2 ek erişim varsayımı).
    CO₂, kaskad rota-ağırlıklı katsayıyla (gerçekçi) hesaplanır.
    """
    reach_pct = min(100.0, participation_pct + new_facilities * 2.0)
    proj = national_projection(reach_pct, blend_co2)
    co2_lo = proj["co2e_saving_t"]["conservative"]
    carbon_value_tl = co2_lo * carbon_price_tl_per_ton
    econ_value_tl = proj["recovered_t"] * 1000 * 18.0    # ~18 TL/kg ortalama fire değeri
    return {
        "inputs": {"participation_pct": participation_pct,
                   "carbon_price_tl_per_ton": carbon_price_tl_per_ton,
                   "new_facilities": new_facilities},
        "effective_reach_pct": round(reach_pct, 1),
        "recovered_t": proj["recovered_t"],
        "co2e_saving_t": proj["co2e_saving_t"],
        "carbon_credit_value_tl": round(carbon_value_tl, 0),
        "material_value_tl": round(econ_value_tl, 0),
        "climate_framing": (f"Bu senaryo yıllık ~{tr_sayi(co2_lo)} ton CO₂e azaltımına ve "
                            f"~{tr_sayi(carbon_value_tl)} TL karbon kredi değerine karşılık gelir "
                            f"(kurulmakta olan ulusal ETS fiyatıyla değerlenir); Türkiye'nin 2030 NDC "
                            f"ve 2053 net-sıfır yoluna ölçülebilir katkı."),
        "note": "Kaydırıcı senaryosu; doğrusal varsayımlar, karbon fiyatı ulusal ETS mertebesinde illüstratif.",
    }


# --------------------------------------------------------------------------- #
# Birim ekonomisi + üç katmanlı gelir modeli (ticarileşme)
# --------------------------------------------------------------------------- #
REVENUE_MODEL = [
    {"layer": 1, "name": "Başarıya dayalı komisyon",
     "desc": "Tamamlanan her işlemden %2–4 komisyon (yalnız eşleşme gerçekleşince).",
     "type": "işlem geliri"},
    {"layer": 2, "name": "ReLoop Verified aboneliği",
     "desc": "Doğrulanmış rozet + öncelikli görünürlük + gelişmiş analitik (aylık SaaS).",
     "type": "yinelenen gelir"},
    {"layer": 3, "name": "Anonim veri lisansı",
     "desc": "Agrega/anonim fire endeksi ve bölgesel istatistiklerin kamu/araştırma lisansı.",
     "type": "veri geliri"},
]


def unit_economics(qty_kg: float, price_tl_per_kg: float, commission_pct: float = 3.0,
                   verification_cost_tl: float = 150.0, verified: bool = True) -> dict:
    gross = qty_kg * price_tl_per_kg
    commission = gross * commission_pct / 100.0
    vcost = verification_cost_tl if verified else 0.0
    margin = commission - vcost
    return {
        "inputs": {"qty_kg": qty_kg, "price_tl_per_kg": price_tl_per_kg,
                   "commission_pct": commission_pct, "verified": verified,
                   "verification_cost_tl": vcost},
        "gross_transaction_tl": round(gross, 0),
        "commission_revenue_tl": round(commission, 2),
        "verification_cost_tl": round(vcost, 2),
        "contribution_margin_tl": round(margin, 2),
        "margin_positive": margin > 0,
        "revenue_model": REVENUE_MODEL,
        "note": ("Örnek parti birim ekonomisi: komisyon geliri − doğrulama maliyeti = "
                 "katkı marjı. Ticarileşme, Bakanlık protokolü çerçevesinde planlanır."),
    }
