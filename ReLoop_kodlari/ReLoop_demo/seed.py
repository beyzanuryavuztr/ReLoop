"""
ReLoop — Sentetik referans veritabanı ('yaşayan ekosistem' demosu).
Gizlilik gereği gerçek firma verisi yerine sentetik/temsili veri kullanılır.
Deterministiktir (random.seed) → her çalıştırmada aynı sonuç.

Tasarım:
  • Lif kompozisyonu kumaş ailesiyle TUTARLI üretilir (polar→polyester, denim/
    poplin/suprem/gabardin→pamuk ağırlıklı), gramaj kumaşın beklenen aralığında.
  • DMP tutarsızlık dedektörünü göstermek için partilerin ~%6'sına KASITLI,
    GERÇEK tutarsızlık ekilir (rasgele artefakt değil).
  • 80 fabrikanın hepsi aktiftir (her fabrikaya en az bir parti düşer).
"""
import random
from reloop import Parti, Talep, GRAMAJ_ARALIK

random.seed(42)

# Şehir -> (lat, lon)  [ULUSAL kapsam — üretim + geri dönüşüm merkezleri]
SEHIRLER = {
    "İstanbul":      (41.01, 28.98),
    "Tekirdağ":      (41.00, 27.51),   # Çorlu konfeksiyon kuşağı
    "Bursa":         (40.19, 29.06),
    "İzmir":         (38.42, 27.14),
    "Denizli":       (37.78, 29.09),
    "Uşak":          (38.68, 29.41),
    "Kayseri":       (38.73, 35.48),
    "Kahramanmaraş": (37.58, 36.93),
    "Gaziantep":     (37.07, 37.38),
    "Adana":         (37.00, 35.32),
}
# Fire ÜRETEN fabrikalar üretim kuşaklarında yoğun (Marmara/Ege + iplik illeri);
# geri dönüşüm merkezlerinde de üretim var → kümeler örtüşür, bölge-içi eşleşme olur.
SEHIR_AGIRLIK = (["Bursa"]*4 + ["İstanbul"]*3 + ["Denizli"]*3 + ["Uşak"]*3 +
                 ["İzmir"]*2 + ["Tekirdağ"]*2 + ["Gaziantep"]*2 +
                 ["Kahramanmaraş"]*1 + ["Adana"]*1 + ["Kayseri"]*1)
KUMASLAR = ["suprem", "denim", "poplin", "gabardin", "polar"]
KALITELER = ["A", "A", "B", "B", "C"]

# Kumaş ailesi -> tutarlı lif profili adayları (pamuk, polyester, elastan) %
LIF_PROFIL = {
    "suprem":   [(100, 0, 0), (100, 0, 0), (95, 0, 5), (80, 20, 0)],
    "denim":    [(100, 0, 0), (100, 0, 0), (98, 0, 2), (97, 0, 3)],
    "poplin":   [(100, 0, 0), (95, 5, 0), (90, 10, 0)],
    "gabardin": [(80, 20, 0), (70, 30, 0), (65, 35, 0)],
    "polar":    [(0, 100, 0), (0, 95, 5), (10, 90, 0)],
}

# Gerçekçi (ama tümüyle KURGUSAL) firma/alıcı isimleri. İsimler index'ten
# DETERMİNİSTİK türetilir; global RNG akışını TÜKETMEZ → eşleştirme değerleri ve
# dolayısıyla rapor sayıları birebir korunur.
FAB_MARKA = ["Ak", "Öz", "Ege", "Anadolu", "Menderes", "Gediz", "Şeker", "Yıldız",
             "Başak", "Ferah", "Aydın", "Selçuk", "Marmara", "Efe", "Toros", "Doğan",
             "Çınar", "Pınar", "Tuna", "Zümrüt"]
FAB_TUR = ["Tekstil", "Örme", "Dokuma", "İplik"]
REC_MARKA = ["Ege", "Anadolu", "Yeşil", "Döngü", "Terra", "Marmara", "Gediz", "Nil",
             "Toros", "Pamuktan", "Yeniden", "Lifsan", "Kar-Teks", "Eko", "Reça"]
REC_TUR = ["Geri Kazanım", "Geri Dönüşüm", "Tekstil Geri Kazanım", "Elyaf San."]


