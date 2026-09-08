"""
Yarı-gerçek seed — ikinci bağımsız test koşusu (rapor md.5.2/10.7).

'Yarı-gerçek' ne demek (dürüst tanım):
  • COĞRAFYA gerçek: Türkiye'nin gerçek tekstil merkezleri ve gerçek koordinatları
    (Uşak: tekstil geri dönüşüm başkenti; Denizli: ev tekstili; Bursa: sentetik/dokuma;
     Gaziantep: iplik/makine halısı; Kahramanmaraş: iplik; Çorlu-Tekirdağ: boya-apre).
  • DAĞILIMLAR gerçekçi: pre-consumer fire ağırlıklı (Altun 2012: TR tekstil atığının
    ~%52'si pre-consumer), kumaş-lif tutarlılığı, sektörel gramaj aralıkları.
  • KURUMLAR sentetik (KVKK): firma adları kurgusal ama gerçekçi, açıkça etiketli.

Kanonik `seed.py`'den AYRIDIR ve onu değiştirmez; kanonik anlık görüntü
(110/250 · %44 · 80,6 ton) bozulmaz. Bu, daha büyük ve gerçek-coğrafyalı bir ikinci doğrulamadır.
Deterministiktir (seed=2026).
"""
from __future__ import annotations
import random

from ._enginepath import ensure_engine_on_path

ensure_engine_on_path()
from reloop import Parti, Talep, GRAMAJ_ARALIK  # type: ignore  # noqa: E402

# Gerçek tekstil merkezleri: (lat, lon, rol-ağırlığı üretici, rol-ağırlığı geri dönüşümcü)
HUBS = {
    "Uşak":          (38.6742, 29.4058, 5, 6),   # geri dönüşüm başkenti → alıcı ağırlıklı
    "Denizli":       (37.7830, 29.0960, 4, 2),   # ev tekstili
    "Bursa":         (40.1960, 29.0610, 3, 2),   # sentetik/dokuma
    "Gaziantep":     (37.1000, 37.3500, 3, 1),   # iplik/makine halısı
    "Kahramanmaraş": (37.6200, 36.9000, 2, 1),   # iplik
    "Çorlu":         (41.1594, 27.8028, 3, 1),   # boya-apre (Tekirdağ)
}
KUMASLAR = ["suprem", "denim", "poplin", "gabardin", "polar"]
KALITELER = ["A", "A", "B", "B", "C"]

# Kumaş → tutarlı lif profili (pamuk, polyester, elastan) %
LIF_PROFIL = {
    "suprem":   [(100, 0, 0), (100, 0, 0), (95, 0, 5), (80, 20, 0)],
    "denim":    [(100, 0, 0), (100, 0, 0), (98, 0, 2), (97, 0, 3)],
    "poplin":   [(100, 0, 0), (95, 5, 0), (90, 10, 0)],
    "gabardin": [(80, 20, 0), (70, 30, 0), (65, 35, 0)],
    "polar":    [(0, 100, 0), (0, 95, 5), (10, 90, 0)],
}

FAB_MARKA = ["Ak", "Öz", "Ege", "Anadolu", "Menderes", "Gediz", "Şeker", "Yıldız",
             "Başak", "Ferah", "Aydın", "Selçuk", "Marmara", "Efe", "Toros", "Doğan",
             "Çınar", "Pınar", "Tuna", "Zümrüt", "Barış", "Umut", "Berrak", "Kaya"]
FAB_TUR = ["Tekstil", "Örme", "Dokuma", "İplik", "Konfeksiyon"]
REC_MARKA = ["Ege", "Anadolu", "Yeşil", "Döngü", "Terra", "Marmara", "Gediz", "Nil",
             "Toros", "Pamuktan", "Yeniden", "Lifsan", "Kar-Teks", "Eko", "Reça", "Devir"]
REC_TUR = ["Geri Kazanım", "Geri Dönüşüm", "Tekstil Geri Kazanım", "Elyaf San."]


