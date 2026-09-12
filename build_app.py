"""
ReLoop — Web uygulaması derleyici.
app_shell.template.html + (seed + motor çıktısı) -> reloop_app.html (tek dosya, internetsiz açılır).

Tek doğruluk kaynağı: seed.py verisi + reloop.py sabitleri JSON olarak gömülür;
arayüzdeki JS motoru bu sabitlerle reloop.py'yi birebir yansıtır.
"""
import json
from dataclasses import asdict
import reloop as R
import seed
import run_demo
from run_demo import VARSAYIM, ESLESME_ESIGI

TARIH = "2026-08-12"


def _parti_dict(p):
    d = asdict(p)
    d.pop("depo_gun", None)  # arayüzde kullanılmıyor
    return d


def _harita_sinir():
    """Basitleştirilmiş Türkiye sınırı (offline, build anında gömülür).
    MultiPolygon dış halkaları -> [[[lon,lat],...], ...]. Koordinatlar 3 basamağa
    yuvarlanır (tek dosya boyutu için)."""
    with open("turkiye_sinir.json", encoding="utf-8") as f:
        gj = json.load(f)
    geom = gj["features"][0]["geometry"]
    halkalar = []
    for poly in geom["coordinates"]:      # her poligonun dış halkası (poly[0])
        halkalar.append([[round(lon, 3), round(lat, 3)] for lon, lat in poly[0]])
    return halkalar


def _uygunluk_ozet(partiler, talepler):
    """Benzersiz firma × tüm parti için uygunluk verdict sayıları (Python).
    Parite testi JS'in AYNI sayıları üretmesini doğrular (uygunluk motoru parite)."""
    seen, uniq = set(), []
    for t in talepler:
        k = t.firma_adi or t.alici
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    ozet = {"UYGUN": 0, "UYARI": 0, "ENGELLİ": 0}
    for p in partiler:
        for t in uniq:
            ozet[R.uygunluk(p, t)["verdict"]] += 1
    return ozet


def veri():
    partiler, talepler, fabrika_itibar = seed.uret()

    # Bölüm 9 örnek hesabı (rapordaki senaryo) — arayüzdeki formül kırılımı için
    op = R.Parti(id="P-DEMO", fabrika="Fabrika-Ornek", lat=38.680, lon=29.410,
                 sehir="Uşak", pamuk=100, polyester=0, elastan=0, kumas="suprem",
                 gramaj=180, en_m=1.8, miktar_kg=800, kalite="A", min_fiyat=18,
                 depo_gun=20, dogrulanmis=True, itibar=0.85)
    ot = R.Talep(id="T-DEMO", alici="GeriDonusum-Ornek", lat=38.905, lon=29.410,
                 sehir="Uşak", min_pamuk=95, max_elastan=0, ihtiyac_kg=1000,
                 max_fiyat=22, min_kalite="B")
    s9 = R.skorla(op, ot)
    ornek9 = {"bilesen": s9["bilesen"], "skor": R.match_score(s9["bilesen"]),
              "mesafe_km": s9["mesafe_km"]}

    return {
        "meta": {"tarih": TARIH, "not": "ReLoop · örnek ortam"},
        "esik": ESLESME_ESIGI,
        "varsayim": {"co2": VARSAYIM["co2_kg_per_kg"], "su": VARSAYIM["su_L_per_kg"]},
        "agirlik": R.AGIRLIK,
        "sabit": {
            "gramaj_aralik": R.GRAMAJ_ARALIK,
            "beklenen_lif": R.BEKLENEN_LIF,
            "elastan_esik": R.ELASTAN_UST_ESIK,
            "min_miktar": R.MIN_MIKTAR_KG,
            "mesafe_yaricap": R.MESAFE_YARICAP_KM,
            "kalite_sira": R.KALITE_SIRA,
            "kalite_skor": R.KALITE_SKOR,
            "etiket": R.BILESEN_ETIKET,
            "kumaslar": seed.KUMASLAR,
            "atik_kodu": R.ATIK_KODU_PRECONSUMER,
            "depo_yasal_gun": R.DEPO_YASAL_GUN,
            "standart_aciklama": R.STANDART_ACIKLAMA,
        },
        "sehirler": seed.SEHIRLER,
        "harita_sinir": _harita_sinir(),
        "partiler": [_parti_dict(p) for p in partiler],
        "talepler": [asdict(t) for t in talepler],
        "ornek9": ornek9,
        # Python motorunun kamu dashboard değerleri — parite testi JS'in aynı
        # sayıları üretip üretmediğini buradan doğrular (Python↔JS parite çıpası).
        "parite_beklenen": run_demo.dashboard_ozet(partiler, talepler),
        "uygunluk_ozet": _uygunluk_ozet(partiler, talepler),
    }


def main():
    with open("app_shell.template.html", encoding="utf-8") as f:
        shell = f.read()
    data_json = json.dumps(veri(), ensure_ascii=False, separators=(",", ":"))
    if "__RELOOP_DATA__" not in shell:
        raise SystemExit("app_shell.template.html içinde __RELOOP_DATA__ yer tutucusu yok!")
    html = shell.replace("__RELOOP_DATA__", data_json)
    with open("reloop_app.html", "w", encoding="utf-8") as f:
        f.write(html)
    kb = len(html.encode("utf-8")) / 1024
    print(f"reloop_app.html yazıldı ({kb:.0f} KB, tek dosya, harici bağımlılık yok).")


if __name__ == "__main__":
    main()