def fabrika_adi(i: int) -> str:
    """Benzersiz, gerçekçi tekstil firması adı (i: 1-tabanlı). RNG kullanmaz."""
    idx = i - 1
    marka = FAB_MARKA[idx % len(FAB_MARKA)]
    tur = FAB_TUR[(idx // len(FAB_MARKA)) % len(FAB_TUR)]
    kat = idx // (len(FAB_MARKA) * len(FAB_TUR))
    return f"{marka} {tur}" + (f" {kat + 1}" if kat else "")


def alici_adi(i: int) -> str:
    """Benzersiz geri dönüşümcü adı (i: 1-tabanlı). RNG kullanmaz."""
    idx = i - 1
    marka = REC_MARKA[idx % len(REC_MARKA)]
    tur = REC_TUR[(idx // len(REC_MARKA)) % len(REC_TUR)]
    kat = idx // (len(REC_MARKA) * len(REC_TUR))
    return f"{marka} {tur}" + (f" {kat + 1}" if kat else "")


# ---------------------------------------------------------------------------
# ALICI FİRMALAR — gerçek geri dönüşümcüler + temsili arketipler.
# DÜRÜSTLÜK: Gerçek firmaların ADI ve KAMUSAL ROLÜ gerçektir (web kaynaklı); kabul
# kriterleri sahip oldukları KAMUSAL sertifikadan (GRS/OEKO-TEX/ZDHC) TÜRETİLMİŞ
# temsili değerlerdir — özel sözleşme/anlaşma iddiası DEĞİLDİR. Arketipler açıkça
# '(temsili)' etiketlidir. Alanlar:
# (ad, ürün/rol, şehir, sertifikalar, izlenebilirlik?, min_lot_kg, elastan_tavan%,
#  min_pamuk%, min_kalite, dürüstlük-kaynak-etiketi)
FIRMALAR = [
    ("Haksa İplik", "GRS'li geri dönüşüm ipliği", "Uşak", ["GRS"], True, 500, 0, 90, "B",
     "Gerçek firma (Uşak, 2013'ten GRS'li); kriter GRS'ten türetildi"),
    ("Kayra Elyaf", "Shoddy elyaf geri dönüşümü", "Uşak", ["GRS"], True, 800, 2, 80, "C",
     "Gerçek firma (Uşak elyaf); kriter GRS'ten türetildi"),
    ("BTZ Tekstil", "Battaniye/geri dönüşüm ipliği", "Uşak", ["RCS"], False, 500, 0, 85, "B",
     "Gerçek firma (Uşak iplik); kriter standarttan türetildi"),
    ("Gaziantep Halı Keçe (temsili)", "Halı zemini keçe / harman iplik", "Gaziantep",
     ["GRS"], False, 1000, 2, 0, "C", "Temsili — Gaziantep halı OSB rolü + GRS"),
    ("Otomotiv Keçe Üreticisi (temsili)", "Nonwoven otomotiv keçesi", "Bursa",
     ["OEKO-TEX", "ZDHC"], True, 800, 0, 0, "B", "Temsili — Bursa otomotiv tedariki + OEKO-TEX/ZDHC"),
    ("Yalıtım Levha Üreticisi (temsili)", "Tekstil bazlı yalıtım levhası", "Kahramanmaraş",
     [], False, 600, 5, 0, "C", "Temsili — yalıtım geri kazanım"),
    ("İhracatçı Denim İpliği (temsili)", "GRS'li denim iplik", "Denizli",
     ["GRS", "OEKO-TEX"], True, 800, 0, 95, "A", "Temsili — Ege ihracatçı + GRS/OEKO-TEX"),
    ("Ev Tekstili Geri Kazanım (temsili)", "Ev tekstili elyaf", "Adana",
     ["RCS"], False, 500, 3, 80, "C", "Temsili — Çukurova iplik/ev tekstili"),
]


def _yerel_koordinat(sehir):
    lat, lon = SEHIRLER[sehir]
    return (round(lat + random.uniform(-0.15, 0.15), 4),
            round(lon + random.uniform(-0.15, 0.15), 4))


def _ekle_tutarsizlik(p: Parti):
    """Bir partiye tek, GERÇEK bir tutarsızlık ek (dedektör bunu yakalar)."""
    tur = random.choice(["gramaj", "lif_kumas", "toplam"])
    lo, hi = GRAMAJ_ARALIK[p.kumas]
    if tur == "gramaj":
        p.gramaj = hi + random.randint(40, 120)          # aralık dışı gramaj
    elif tur == "lif_kumas":
        if p.kumas == "polar":
            p.pamuk, p.polyester, p.elastan = 70, 30, 0   # polar ama pamuk baskın
        else:
            p.pamuk, p.polyester, p.elastan = 30, 70, 0   # pamuk kumaşı ama polyester
    else:
        p.polyester += 6                                  # toplam %100 değil
    return p


def uret(n_fabrika=80, n_parti=250, n_talep=60):
    random.seed(42)   # HER çağrıda RNG'yi sıfırla → reseed birebir aynı veri (determinizm)
    # --- Fabrikalar + itibar (geçmiş teslim başarı oranı, 0–1) ---
    fabrikalar = []               # (ad, sehir, itibar)
    fabrika_itibar = {}
    for i in range(1, n_fabrika + 1):
        sehir = random.choice(SEHIR_AGIRLIK)
        itibar = round(random.uniform(0.70, 0.98), 2)
        ad = fabrika_adi(i)
        fabrikalar.append((ad, sehir, itibar))
        fabrika_itibar[ad] = itibar

    # Her fabrikaya en az bir parti düşsün (80 fabrikanın hepsi aktif) →
    # ilk n_fabrika parti fabrikalara birebir, kalanı ağırlıklı rasgele.
    parti_fabrika_sirasi = list(fabrikalar)
    while len(parti_fabrika_sirasi) < n_parti:
        parti_fabrika_sirasi.append(random.choice(fabrikalar))
    random.shuffle(parti_fabrika_sirasi)

    # --- Fire partileri (DMP) ---
    partiler = []
    for i in range(1, n_parti + 1):
        ad, sehir, itibar = parti_fabrika_sirasi[i - 1]
        lat, lon = _yerel_koordinat(sehir)
        kumas = random.choice(KUMASLAR)
        pamuk, poly, elas = random.choice(LIF_PROFIL[kumas])
        lo, hi = GRAMAJ_ARALIK[kumas]
        partiler.append(Parti(
            id=f"P{i:04d}", fabrika=ad, lat=lat, lon=lon, sehir=sehir,
            pamuk=float(pamuk), polyester=float(poly), elastan=float(elas),
            kumas=kumas, gramaj=random.randint(lo, hi),
            en_m=round(random.uniform(1.4, 2.2), 1),
            miktar_kg=float(random.choice([120, 250, 400, 600, 800, 1200, 1800])),
            kalite=random.choice(KALITELER),
            min_fiyat=float(random.randint(14, 26)),
            depo_gun=random.randint(1, 90),
            dogrulanmis=random.random() < 0.30,
            itibar=itibar,
        ))

    # --- Kasıtlı, gerçek tutarsızlık ekimi (~%6) ---
    n_tutarsiz = max(1, round(n_parti * 0.06))
    for idx in random.sample(range(n_parti), n_tutarsiz):
        _ekle_tutarsizlik(partiler[idx])

    # --- Alıcı talepleri (gerçek + temsili geri dönüşümcü firmalar) ---
    # Her talep bir FİRMAYA bağlıdır; kabul kriterleri firmanın standardından gelir
    # (çift mevzuat motorunun 'firma katmanı' bu alanları kullanır).
    talepler = []
    for i in range(1, n_talep + 1):
        (fad, ftur, fsehir, fcert, fizl, flot, felas, fpamuk, fkal, fkaynak) = \
            FIRMALAR[(i - 1) % len(FIRMALAR)]
        lat, lon = _yerel_koordinat(fsehir)
        talepler.append(Talep(
            id=f"T{i:03d}", alici=fad, lat=lat, lon=lon, sehir=fsehir,
            min_pamuk=float(fpamuk),
            max_elastan=float(felas),
            ihtiyac_kg=float(random.choice([500, 800, 1000, 1500, 2000])),
            max_fiyat=float(random.randint(20, 30)),
            min_kalite=fkal,
            dogrulanmis_ister=fizl,
            firma_adi=fad, firma_tur=ftur, sertifika_ister=list(fcert),
            izlenebilirlik_ister=fizl, min_lot_kg=float(flot), kaynak=fkaynak,
        ))

    return partiler, talepler, fabrika_itibar
