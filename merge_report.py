# -*- coding: utf-8 -*-
"""ReLoop raporu birleştirme: base (benim §1/§5-§8/§13/§15 + görseller) üzerine
Revize §2/§3/§4/§9/§10/§11/§12/§14 yerleştir; numara uyumla; kaynakça [1]-[26]."""
import re, copy, io
import docx
from docx import Document
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Inches, Pt

BASE = "/home/claude/beyza geçici klasör/ReLoop_On_Degerlendirme_Raporu.docx"
REV  = "/home/claude/beyza geçici klasör/ReLoop_Rapor_Revize_Bolumler.docx"
OUT  = "/home/claude/beyza geçici klasör/ReLoop_On_Degerlendirme_Raporu.docx"

base = Document(BASE)
rev  = Document(REV)
W = qn('w:p'); TBL = qn('w:tbl'); T = qn('w:t')

def para_text(el):
    return "".join((t.text or "") for t in el.iter(T)) if el.tag==W else None

def is_head_base(el):
    t = para_text(el)
    if not t: return None
    m = re.match(r'^\s*(\d{1,2})\.\s+(.*)$', t.strip())
    if not m: return None
    rest = m.group(2).strip()
    if rest and rest == rest.upper():   # base başlıkları BÜYÜK HARF
        return int(m.group(1))
    return None

def is_head_rev(el):
    t = para_text(el)
    if not t: return None
    m = re.match(r'^\s*(\d{1,2})\.\s+', t.strip())
    if m and 'puan' in t.lower():
        return int(m.group(1))
    return None

def body_children(doc):
    return [c for c in doc.element.body.iterchildren() if c.tag in (W, TBL)]

def remap_images(el, src_part, dst_part):
    for blip in el.iter(qn('a:blip')):
        old = blip.get(qn('r:embed'))
        if old:
            src_img = src_part.related_parts[old]
            new_img = dst_part.package.image_parts.get_or_add_image_part(io.BytesIO(src_img.blob))
            blip.set(qn('r:embed'), dst_part.relate_to(new_img, RT.IMAGE))

def renumber(el, mapping):
    """el içindeki tüm w:t düğümlerinde 'Şekil N'/'Tablo N' token'larını haritaya göre değiştir."""
    if not mapping: return
    pat = re.compile(r'(Şekil|Tablo)\s+(\d+)')
    for t in el.iter(T):
        if t.text and ('Şekil' in t.text or 'Tablo' in t.text):
            t.text = pat.sub(lambda m: mapping.get(m.group(0), m.group(0)), t.text)

def find_head_el(doc, secnum, detector):
    for el in body_children(doc):
        if el.tag==W and detector(el)==secnum:
            return el
    return None

def next_head_el(doc, after_el, detector):
    el = after_el.getnext()
    while el is not None:
        if el.tag==W and detector(el) is not None:
            return el
        el = el.getnext()
    return None  # son bölüm

# --- Revize bölüm içeriğini (başlık HARİÇ) al ---
def rev_section_content(secnum):
    h = find_head_el(rev, secnum, is_head_rev)
    end = next_head_el(rev, h, is_head_rev)
    out=[]
    el = h.getnext()
    while el is not None and el is not end:
        # rev'in kendi kaynakça/başlık dışı içeriği
        out.append(el)
        el = el.getnext()
    return out

RENUM = {
    10: {'Şekil 1':'Şekil 6','Tablo 2':'Tablo 3','Tablo 3':'Tablo 4'},
    12: {'Şekil 2':'Şekil 7','Tablo 5':'Tablo 6'},
    14: {'Şekil 3':'Şekil 8','Tablo 6':'Tablo 8'},
    11: {'Tablo 4':'Tablo 5'},
}
REV_SECS = [2,3,4,9,10,11,12,14]