def _ad(marka_list, tur_list, i):
    idx = i - 1
    marka = marka_list[idx % len(marka_list)]
    tur = tur_list[(idx // len(marka_list)) % len(tur_list)]
    kat = idx // (len(marka_list) * len(tur_list))
    return f"{marka} {tur}" + (f" {kat + 1}" if kat else "")


def _coord(hub, rng):
    lat, lon, *_ = HUBS[hub]
    return (round(lat + rng.uniform(-0.08, 0.08), 4),
            round(lon + rng.uniform(-0.08, 0.08), 4))


def _hub_dagilim(key_index):
    """Gerçekçi hub ağırlıkları (üretici veya alıcı)."""
    bag = []
    for h, (_, _, wp, wr) in HUBS.items():
        bag += [h] * (wp if key_index == 0 else wr)
    return bag


def uret(n_fabrika=120, n_parti=400, n_talep=90, seed=2026):
    rng = random.Random(seed)
    uretici_hublari = _hub_dagilim(0)
    alici_hublari = _hub_dagilim(1)

    # Üretici fabrikalar + itibar
    fabrikalar = []
    for i in range(1, n_fabrika + 1):
        hub = rng.choice(uretici_hublari)
        itibar = round(rng.uniform(0.70, 0.98), 2)
        fabrikalar.append((_ad(FAB_MARKA, FAB_TUR, i), hub, itibar))

    sirali = list(fabrikalar)
    while len(sirali) < n_parti:
        sirali.append(rng.choice(fabrikalar))
    rng.shuffle(sirali)

    partiler = []
    for i in range(1, n_parti + 1):
        ad, hub, itibar = sirali[i - 1]
        lat, lon = _coord(hub, rng)
        kumas = rng.choice(KUMASLAR)
        pamuk, poly, elas = rng.choice(LIF_PROFIL[kumas])
        lo, hi = GRAMAJ_ARALIK[kumas]
        # Pre-consumer ağırlıklı: fire miktarı orta-küçük partiler yoğun (log benzeri)
        miktar = rng.choice([120, 180, 250, 250, 400, 400, 600, 800, 1200, 1800])
        kalite = rng.choice(KALITELER)
        dogrulanmis = rng.random() < 0.32
        # GERÇEKÇİ FİYAT (yarı-gerçek): pamuk saflığı primi + kalite + doğrulama primi
        # − kontaminant (elastan) iskontosu + küçük gürültü. Hedonik model bunu öğrenir.
        kal_ord = {"A": 2, "B": 1, "C": 0}[kalite]
        fiyat = (11.0 + 9.0 * (pamuk / 100.0) + 2.5 * kal_ord
                 + 2.0 * (1 if dogrulanmis else 0) - 0.5 * elas
                 + rng.uniform(-1.5, 1.5))
        fiyat = round(min(30.0, max(12.0, fiyat)), 1)
        partiler.append(Parti(
            id=f"P{i:04d}", fabrika=ad, lat=lat, lon=lon, sehir=hub,
            pamuk=float(pamuk), polyester=float(poly), elastan=float(elas),
            kumas=kumas, gramaj=rng.randint(lo, hi),
            en_m=round(rng.uniform(1.4, 2.2), 1), miktar_kg=float(miktar),
            kalite=kalite, min_fiyat=fiyat,
            depo_gun=rng.randint(1, 90), dogrulanmis=dogrulanmis,
            itibar=itibar,
        ))

    # ~%6 kasıtlı, gerçek tutarsızlık (dedektör bunu yakalar)
    n_tutarsiz = max(1, round(n_parti * 0.06))
    for idx in rng.sample(range(n_parti), n_tutarsiz):
        p = partiler[idx]
        lo, hi = GRAMAJ_ARALIK[p.kumas]
        secim = rng.choice(["gramaj", "lif", "toplam"])
        if secim == "gramaj":
            p.gramaj = hi + rng.randint(40, 120)
        elif secim == "lif":
            if p.kumas == "polar":
                p.pamuk, p.polyester, p.elastan = 70, 30, 0
            else:
                p.pamuk, p.polyester, p.elastan = 30, 70, 0
        else:
            p.polyester += 6

    talepler = []
    for i in range(1, n_talep + 1):
        hub = rng.choice(alici_hublari)
        lat, lon = _coord(hub, rng)
        talepler.append(Talep(
            id=f"T{i:03d}", alici=_ad(REC_MARKA, REC_TUR, i), lat=lat, lon=lon, sehir=hub,
            min_pamuk=float(rng.choice([80, 90, 95])), max_elastan=0.0,
            ihtiyac_kg=float(rng.choice([500, 800, 1000, 1500, 2000])),
            max_fiyat=float(rng.randint(20, 30)),
            min_kalite=rng.choice(["B", "B", "C"]),
            dogrulanmis_ister=rng.random() < 0.30,
        ))

    itibarlar = {ad: it for ad, _, it in fabrikalar}
    return partiler, talepler, itibarlar
