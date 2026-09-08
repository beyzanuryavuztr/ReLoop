"""
AB Dijital Ürün Pasaportu (DPP) uyumu (Dalga 4):
  • JSON-LD export (#19)       — yapılandırılmış, bağlanabilir (linked-data) çıktı
  • ESPR alan eşlemesi (#20)   — pasaport şeması ↔ ESPR DPP veri kategorileri
  • İmzalı/doğrulanabilir DPP   — en güncel hash zinciri hash'i 'proof' olarak eklenir
                                  (Dalga 2 menşe zincirine bağlanır)

Dürüst not: CIRPASS/GS1 tam sözlüğü yerine gösterim amaçlı bir eşleme kullanılır;
alanlar ESPR veri kategorileriyle hizalıdır. Akredite bir DPP kaydı değildir.
"""
from __future__ import annotations

from .pricing import fiber_class

DPP_CONTEXT = {
    "@vocab": "https://schema.org/",
    "reloop": "https://reloop.example/dpp#",
    "dpp": "https://data.europa.eu/espr/dpp#",
    "identifier": "reloop:identifier",
    "materialComposition": "dpp:materialComposition",
    "recycledContentShare": "dpp:recycledContentShare",
    "preConsumerWaste": "reloop:preConsumerWaste",
    "wasteCode": "reloop:ewcWasteCode",
    "qualityGrade": "reloop:qualityGrade",
    "originRegion": "reloop:originRegion",
    "verified": "reloop:labVerified",
    "proof": "reloop:integrityProof",
}


def build_jsonld(b, last_hash: str | None) -> dict:
    return {
        "@context": DPP_CONTEXT,
        "@type": "Product",
        "@id": f"https://reloop.example/dmp/{b.code}",
        "identifier": b.code,
        "name": f"Tekstil fire partisi ({b.kumas})",
        "category": "pre-consumer textile scrap",
        "wasteCode": b.waste_code,
        "originRegion": b.city,
        "weight": {"@type": "QuantitativeValue", "value": b.miktar_kg, "unitCode": "KGM"},
        "materialComposition": [
            {"material": "cotton", "share": b.pamuk},
            {"material": "polyester", "share": b.polyester},
            {"material": "elastane", "share": b.elastan},
        ],
        "fiberClass": fiber_class(b.pamuk, b.polyester),
        "recycledContentShare": 0,          # pre-consumer virgin fire; geri kazanıma girer
        "preConsumerWaste": True,
        "qualityGrade": b.kalite,
        "verified": b.dogrulanmis,
        "proof": {
            "@type": "reloop:HashChainProof",
            "algorithm": "SHA-256",
            "chainHead": last_hash,
            "note": "Menşe hash zincirinin en güncel hash'i; kurcalama tespiti sağlar.",
        },
    }


# ESPR DPP veri kategorileri → pasaport alanı eşlemesi (statik şema)
ESPR_MAPPING_SCHEMA = [
    {"espr_category": "Product identifier (unique)", "passport_field": "code",
     "note": "Benzersiz ürün kimliği; QR/NFC ile çözülür."},
    {"espr_category": "Material composition", "passport_field": "pamuk/polyester/elastan",
     "note": "Lif yüzdeleri; DMP tutarsızlık dedektörüyle doğrulanır."},
    {"espr_category": "Substances of concern", "passport_field": "elastan (kontaminant)",
     "note": "Mekanik geri dönüşümü bozan kontaminant izlenir."},
    {"espr_category": "Recyclability / recycled content", "passport_field": "preConsumerWaste + fiber_class",
     "note": "Pre-consumer fire; geri kazanım rotası kaskadla belirlenir."},
    {"espr_category": "Origin / traceability", "passport_field": "city + hash chain",
     "note": "Menşe bölgesi + değişmez olay zinciri (chain-of-custody)."},
    {"espr_category": "Performance / quality", "passport_field": "kalite (A/B/C), gramaj",
     "note": "Kalite sınıfı ve gramaj."},
    {"espr_category": "Data carrier", "passport_field": "QR / NFC (NTAG213)",
     "note": "Fiziksel taşıyıcı; herkese açık DMP sayfasına çözülür."},
]


def espr_view(b, last_hash: str | None) -> dict:
    return {
        "batch_code": b.code,
        "espr_data": {
            "product_identifier": b.code,
            "material_composition": {"cotton_pct": b.pamuk, "polyester_pct": b.polyester,
                                     "elastane_pct": b.elastan},
            "substances_of_concern": {"elastane_contaminant_pct": b.elastan},
            "recyclability": {"pre_consumer": True, "fiber_class": fiber_class(b.pamuk, b.polyester)},
            "origin_traceability": {"region": b.city, "chain_head_hash": last_hash},
            "quality_performance": {"grade": b.kalite, "gramaj_g_m2": b.gramaj},
            "data_carrier": {"qr": f"/passports/{b.code}/qr.svg", "nfc": "NTAG213"},
        },
        "mapping": ESPR_MAPPING_SCHEMA,
        "note": "ESPR veri kategorileriyle hizalı gösterim eşlemesi (akredite DPP kaydı değil).",
    }