# --- base'de her Revize bölümünün İÇERİĞİNİ (başlıktan sonra) rev ile değiştir ---
for sec in REV_SECS:
    bh = find_head_el(base, sec, is_head_base)
    if bh is None: raise SystemExit(f"base'de §{sec} başlığı bulunamadı")
    bend = next_head_el(base, bh, is_head_base)   # §15 dahil bir sonraki başlık
    # base içerik elemanlarını sil (başlıktan sonra, sonraki başlığa kadar)
    el = bh.getnext(); rm=[]
    while el is not None and el is not bend:
        rm.append(el); el = el.getnext()
    for e in rm: base.element.body.remove(e)
    # rev içeriğini kopyala, remap, renumber, ekle (bend'den önce; bend yoksa sona)
    revels = rev_section_content(sec)
    mp = RENUM.get(sec)
    anchor = bend
    copies=[]
    for e in revels:
        ne = copy.deepcopy(e)
        remap_images(ne, rev.part, base.part)
        renumber(ne, mp)
        copies.append(ne)
    for ne in copies:
        if anchor is not None: anchor.addprevious(ne)
        else: base.element.body.append(ne)

# --- base'de tutulan bölümlerde hedefli düzeltmeler ---
def fix_in_section(secnum, repls):
    bh = find_head_el(base, secnum, is_head_base)
    bend = next_head_el(base, bh, is_head_base)
    el = bh
    while el is not None and el is not bend:
        for t in el.iter(T):
            if t.text:
                for a,b in repls: t.text = t.text.replace(a,b)
        el = el.getnext()
# §5,§7: [13]Du -> [16]
fix_in_section(5, [('[13]','[16]')])
fix_in_section(7, [('[13]','[16]')])
# §13 takım tablosu Tablo 4 -> Tablo 7
fix_in_section(13, [('Tablo 4','Tablo 7')])

