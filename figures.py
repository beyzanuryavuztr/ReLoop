"""ReLoop — Rapor görselleri (şema + demo grafiği). Çıktı: figures/*.png"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import seed
from reloop import sert_filtre, skorla, match_score

os.makedirs("figures", exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})

# Kurumsal, ölçülü palet (yeşil/teal + nötr)
KOYU   = "#12352a"
ORTA   = "#1f5a44"
ACCENT = "#2f7d5b"
ACIK   = "#e9f2ee"
GRI    = "#5b6b66"


def kutu(ax, x, y, w, h, baslik, alt="", fc=ACIK, ec=ORTA, tc=KOYU):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=fc, ec=ec, lw=1.6))
    ax.text(x + w/2, y + h*(0.62 if alt else 0.5), baslik, ha="center", va="center",
            fontsize=11.5, fontweight="bold", color=tc)
    if alt:
        ax.text(x + w/2, y + h*0.30, alt, ha="center", va="center", fontsize=9, color=GRI)


# ---------------------------------------------------------------- Şekil 1: Mimari
def sekil1():
    fig, ax = plt.subplots(figsize=(9.2, 6.6)); ax.axis("off")
    ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    katmanlar = [
        ("SUNUM KATMANI", "Web / PWA  ·  WhatsApp Business API", 8.4),
        ("API KATMANI (REST)", "Kimlik doğrulama · JSON/CSV · açık standart (REST/OGC)", 7.0),
        ("ÇEKİRDEK SERVİSLER", "DMP  ·  Eşleştirme  ·  Güven & İşlem  ·  Kamu-Veri", 5.6),
        ("YAPAY ZEKÂ ÇALIŞMA ZAMANI", "Görüntü İşleme · OCR · Skorlama  (edge / yurt içi — md.10.5)", 4.2),
        ("VERİ KATMANI", "PostgreSQL (ilişkisel + JSONB pasaport) · nesne deposu · kuyruk", 2.8),
    ]
    for i, (b, a, y) in enumerate(katmanlar):
        fc = ACIK if i else "#d7e8e0"
        kutu(ax, 1.2, y, 7.6, 1.1, b, a, fc=fc)
    # Entegrasyon şeridi (sağ) — Kamu
    ax.add_patch(FancyBboxPatch((8.95, 2.8), 0.85, 6.7, boxstyle="round,pad=0.02,rounding_size=0.06",
                                fc=ORTA, ec=KOYU, lw=1.6))
    ax.text(9.375, 6.15, "KAMU  ·  UÇBS / TABS", rotation=90, ha="center", va="center",
            fontsize=11, fontweight="bold", color="white")
    # Kamu çıktı kutusu
    kutu(ax, 1.2, 1.15, 7.6, 1.0, "KAMU & OSB DASHBOARD", "Anonim/agrega: ton · CO₂ · eşleşme süresi", fc="#d7e8e0")
    ax.add_patch(FancyArrowPatch((5.0, 2.8), (5.0, 2.18), arrowstyle="->",
                                 mutation_scale=14, color=ACCENT, lw=1.6))
    ax.text(5.0, 9.65, "Şekil 1. ReLoop katmanlı sistem mimarisi", ha="center",
            fontsize=12.5, fontweight="bold", color=KOYU)
    fig.savefig("figures/sekil1_mimari.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Şekil 2: İş akışı
def sekil2():
    fig, ax = plt.subplots(figsize=(13, 3.4)); ax.axis("off")
    ax.set_xlim(0, 21); ax.set_ylim(0, 5)
    adimlar = [
        ("1. FİRE → DMP", "fotoğraf + beyan"),
        ("2. EŞLEŞTİRME", "filtre + skor"),
        ("3. TEKLİF (blind)", "kimlik gizli"),
        ("4. KABUL", "escrow"),
        ("5. TESLİM", "onay + puan"),
        ("6. KAMU VERİSİ", "UÇBS / TABS"),
    ]
    w, gap = 3.0, 0.5; x = 0.3
    for i, (b, a) in enumerate(adimlar):
        ax.add_patch(FancyBboxPatch((x, 1.6), w, 1.8, boxstyle="round,pad=0.02,rounding_size=0.05",
                                    fc=ACIK if i % 2 == 0 else "#d7e8e0", ec=ORTA, lw=1.6))
        ax.text(x+w/2, 2.78, b, ha="center", va="center", fontsize=10, fontweight="bold", color=KOYU)
        ax.text(x+w/2, 2.15, a, ha="center", va="center", fontsize=8.5, color=GRI)
        if i < len(adimlar) - 1:
            ax.add_patch(FancyArrowPatch((x+w+0.03, 2.5), (x+w+gap-0.03, 2.5), arrowstyle="-|>",
                                         mutation_scale=15, color=ACCENT, lw=2))
        x += w + gap
    ax.text(10.5, 4.55, "Şekil 2. Uçtan uca kullanıcı ve veri akışı", ha="center",
            fontsize=12.5, fontweight="bold", color=KOYU)
    fig.savefig("figures/sekil2_akis.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- Şekil 3: Demo skor dağılımı
def sekil3():
    partiler, talepler, _ = seed.uret()
    skorlar = []
    for p in partiler:
        en = None
        for t in talepler:
            ok, _ = sert_filtre(p, t)
            if ok:
                sk = match_score(skorla(p, t)["bilesen"])
                en = sk if en is None or sk > en else en
        if en is not None and en >= 0.60:
            skorlar.append(en * 100)
    ort = sum(skorlar) / len(skorlar)
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    ax.hist(skorlar, bins=12, color=ACCENT, edgecolor="white")
    ax.axvline(ort, color=KOYU, ls="--", lw=2, label=f"Ortalama = %{ort:.0f}")
    ax.set_xlabel("En iyi eşleşme skoru (%)"); ax.set_ylabel("Fire partisi sayısı")
    ax.set_title(f"Şekil 3. Eşleşme skoru dağılımı (n={len(skorlar)} eşleşen parti, sentetik veri)",
                 fontsize=11.5, fontweight="bold", color=KOYU)
    ax.legend(frameon=False); ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    fig.savefig("figures/sekil3_demo.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return len(skorlar), ort


if __name__ == "__main__":
    sekil1(); sekil2(); n, ort = sekil3()
    print(f"Şekiller üretildi. Skor dağılımı: n={n}, ort=%{ort:.0f}")
