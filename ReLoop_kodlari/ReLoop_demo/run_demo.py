"""
ReLoop — Demo çalıştırıcı.
Çıktı: (1) seed özeti, (2) DMP tutarsızlık örneği, (3) Bölüm 9 birebir örnek hesap,
        (4) örnek eşleşmeler, (5) kamu dashboard metrikleri + dashboard.html
"""
from reloop import (Parti, Talep, skorla, match_score, katki, sert_filtre,
                    aciklama, tutarsizlik_uyarilari, AGIRLIK, BILESEN_ETIKET)
import seed

# --- Ölçülebilir etki VARSAYIMLARI (varsayım + yöntem + kaynak; şeffaf) ---
# Sistem sınırı: elyaf üretimi (virgin vs. geri kazanılan pamuk), kg bazında.
VARSAYIM = {
    # Not: virgin pamuğun su ayak izi kg başına ~10.000 L (tişört≈2.700 L/250g).
    # Konservatif birim tasarruflar (virgin pamuk vs mekanik geri kazanılan pamuk, lif
    # düzeyi). Metrikler bu katsayılardan CANLI hesaplanır — sabit sayı gömülmez.
    "su_L_per_kg":  2100.0,  # konservatif su tasarrufu (virgin pamuk ~10.000 L/kg fiber ref.)
    "co2_kg_per_kg": 1.6,    # konservatif (PE/Miljögiraff); ecoinvent üst sınırı ~2,93 kg/kg
}
ESLESME_ESIGI = 0.60


def en_iyi_eslesme(p, talepler):
    """Bir parti için en yüksek skorlu talebi bul (sert filtre + kademeli skor)."""
    en_iyi = None
    for t in talepler:
        ok, _ = sert_filtre(p, t)
        if not ok:
            continue
        s = skorla(p, t)
        skor = match_score(s["bilesen"])
        if en_iyi is None or skor > en_iyi[0]:
            en_iyi = (skor, t, s)
    return en_iyi


def dashboard_ozet(partiler, talepler):
    """Kamu dashboard metriklerini dict döndürür. build_app.py bunu gömer; parite
    testi JS hesaplaDashboard() çıktısını bu Python değerleriyle karşılaştırır →
    gerçek Python↔JS paritesi (veri değişince beklenen değerler otomatik güncellenir)."""
    eslesen_kg, skorlar = 0.0, []
    for p in partiler:
        e = en_iyi_eslesme(p, talepler)
        if e and e[0] >= ESLESME_ESIGI:
            eslesen_kg += p.miktar_kg
            skorlar.append(e[0])
    tutarsiz = sum(1 for p in partiler if tutarsizlik_uyarilari(p))
    n = len(skorlar)
    return {
        "eslesen": len(skorlar), "toplam": len(partiler),
        "ton": round(eslesen_kg / 1000.0, 1),
        "co2": round(eslesen_kg * VARSAYIM["co2_kg_per_kg"] / 1000.0),
        "su": round(eslesen_kg * VARSAYIM["su_L_per_kg"] / 1_000_000.0, 2),
        "ort_skor": round(sum(skorlar) / n * 100) if n else 0,
        "min": round(min(skorlar) * 100) if n else 0,
        "max": round(max(skorlar) * 100) if n else 0,
        "tutarsiz": tutarsiz,
    }