# --- §15 (EK AÇIKLAMALAR) + kaynakça: lisans Tablo 6 -> Tablo 9; [1]-[12] -> [1]-[26] ---
BIB = {
 1:"Ellen MacArthur Foundation (2017). A New Textiles Economy: Redesigning Fashion's Future. Cowes: EMF.",
 2:"Chapagain, A. K., Hoekstra, A. Y., Savenije, H. H. G. & Gautam, R. (2006). The Water Footprint of Cotton Consumption. Ecological Economics, 60(2), 186–203.",
 3:"Anadolu Ajansı. Uşak'ta tekstil atıklarından geri dönüşümle 62 ülkeye ihracat (sektör beyanı, ~1.700 ton/gün).",
 4:"Ege İhracatçı Birlikleri. Türkiye'nin geri dönüşüm merkezi Uşak. Alternatif kapasite figürü (~2.716 ton/gün); rakam aralığının teyidi için.",
 5:"Avrupa Komisyonu (2025). Ecodesign for Sustainable Products and Energy Labelling Working Plan 2025–2030 [COM(2025) 187].",
 6:"Reverse Resources (Estonya, 2014). Pre-consumer tekstil atığı izleme ve eşleştirme platformu. Bağımsız kaynaklar: e-Estonia (2021); H&M Foundation (2026).",
 7:"Swatchloop (Türkiye, İzmir, 2022). Yapay zekâ destekli tekstil atığı yönetimi ve dijital ürün pasaportu. Bağımsız kaynaklar: Textilegence (2025); Webrazzi (2024).",
 8:"Atık Yönetimi Yönetmeliği (Resmî Gazete, 2 Nisan 2015, Sayı 29314). Tekstil üretim firesi (atık kodu 04 02 21 / 04 02 22) tehlikesiz atık sınıfındadır.",
 9:"Sıfır Atık Yönetmeliği (Resmî Gazete, 12 Temmuz 2019, Sayı 30829).",
 10:"T.C. Çevre, Şehircilik ve İklim Değişikliği Bakanlığı — Entegre Çevre Bilgi Sistemi (EÇBS). TABS, EÇBS altındaki atık beyan modülüdür.",
 11:"Akerlof, G. A. (1970). The Market for 'Lemons': Quality Uncertainty and the Market Mechanism. The Quarterly Journal of Economics, 84(3), 488–500.",
 12:"Sandin, G. & Peters, G. M. (2018). Environmental impact of textile reuse and recycling – A review. Journal of Cleaner Production, 184, 353–365.",
 13:"Altun, Ş. (2012). Prediction of Textile Waste Profile and Recycling Opportunities in Turkey. Fibres & Textiles in Eastern Europe, 20(5/94), 16–20.",
 14:"Berg, H. & Wilts, H. (2019). Digital platforms as market places for the circular economy. Sustainability Management Forum, 27(1), 1–9.",
 15:"Wilson, D. C., Velis, C. & Cheeseman, C. (2006). Role of informal sector recycling in waste management in developing countries. Habitat International, 30(4), 797–808.",
 16:"Du, W. vd. (2022). Efficient recognition and automatic sorting of waste textiles based on online near-infrared spectroscopy and convolutional neural network. Resources, Conservation and Recycling, 180, 106157.",
 17:"Fibersort Project (Interreg North-West Europe / Circle Economy) (2016–2020). Final Case Studies Report.",
 18:"circular.fashion / circularity.ID (Berlin, 2018–). EcoDesign Circle profili ve circularity.ID White Paper (2021).",
 19:"Miljögiraff (2016). LCA of Recycling Cotton (mechanically), Report No. 75. H&M için hazırlanmıştır.",
 20:"Textile Exchange / Sphera (2025). Life Cycle Assessment for Cotton — Technical Report.",
 21:"Chertow, M. R. (2000). Industrial Symbiosis: Literature and Taxonomy. Annual Review of Energy and the Environment, 25, 313–337.",
 22:"Mirata, M. (2004). Experiences from early stages of a national industrial symbiosis programme in the UK. Journal of Cleaner Production, 12(8–10), 967–983.",
 23:"Dolgen, D. & Alpaslan, M. N. (2020). Eco-Industrial Parks: Experiences from Turkey. Global Journal of Ecology, 5(1), 30–32.",
 24:"OSBÜK (Organize Sanayi Bölgeleri Üst Kuruluşu) / Anadolu Ajansı (Ocak 2026). Türkiye'de OSB sayısı 416'ya ulaştı.",
 25:"Sosyal Güvenlik Kurumu (SGK) tescilli işyeri verisi (Mart 2025); Textilegence aktarımı.",
 26:"Türkiye İhracatçılar Meclisi (TİM) / İHKİB (2024). Tekstil ve hazır giyim ihracatı istatistikleri.",
}
# lisans tablosu numarası
fix_in_section(15, [('Tablo 6','Tablo 9')])

# kaynakça giriş paragraflarını bul ([N] ile başlayanlar) ve yenile
body = base.element.body
entry_ps = [el for el in body_children(base)
            if el.tag==W and re.match(r'^\s*\[\d+\]\s', para_text(el) or "")]
if not entry_ps:
    raise SystemExit("kaynakça giriş paragrafı bulunamadı")
first = entry_ps[0]
# şablon biçimi ilk girişten alınacak; sil ve yeniden kur
anchor = first
# yeni girişleri first'ten önce ekle, sonra eski girişleri sil
from docx.text.paragraph import Paragraph
for n in range(1, 27):
    p = base.add_paragraph()  # sona eklenir, sonra taşınacak
    pel = p._p
    pf = p.paragraph_format
    pf.left_indent = Inches(0.3); pf.first_line_indent = Inches(-0.3)
    r0 = p.add_run(f"[{n}] "); r0.bold=True; r0.font.size=Pt(10.5)
    r1 = p.add_run(BIB[n]); r1.font.size=Pt(10.5)
    first.addprevious(pel)   # taşı
for el in entry_ps:
    body.remove(el)

base.save(OUT)
print("BİRLEŞTİRME TAMAM ->", OUT)