def main():
    partiler, talepler, fabrika_itibar = seed.uret()
    print("=" * 68)
    print("ReLoop — Açıklanabilir Eşleştirme Motoru · Demo (sentetik veri)")
    print("=" * 68)
    print(f"Fabrika: {len({p.fabrika for p in partiler})} | "
          f"Fire partisi (DMP): {len(partiler)} | Alıcı talebi: {len(talepler)}")

    # (1) DMP tutarsızlık kontrolü — ekilen gerçek tutarsızlıklar
    print("\n[1] DMP TUTARSIZLIK KONTROLÜ (otomatik uyarı örnekleri)")
    tutarsizlar = [(p, tutarsizlik_uyarilari(p)) for p in partiler]
    tutarsizlar = [(p, u) for p, u in tutarsizlar if u]
    print(f"  {len(tutarsizlar)}/{len(partiler)} partide uyarı bulundu (kasıtlı ekilmiş):")
    for p, u in tutarsizlar[:3]:
        print(f"  {p.id} ({p.kumas}, %{p.pamuk:.0f} pamuk, {p.gramaj} g/m²): {u[0]}")

    # (2) Bölüm 9 birebir örnek hesap
    print("\n[2] BÖLÜM 9 ÖRNEK HESABI (rapordaki senaryo)")
    ornek_p = Parti(id="P-DEMO", fabrika="Fabrika-Ornek", lat=38.680, lon=29.410,
                    sehir="Uşak", pamuk=100, polyester=0, elastan=0, kumas="suprem",
                    gramaj=180, en_m=1.8, miktar_kg=800, kalite="A", min_fiyat=18,
                    depo_gun=20, dogrulanmis=True, itibar=0.85)
    ornek_t = Talep(id="T-DEMO", alici="GeriDonusum-Ornek", lat=38.905, lon=29.410,
                    sehir="Uşak", min_pamuk=95, max_elastan=0, ihtiyac_kg=1000,
                    max_fiyat=22, min_kalite="B")
    s = skorla(ornek_p, ornek_t)
    skor = match_score(s["bilesen"])
    b, k = s["bilesen"], katki(s["bilesen"])
    print("  " + "  ".join(f"f_{ad}={b[ad]:.3f}" for ad in AGIRLIK))
    print("  " + "  ".join(f"{AGIRLIK[ad]:.2f}×{b[ad]:.2f}={k[ad]:.3f}" for ad in AGIRLIK))
    print(f"  => MatchScore = {skor:.3f}  ->  {aciklama(s, skor)}")

    # (3) Örnek eşleşmeler — 3 talep için en iyi parti
    print("\n[3] ÖRNEK EŞLEŞMELER (talep -> en uygun fire partisi)")
    for t in talepler[:3]:
        adaylar = []
        for p in partiler:
            ok, _ = sert_filtre(p, t)
            if ok:
                sc = skorla(p, t)
                adaylar.append((match_score(sc["bilesen"]), p, sc))
        adaylar.sort(key=lambda x: x[0], reverse=True)
        if adaylar:
            skor, p, sc = adaylar[0]
            print(f"  {t.id} (≥%{t.min_pamuk:.0f} pamuk, {t.ihtiyac_kg:.0f} kg, {t.sehir}) "
                  f"<- {p.id} [{p.fabrika}] : {aciklama(sc, skor)}  "
                  f"({len(adaylar)} uygun aday)")
        else:
            print(f"  {t.id}: uygun parti yok (filtreler elendi)")

    # (4) KAMU DASHBOARD METRİKLERİ
    eslesen_kg, skorlar, mesafeler = 0.0, [], []
    eslesen_sayi = 0
    for p in partiler:
        e = en_iyi_eslesme(p, talepler)
        if e and e[0] >= ESLESME_ESIGI:
            eslesen_sayi += 1
            eslesen_kg += p.miktar_kg
            skorlar.append(e[0])
            mesafeler.append(e[2]["mesafe_km"])
    ton = eslesen_kg / 1000.0
    co2 = eslesen_kg * VARSAYIM["co2_kg_per_kg"] / 1000.0   # ton CO2e
    su = eslesen_kg * VARSAYIM["su_L_per_kg"] / 1_000_000.0  # milyon L
    ort_skor = sum(skorlar)/len(skorlar) if skorlar else 0
    ort_mesafe = sum(mesafeler)/len(mesafeler) if mesafeler else 0
    basari = eslesen_sayi/len(partiler)*100

    print("\n[4] KAMU DASHBOARD (anonim/agrega — Bakanlık & OSB)")
    print(f"  Eşleşen parti           : {eslesen_sayi}/{len(partiler)}  (%{basari:.0f} eşleşme başarısı)")
    print(f"  Yönlendirilen malzeme   : {ton:,.1f} ton")
    print(f"  Tahmini CO2 azaltımı*   : {co2:,.1f} ton CO2e")
    print(f"  Tahmini su tasarrufu*   : {su:,.2f} milyon L")
    print(f"  Ortalama eşleşme skoru  : %{ort_skor*100:.0f}  (min {min(skorlar)*100:.0f} – max {max(skorlar)*100:.0f})")
    print(f"  Ortalama mesafe         : {ort_mesafe:.0f} km (bölge-içi → düşük lojistik)")
    print("  * VARSAYIM: co2=1,6 kg/kg (ecoinvent üst ~2,9), su=2100 L/kg; lif düzeyi. Metrikler katsayılardan canlı hesaplanır.")

    _dashboard_html(eslesen_sayi, len(partiler), ton, co2, su, ort_skor, ort_mesafe, basari,
                    min(skorlar), max(skorlar), len(tutarsizlar))
    print("\n  -> dashboard.html yazıldı (tam etkileşimli sürüm: reloop_app.html).")


def _dashboard_html(es, top, ton, co2, su, skor, mesafe, basari, mn, mx, tutarsiz):
    kart = lambda b, u: f'<div class="c"><div class="v">{b}</div><div class="u">{u}</div></div>'
    html = f"""<!doctype html><meta charset=utf-8><title>ReLoop Kamu Dashboard</title>
<style>body{{font-family:system-ui;background:#0b1f17;color:#eafff5;margin:0;padding:32px}}
h1{{font-size:22px}}.g{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:820px}}
.c{{background:#12352a;border:1px solid #1f5a44;border-radius:14px;padding:20px}}
.v{{font-size:30px;font-weight:700;color:#3ee6a0}}.u{{font-size:13px;opacity:.8;margin-top:6px}}
small{{opacity:.6}}</style>
<h1>ReLoop — Kamu &amp; OSB Dashboard <small>(demo · sentetik veri)</small></h1>
<div class=g>
{kart(f"{es}/{top}", f"Eşleşen parti (%{basari:.0f} başarı)")}
{kart(f"{ton:,.0f} ton", "Yönlendirilen malzeme")}
{kart(f"{co2:,.0f} ton", "Tahmini CO₂e azaltımı*")}
{kart(f"{su:,.1f} M L", "Tahmini su tasarrufu*")}
{kart(f"%{skor*100:.0f}", f"Ortalama skor (%{mn*100:.0f}–%{mx*100:.0f})")}
{kart(f"{mesafe:.0f} km", "Ortalama mesafe")}
</div>
<p><small>* VARSAYIM: CO₂ 1,6 kg/kg (ecoinvent üst ~2,9), su 2100 L/kg; lif düzeyi. Metrikler katsayılardan canlı hesaplanır.
&nbsp;·&nbsp;{tutarsiz} DMP tutarsızlık uyarısı yakalandı. Tam etkileşimli sürüm: reloop_app.html</small></p>
"""
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    main()
