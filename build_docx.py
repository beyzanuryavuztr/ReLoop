# -*- coding: utf-8 -*-
"""ReLoop — Ön Değerlendirme Raporu'nu profesyonel .docx olarak üretir."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

KOYU = RGBColor(0x12, 0x35, 0x2A)
FIGDIR = "figures"
OUT = "../ReLoop_On_Degerlendirme_Raporu.docx"

doc = Document()

# --- Temel biçim: Times New Roman 12, iki yana yaslı, 1.15 satır ---
normal = doc.styles["Normal"]
normal.font.name = "Times New Roman"
normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
pf = normal.paragraph_format
pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
pf.line_spacing = 1.15
pf.space_after = Pt(8)

for i in range(1, 4):
    h = doc.styles[f"Heading {i}"]
    h.font.name = "Times New Roman"
    h.font.color.rgb = KOYU
    h.font.size = Pt(15 - i)


def p(text, italic=False, align=None, size=None):
    par = doc.add_paragraph()
    run = par.add_run(text)
    run.italic = italic
    if size:
        run.font.size = Pt(size)
    if align == "c":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return par


def h(text, level=1):
    doc.add_heading(text, level=level)


def figure(fname, width, caption):
    doc.add_picture(os.path.join(FIGDIR, fname), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption); r.italic = True; r.font.size = Pt(10)


def table(headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, hd in enumerate(headers):
        c = t.rows[0].cells[j]
        c.paragraphs[0].add_run(hd).bold = True
        c.paragraphs[0].runs[0].font.size = Pt(11)
    for row in rows:
        cells = t.add_row().cells
        for j, val in enumerate(row):
            cells[j].text = ""
            rr = cells[j].paragraphs[0].add_run(val)
            rr.font.size = Pt(10.5)
    if widths:
        for row in t.rows:
            for j, w in enumerate(widths):
                row.cells[j].width = Inches(w)
    doc.add_paragraph()
    return t


# ====================== KAPAK ======================
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = title.add_run("ReLoop")
tr.bold = True; tr.font.size = Pt(30); tr.font.color.rgb = KOYU
p("Yapay Zekâ Destekli Dijital Malzeme Pasaportu ve Döngüsel Eşleştirme Platformu",
  italic=True, align="c", size=13)
p("TEKNOFEST 2026 · Sıfır Atık ve Döngüsel Ekonomi Yarışması", align="c", size=12)
p("Tema 3.2: Endüstriyel Atık Yönetimi ve Yeniden Kullanım", align="c", size=12)
p("Proje Ön Değerlendirme Raporu", align="c", size=12)
p("Takım: [Takım Adı]", align="c", size=12)
doc.add_paragraph()

# Versiyonlar
h("VERSİYONLAR")
table(["Versiyon", "Tarih", "Tanım", "Değişiklikler"],
      [["1.0", "12.08.2026", "İlk sürüm: TEKNOFEST 2026 Ön Değerlendirme Raporu", "İlk yayım"]],
      widths=[1.0, 1.2, 2.6, 1.7])
doc.add_page_break()

# ====================== 1. ÖZET ======================
h("1. PROJENİN KISA ÖZETİ (10 PUAN)")
p("Türkiye, dünya tekstil üretiminin önde gelen ülkelerinden biridir. Bu kapasitenin yan ürünü olan "
  "üretim (pre-consumer) firesi, temiz ve homojen yapısı ile bilinen bileşimi sayesinde en kolay geri "
  "kazanılabilir atık sınıfını oluşturur. Buna rağmen fire, büyük ölçüde enformel kanallarla ve "
  "değerinin altında elden çıkar. Bu tablonun ardında bir arz ve talep sorunu değil, üretici ile geri "
  "dönüşümcü arasındaki bilgi asimetrisi vardır: taraflar mevcuttur, eksik olan onları buluşturan "
  "güvenilir eşleşme bilgisidir.")
p("ReLoop, bu asimetriyi gidermek ve kamu sistemlerine entegre olmak üzere tasarlanan bir "
  "endüstriyel döngüsellik platformudur. Platform, her fire partisi için otomatik bir Dijital "
  "Malzeme Pasaportu üretir. Bileşim, kalite ve konum verisini kullanan açıklanabilir bir motor, "
  "üreticiyi en uygun geri dönüşümcüyle eşleştirir ve bunun gerekçesini kullanıcıya gösterir. "
  "Rekabet mahremiyetini koruyan kör (blind) eşleştirme, WhatsApp tabanlı saha erişimi ve katmanlı "
  "güven mekanizmaları ise çözümü sahada uygulanabilir kılacaktır. İşlem verisinin, anonim ve "
  "toplulaştırılmış biçimde Bakanlığın çevre bilgi sistemlerine aktarılması hedeflenir.")
p("Projenin çekirdek bileşeni bugün çalışır durumdadır. Eşleştirme motoru; seksen fabrika ve "
  "iki yüz elli fire partisinden oluşan sentetik bir veri tabanı üzerinde bu partilerin yüz "
  "on dokuzunu eşleştirerek uçtan uca akışın işlediğini göstermiştir (bulguların yorumu Bölüm "
  "7'de ele alınır). Çözüm, arz ve talebin aynı bölgede yoğunlaştığı Uşak pilotuyla başlayacak, "
  "sektörden bağımsız mimarisi sayesinde ulusal ölçeğe ve farklı endüstrilere genişleyecektir. "
  "Nihai değer üç taraflıdır: üreticiye daha yüksek fiyat ve hız, geri dönüşümcüye doğrulanmış ve "
  "sürekli hammadde, kamuya ölçülebilir atık verisi.")

# ====================== 2. PROBLEM ======================
h("2. ÇÖZÜLMESİ HEDEFLENEN PROBLEM (10 PUAN)")
p("Türkiye'nin tekstil üretimindeki güçlü konumu, beraberinde büyük bir atık yükü getirir. Ülkede "
  "her yıl ortaya çıkan tekstil atığı sektör kaynaklarınca yaklaşık bir milyon ton olarak tahmin "
  "edilirken, dünya genelinde bu atığın yüzde birinden azı yeni tekstile geri kazanılabilmektedir "
  "[1]. Atığın kayda değer bir bölümünü, üretim sürecinde açığa çıkan pre-consumer fire oluşturur: "
  "kumaş kesim parçaları, iplik artıkları ve lot fazlası üretimler. Tüketim sonrası atıktan farklı "
  "olarak bu fire temiz, homojen ve bileşimi bilinen bir malzemedir. Bu nedenle ekonomik ve çevresel "
  "açıdan en kolay geri kazanılabilir sınıfı temsil eder. Buna karşın söz konusu malzeme büyük ölçüde "
  "enformel ve verimsiz yöntemlerle yönetilir.")
p("Sorunun temelinde bir pazar yokluğu değil, tarafların birbirini görememesinden doğan bir bilgi "
  "asimetrisi yatar. İktisat yazınında Akerlof'un ortaya koyduğu gibi, kalite bilgisinin alıcı ile "
  "satıcı arasında eşitsiz dağıldığı bir piyasada işlemler ya değerinin altında gerçekleşir ya da hiç "
  "kurulamaz [11]. Üretici fabrika ne ürettiğini bilir ama kimin talep ettiğini bilmez; geri "
  "dönüşümcü ihtiyacını bilir ama uygun arzın kimde olduğunu bilmez. Bu boşlukta faaliyet gösteren "
  "aracılar ölçeklenemez ve süreç, telefon ile WhatsApp üzerinden yürüyen kişisel ağlara bağlı kalır. "
  "Sonuçları somuttur: envanter elektronik tablolarda tutulur, çok katmanlı aracılık üreticiyi gerçek "
  "piyasa fiyatından uzaklaştırır, zamanında alıcı bulunamayan fire depoda nem ve küf nedeniyle değer "
  "yitirir, bileşim ve kalite bilgisinin kayıt altında olmaması ise alıcıda güvensizlik doğurur.")
p("Bu tablodan dört paydaş doğrudan etkilenir. Atığını düşük bedelle elden çıkarmak zorunda kalan "
  "üretici fabrika gelir kaybeder. Tutarlı ve doğrulanmış hammadde arayan geri dönüşümcü tedarik "
  "riskiyle karşılaşır. Geri kazanılabilir malzemenin bertarafa yönelmesi çevresel yükü artırır. "
  "Endüstriyel atık akışına ilişkin gerçek zamanlı veriden yoksun kalan kamu ise politika üretme "
  "kabiliyetini yitirir. Kaybedilen her partinin çevresel bedeli, tek bir tişörtün üretiminin yaklaşık "
  "iki bin yedi yüz litre su gerektirdiği düşünüldüğünde daha da belirginleşir [2]. Nitekim Uşak gibi "
  "merkezlerde günde bin yedi yüz tonu aşan bir işleme kapasitesi bulunmasına karşın, sistemsizlik bu "
  "potansiyelin gerisinde kalınmasına yol açar [3]. Kısacası değeri yüksek ve geri kazanımı kolay bir "
  "kaynak, yalnızca bilgi eksikliği yüzünden hem ekonomiye hem çevreye kazandırılamaz.")

# ====================== 3. ÇÖZÜM ======================
h("3. ÇÖZÜM YAKLAŞIMI (10 PUAN)")
p("ReLoop, üretim firesini iki bütünleşik bileşen aracılığıyla ekonomiye kazandıran, kamu "
  "sistemlerine entegre bir işletmeler arası döngüsellik platformudur; genel katmanlı mimarisi "
  "Şekil 1'de gösterilir. Birinci bileşen, "
  "her fire partisi için otomatik olarak oluşturulan Dijital Malzeme Pasaportudur. Pasaport; lif "
  "bileşimini, gramaj ve eni, rengi, lot numarasını, üretim tarihini, uygulanan kimyasal işlemleri, "
  "miktarı, kalite sınıfını, konumu ve fotoğrafları bir arada tutar. Burada kritik bir tasarım "
  "tercihi yapılmıştır: lif bileşimi fotoğraftan tahmin edilmez, çünkü bir görüntüden lif oranının "
  "çıkarılması bilimsel olarak mümkün değildir. Bileşim, fabrikanın kendi üretim reçetesinden veya "
  "kurumsal kaynak planlama kaydından alınır. Görüntü işleme ise yalnızca veri girişini hafifletmek "
  "amacıyla rengi, kumaş ailesini ve olası kusurları tanımak ve etiket bilgisini okumak için "
  "kullanılır. Pasaport oluşturulurken çalışan tutarsızlık denetimi, gramaj ile kumaş tipi veya "
  "beyan edilen lif ile kumaş ailesi arasındaki çelişkileri işaretleyerek veri kalitesini güvence "
  "altına alır. Miktar ise uzunluk, en ve gramaj bilgisinden kilograma normalize edilir.")
p("İkinci bileşen, açıklanabilir bir eşleştirme motorudur ve iki aşamada çalışır. İlk aşamada, "
  "mekanik geri dönüşümü olanaksız kılan elastan gibi kontaminant liflerin varlığı, yüz kilogramlık "
  "asgari miktar, alıcının kalite tabanı ve bölge yarıçapı gibi ölçütler bir sert filtre olarak "
  "uygulanır. İkinci aşamada, bu filtreyi geçen partiler lif uyumu, lojistik maliyeti, miktar, fiyat "
  "örtüşmesi, kalite ve satıcı güvenilirliğinden oluşan ağırlıklı bir skor fonksiyonuyla sıralanır. "
  "Sonuç yalnızca bir yüzde değil, gerekçesiyle birlikte sunulur. Böylece kullanıcı eşleşmenin neden "
  "önerildiğini görür. Sistem, veri birikene kadar yalnızca içerik ve profil temelli çalışır, "
  "işbirlikçi filtreleme gibi yöntemlere ancak yeterli işlem geçmişi oluştuğunda geçer.")
p("Platformun uçtan uca akışı Şekil 2'de özetlenmiştir. Fabrika fireyi fotoğraflayarak veya WhatsApp "
  "üzerinden ileterek pasaportu oluşturur. Motor, mevcut talep havuzunu tarayıp en uygun eşleşmeleri "
  "önerir. Alıcı, eşleşme onaylanana kadar yalnızca bölge, lif, miktar ve kalite bilgisini görür; "
  "fabrikanın kimliği ve üretim ayrıntıları gizli kalır. Teklif kabul edildiğinde taraf kimlikleri "
  "açılır ve ödeme, teslim onayına kadar emanet hesabında tutulur. Teslimde alıcının onayı ve "
  "fotoğraflı geri bildirimiyle ödeme serbest bırakılır, taraflar birbirini değerlendirir. İşlem "
  "verisi son olarak anonim ve toplulaştırılmış biçimde Bakanlığın çevre bilgi sistemlerine ve "
  "ilgili organize sanayi bölgesi panosuna yansır. Kayıt aşamasındaki vergi levhası, ticaret sicil "
  "ve OSB üyelik doğrulaması, ilk işlemlerdeki güvenli mod ve isteğe bağlı laboratuvar doğrulamasıyla "
  "verilen doğrulanmış parti niteliği güveni katmanlı biçimde tesis eder. Böylece ReLoop; üreticiye "
  "daha yüksek fiyat ve daha hızlı satış, geri dönüşümcüye doğrulanmış ve sürekli hammadde, kamuya "
  "ise ölçülebilir bir atık verisi sağlar.")
figure("sekil1_mimari.png", 5.6, "Şekil 1. ReLoop katmanlı sistem mimarisi.")
figure("sekil2_akis.png", 6.3, "Şekil 2. Uçtan uca kullanıcı ve veri akışı.")

# ====================== 4. YENİLİKÇİLİK ======================
h("4. PROJENİN YENİLİKÇİ YÖNLERİ VE BENZERSİZ DEĞER ÖNERİSİ (10 PUAN)")
p("ReLoop'un yenilikçiliği tek bir teknolojik bileşende değil, Türkiye tekstil sanayisinin kendine "
  "özgü yapısına uyarlanmış bütünleşik bir kurguda ve kamu ekosistemiyle kurduğu bağda gizlidir. "
  "Dijital pasaport ya da işletmeler arası pazar yeri kavramlarının her biri tek başına zaten bilinir. "
  "ReLoop'u ayırt eden nokta, bu kavramları pre-consumer fireye, organize sanayi bölgesi gerçeğine ve "
  "ulusal çevre bilgi sistemlerine birlikte uyarlamasıdır. Alandaki benzer girişimler gözden "
  "kaçırılmamış, farklılaşma onların karşısında açıkça konumlandırılmıştır. Tablo 1, ReLoop'u bu "
  "girişimlerden ayıran temel farkları özetler.")
table(["Girişim", "Odağı", "ReLoop'tan farkı"],
      [["Reverse Resources (Estonya) [6]", "Markaların küresel geri dönüşüm tedariki",
        "Türkiye OSB/KOBİ gerçeğine ve kamu sistemlerine entegre değildir"],
       ["Swatchloop (Türkiye) [7]", "YZ destekli tekstil atık yönetimi ve dijital ürün pasaportu",
        "En yakın benzer; dijital pasaport ve YZ her ikisinde de var. ReLoop pre-consumer fire, OSB "
        "kümesi, blind eşleştirme ve EÇBS/TABS kamu entegrasyonu odağıyla ayrışır"],
       ["Fibersort (Hollanda)", "Tüketim sonrası otomatik ayrıştırma donanımı",
        "ReLoop yazılım tabanlı olup üretim atığını eşleştirir"],
       ["circular.fashion (Almanya)", "Tasarım aşaması ve dijital pasaport danışmanlığı",
        "Üretim atığı eşleştirmesi yapmaz"]],
      widths=[1.8, 2.1, 2.6])
p("Tablo 1. Benzer girişimlerle karşılaştırma.", italic=True, align="c", size=10)
doc.add_paragraph()
p("Platformun savunulabilir üstünlüğü beş eksende toplanır. Bunların ilki kamu entegrasyonudur. "
  "ReLoop, fire verisini anonim ve toplulaştırılmış biçimde Bakanlığın çevre bilgi sistemlerine "
  "aktararak kamuya doğrudan değer üreten tek platformdur. Sayılan girişimlerin hiçbiri bu bağı "
  "kurmaz. İkinci eksen rekabet mahremiyetidir. Aynı organize sanayi bölgesindeki rakip fabrikaların "
  "birbirinin fire oranını görmesini engelleyen blind eşleştirme, Türk üreticisinin en somut "
  "kaygısına doğrudan yanıt verir. Üçüncüsü, lif ailesinden kalite sınıfına uzanan sektöre özgü "
  "ontolojidir. Bu taksonomi, geri dönüşülebilirlik kurallarını içinde barındırarak eşleştirme "
  "doğruluğunu yükseltir. Dördüncü eksen izlenebilirliktir. Pasaport şeması Avrupa Birliği'nin "
  "Dijital Ürün Pasaportu veri alanlarıyla uyumlu tasarlandığından, ihracatçı için gelecekteki "
  "yükümlülüklere hazır bir altyapı sunar [5]. Bununla birlikte projenin değer önerisi bu düzenlemeye "
  "bağımlı değildir. Beşincisi ise saha öncelikli tasarımdır. WhatsApp, fotoğraf ve çevrimdışı "
  "senkronizasyon üzerine kurulduğu için dijital okuryazarlığı sınırlı kullanıcıyı da kapsar. Bu beş "
  "bileşenin bütünü, mevcut çözümlerin ulaşamadığı bir değeri hem eşleştirme doğruluğu hem de kamu "
  "faydası ekseninde ortaya çıkarır.")

# ====================== 5. TEKNOLOJİLER ======================
h("5. KULLANILACAK TEKNOLOJİLER (5 PUAN)")
p("ReLoop, olgun ve büyük ölçüde açık kaynaklı bileşenlerden oluşan katmanlı bir teknoloji "
  "yığınıyla geliştirilmektedir. Yığın, Şekil 1'deki sistem mimarisiyle örtüşen işlevsel "
  "katmanlara ayrılmaktadır. Her katmanın bileşenleri, çalışan çekirdek ile yol haritasındaki "
  "ileri yetenekleri ayıran olgunluk durumlarıyla birlikte Tablo 2'de özetlenmektedir. Teknoloji "
  "seçiminde belirleyici ölçüt, saha koşullarında güvenilir çalışma ve uzun vadeli bakım kolaylığı "
  "olduğundan her katmanda yaygın benimsenmiş ve topluluk desteği güçlü bileşenler tercih "
  "edilmektedir. Kullanılan başlıca bileşenlerin lisansları izin verici niteliktedir. PostgreSQL "
  "için PostgreSQL Lisansı, FastAPI ve React için MIT, OpenCV için Apache 2.0 geçerli olup tüm "
  "künyeler on beşinci bölümdeki tabloda beyan edilmektedir. Bakanlık ve firma verisiyle çalışan "
  "yapay zekâ modelleri ise veri egemenliği ve kişisel verilerin korunması ilkesi gereği yurt "
  "içinde veya uç altyapıda çalıştırılmakta, açık izin olmaksızın üçüncü taraf bulut hizmetlerine "
  "aktarılmamaktadır.")
table(["Katman", "Bileşenler ve teknolojiler", "Durum"],
      [["Mobil ve saha",
        "React Native mobil uygulama, WhatsApp Business Cloud API, cihaz kamerasıyla fotoğraf "
        "yakalama, çevrimdışı çalışıp bağlantıda eşitlenen yerel depolama", "Geliştiriliyor"],
       ["Web ve gösterge paneli",
        "Çalışan gösterim saf HTML, JavaScript ve SVG ile tek dosya, üretim arayüzü React ve "
        "TypeScript, B2B pazar ile kamu ve OSB gösterge panelleri", "Çalışan demo"],
       ["Uygulama ve API",
        "Python FastAPI servisleri, REST ve coğrafi alanlar için OGC API Features, rol tabanlı "
        "erişim (RBAC), OAuth 2.0 ve JWT, TLS ve AES şifreleme, emanet iş mantığı", "Prototip"],
       ["Yapay zekâ ve eşleştirme",
        "Python standart kütüphanesiyle açıklanabilir iki aşamalı motor (elle ağırlıklı doğrusal "
        "skor), veri biriktikçe LightGBM tabanlı sıralama öğrenme", "Çekirdek çalışıyor"],
       ["Görüntü işleme",
        "OpenCV ile renk, kumaş ailesi ve kusur ön tespiti, Tesseract ile etiket okuma (OCR), "
        "ileri aşamada PyTorch üzerinde NIR ve derin öğrenme ile lif tanıma", "Kısmi / yol haritası"],
       ["Veri ve büyük veri",
        "PostgreSQL ve yarı yapılı alanlar için JSONB, S3 uyumlu nesne depolama, Redis önbellek ve "
        "kuyruk, ölçekte agrega çevre analitiği", "Veri modeli tanımlı"],
       ["Bulut ve altyapı",
        "Docker konteynerleri, yurt içi bulut veya uç çalışma zamanı, yatay ölçeklenebilir servis "
        "mimarisi", "Planlanan"],
       ["Sensör ve donanım",
        "NIR spektroskopi tabanlı otomatik ayrıştırma düzeneği, depo nem ve koşul izleme için IoT "
        "sensörleri", "Yol haritası"],
       ["Kamu entegrasyonu",
        "EÇBS/TABS için REST ve JSON bildirim bağdaştırıcısı (atık kodu 04 02 22), Avrupa Birliği "
        "Dijital Ürün Pasaportu veri alanlarıyla uyum", "Örnek akış"]],
      widths=[1.55, 3.75, 1.2])
p("Tablo 2. Teknoloji yığınının katmanlara göre dağılımı ve olgunluk durumu.", italic=True, align="c", size=10)
doc.add_paragraph()
p("İstemci katmanı, dijital okuryazarlığı değişken bir kullanıcı kitlesini kapsayacak biçimde saha "
  "öncelikli tasarlanmaktadır. Fabrika kullanıcısı fireyi kendi telefonuyla fotoğraflayarak veya "
  "WhatsApp Business Cloud API üzerinden ileterek pasaport oluşturabilmekte, böylece ayrı bir "
  "uygulama öğrenme yükü ortadan kalkmaktadır. React Native ile geliştirilen mobil uygulama, "
  "bağlantının zayıf olduğu üretim sahalarında çevrimdışı çalışıp bağlantı sağlandığında "
  "eşitlenmektedir. Sistemin bugünkü işleyişi, kullanıcının kendi akıllı telefonu dışında özel bir "
  "donanım gerektirmemekte ve bu durum yaygınlaşma önündeki eşiği düşürmektedir. Alıcılar ile kamu "
  "ve organize sanayi bölgesi yöneticileri aynı veriye, React ve TypeScript ile geliştirilen mobil "
  "uyumlu web arayüzü ve buradaki gösterge panelleri üzerinden erişmektedir. Bu arayüzün çalışan "
  "gösterimi, herhangi bir çerçeveye bağımlı olmadan saf HTML, JavaScript ve SVG ile tek dosya "
  "biçiminde hazırlanmış olup bağlantısız ortamlarda dahi tam işlevle açılmaktadır.")
p("Yığının çekirdeğini, pasaport üretimi ile eşleştirmeyi yürüten yapay zekâ ve görüntü işleme "
  "katmanı oluşturmaktadır. Görüntü işleme burada sınırlı ve belirli bir görev üstlenmektedir. "
  "OpenCV ile renk ve kumaş ailesi sınıflandırılmakta ve olası kusurlar ön tespitle "
  "işaretlenmekte, Tesseract ile de etiket üzerindeki bilgi optik karakter tanımayla "
  "okunmaktadır. Lif bileşimi bir görüntüden çıkarılamayacağından fotoğraftan tahmin edilmemekte, "
  "fabrikanın üretim reçetesinden veya kurumsal kaynak planlama kaydından alınmaktadır. Eşleştirme "
  "motoru iki aşamalı ve açıklanabilir bir kurgu olup Python standart kütüphanesiyle deterministik "
  "biçimde çalışmaktadır. Skor elle ağırlıklandırılmış doğrusal bir fonksiyonla üretildiğinden "
  "sonuç, bir kara kutu değil, bileşen katkılarına ayrıştırılabilen bir gerekçe olarak "
  "sunulmaktadır. Sistem, yeterli işlem geçmişine ulaşana kadar yalnızca içerik ve profil temelli "
  "çalışmaktadır. Ağırlıkların veriyle güncellendiği LightGBM tabanlı sıralama öğrenme yaklaşımına "
  "ise ancak bu geçmiş biriktiğinde geçilmektedir. Görüntü işlemedeki ileri hedef, yakın kızılötesi "
  "tayfını derin öğrenmeyle birleştiren otomatik lif tanımadır. Bu yaklaşımın yüksek doğrulukla "
  "uygulanabilirliği alan yazınında gösterilmiştir [13].")
p("Bu çekirdeği veri, arka uç ve entegrasyon katmanları taşımaktadır. Her fire partisi, "
  "PostgreSQL üzerinde tutulan ve yarı yapılı alanlar için JSONB esnekliğinden yararlanan Dijital "
  "Malzeme Pasaportu şemasıyla temsil edilmektedir. Kamuya açılan görünümler ise bu kayıtlardan "
  "anonim ve toplulaştırılmış biçimde türetilmektedir. Servisler Python tabanlı FastAPI ile "
  "yazılmakta, dış sistemlere açılan uçlar REST ve coğrafi alanlar için OGC API Features "
  "standardıyla sunulmaktadır. Güvenlik katmanında rol tabanlı erişim denetimi ile OAuth 2.0 ve "
  "JWT tabanlı kimlik doğrulama uygulanmaktadır. Veri aktarımda TLS, saklamada AES ile "
  "şifrelenmekte, ödeme ise teslim onayına kadar emanet mantığıyla korunmaktadır. Tüm servisler "
  "Docker konteynerleriyle paketlenmekte ve yurt içinde barındırılabilen, yatay ölçeklenebilir bir "
  "modelle çalıştırılmaktadır. Veri katmanı bugün ilişkisel bir modele dayanmaktadır. Ulusal "
  "ölçekte işlem hacmi büyüdükçe agrega çevre göstergelerinin üretimi için büyük veri analitiği yol "
  "haritasında yer almaktadır. Kamu entegrasyonu, tamamlanan eşleşmeleri atık koduyla birlikte "
  "Bakanlığın çevre bilgi sistemlerine bildiren bir bağdaştırıcıyla sağlanmaktadır. Pasaport "
  "şeması ise Avrupa Birliği Dijital Ürün Pasaportu veri alanlarıyla uyumlu tasarlandığından "
  "ihracatçı için gelecekteki yükümlülüklere hazır bir altyapı oluşturmaktadır [5]. Donanım tarafı "
  "yol haritasında yer almakta, endüstriyel ölçekte otomatik ayrıştırma için yakın kızılötesi "
  "tabanlı düzenekleri ve firenin depoda nemden değer yitirmesini önlemeye yönelik nesnelerin "
  "interneti sensörlerini kapsamaktadır.")

# ====================== 6. TEKNİK MİMARİ ======================
h("6. TEKNİK MİMARİ (8 PUAN)")
p("ReLoop, kamu sistemleriyle veri paylaşımına olanak veren katmanlı ve servis odaklı bir "
  "mimariyle tasarlanmaktadır (Şekil 1). Sunum katmanı, saha için React Native mobil uygulamayı ve "
  "WhatsApp Business Cloud API'sini, alıcı ile kamu görünümleri için de React ve TypeScript tabanlı "
  "mobil uyumlu web arayüzünü barındırmaktadır. Bunun altındaki uygulama katmanı, Python tabanlı "
  "FastAPI ile yazılan, sürümlenmiş ve kimlik doğrulamalı REST uçlarından oluşmaktadır. Çekirdek iş "
  "mantığı dört bağımsız servise ayrılmaktadır. Pasaport servisi pasaportun yaşam döngüsünü ve "
  "tutarsızlık denetimini yürütmekte, eşleştirme servisi arz ile talebi puanlamakta, güven ve işlem "
  "servisi kör teklif ile emanet ve değerlendirme süreçlerini yönetmekte, kamu veri servisi ise "
  "anonim ve toplulaştırılmış raporlamayı üstlenmektedir. Yapay zekâ çalışma zamanı görüntü işleme, "
  "optik karakter tanıma ve skorlama bileşenlerini barındırmakta, Bakanlık verisinin üçüncü taraf "
  "buluta gönderilmesini yasaklayan ilke gereği yurt içinde veya uç altyapıda çalıştırılmaktadır.")
p("Veri katmanında ilişkisel yapı ile pasaportun yarı yapılı içeriği bir arada tutulmaktadır. "
  "Çekirdek varlıklar Pasaport, Talep, İşlem, Kurum ile Kullanıcı ve Puan olup pasaport, PostgreSQL "
  "şeması içindeki bir JSONB alanında saklanmaktadır. Sistemin uçtan uca veri akışı Şekil 2'de "
  "özetlenmektedir. Fabrikanın fireyi fotoğraflaması veya WhatsApp üzerinden iletmesiyle pasaport "
  "oluşturulmakta, eşleştirme servisi talep havuzunu tarayarak sıralı önerileri döndürmektedir. "
  "Kabul edilen teklifte kimlikler açılmakta ve ödeme emanete alınmakta, teslim onayıyla serbest "
  "bırakılmakta, işlem ise anonim biçimde kamu sistemlerine yansımaktadır. Mimarinin belkemiğini, "
  "lif ailesinden alt tipe ve kalite sınıfına uzanan sektöre özgü ontoloji oluşturmaktadır. "
  "Kullanıcı rolleri fabrika, alıcı, OSB yöneticisi, salt okunur Bakanlık ve moderatör olarak "
  "ayrılmakta, her rol yalnızca yetkili olduğu veriye erişmektedir.")
p("Eşleştirme motoru iki aşamalıdır. Elastan gibi kontaminant lifler, asgari miktar ve bölge "
  "yarıçapı gibi ölçütlerden oluşan sert filtreyi geçen partiler, ikinci aşamada altı bileşenin "
  "ağırlıklı toplamıyla puanlanmaktadır. Bu bileşenler lif uyumu, lojistik yakınlığı, miktar "
  "karşılama, fiyat örtüşmesi, kalite ve satıcı güvenilirliği olup her biri sıfır ile bir arasında "
  "normalize edilmektedir. Ağırlıklar ise alan bilgisinden türetilen ve veri biriktikçe sıralama "
  "öğrenmeyle güncellenen başlangıç değerleridir.")
eq = p("MatchScore = 0,30·lif + 0,20·lojistik + 0,15·miktar + 0,15·fiyat + 0,10·kalite + 0,10·güven",
       align="c")
eq.runs[0].italic = True
p("Skorun açıklanabilir çıktısı, öneri gerekçesini bileşen katkılarına ayrıştırarak kullanıcıya "
  "iletmektedir. Dışa açılan uçlar REST ile birlikte coğrafi ve raporlama verisi için OGC API "
  "Features standardını ve JSON ile CSV taşınabilir biçimlerini desteklemektedir. Dış sistem "
  "entegrasyonları, EÇBS/TABS'a atık koduyla bildirimi, WhatsApp Business Cloud API ile mesajlaşmayı "
  "ve yol haritasında kurumsal kaynak planlama ile NIR ayrıştırma cihazlarını kapsamaktadır. Donanım "
  "bileşeni tarafında sahadaki veri yakalama bugün kullanıcının akıllı telefonu ve kamerasıyla "
  "gerçekleştirilmekte, böylece özel bir cihaz gerekmemektedir. Endüstriyel ölçekte otomatik "
  "doğrulama için NIR spektroskopi düzenekleri ve depo nemini izleyen nesnelerin interneti "
  "sensörleri ise yol haritasında yer almaktadır. Güvenlik, OAuth 2.0 ile rol tabanlı erişim ve "
  "aktarımda TLS, saklamada AES şifrelemeyle sağlanmaktadır. Durumsuz API, kuyruk ve yatay ölçekleme "
  "sayesinde yeni sektörler büyük ölçüde ontoloji ile pasaport şemasının genişletilmesiyle sisteme "
  "eklenebilmektedir.")

# ====================== 7. GELİŞTİRME SEVİYESİ ======================
h("7. PROJENİN GELİŞTİRME SEVİYESİ (8 PUAN)")
p("Proje, fikir aşamasını geride bırakmış ve çalışan bir asgari uygulanabilir ürünle prototip "
  "düzeyine ulaşmıştır. Başvuru için fikir veya asgari uygulanabilir ürün düzeyi yeterli olsa da, "
  "iddiaların doğrulanabilirliğini göstermek amacıyla çekirdek işlevsellik fiilen kodlanmıştır. "
  "Proje bugün, açıklanabilir eşleştirme çekirdeği ile etkileşimli bir arayüzün çalıştığı, saha "
  "pilotundan önceki bir olgunluk düzeyinde bulunmaktadır.")
p("Çalışır durumdaki başlıca bileşenler, harici bağımlılık olmadan geliştirilmiştir. Bunlar iki "
  "aşamalı ve açıklanabilir eşleştirme motoru, lif ailesinden kalite sınıfına uzanan sektöre özgü "
  "ontoloji, pasaport tutarsızlık denetimi, seksen fabrika ile iki yüz elli fire partisi ve altmış "
  "alıcı talebinden oluşan sentetik ekosistem üreteci ve anonim kamu panosudur. Bu çekirdek, "
  "tarayıcıda internet bağlantısı olmadan açılan tek dosyalık bir arayüzde beş sekme hâlinde "
  "kullanıma sunulmuştur. Donanım tarafında ayrı bir bileşen geliştirilmesine gerek kalmamış, saha "
  "verisi kullanıcının akıllı telefonu ve kamerasıyla toplanmaktadır.")
p("Arayüz tarafı tamamlanmış ve tam etkileşimli hâldedir. Açıklanabilir eşleşme skoru, canlı "
  "tutarsızlık denetimiyle pasaport oluşturma ve anonim kamu panosu, bu arayüzde gerçek veri "
  "üzerinde çalışmaktadır. Açıklanabilir skor kırılımı ile menzil haritası Şekil 3'te, kamu ve "
  "organize sanayi bölgesi için ulusal gösterge paneli ise Şekil 4'te görülmektedir. Kör teklif ile "
  "emanet akışı etkileşimli bir durum makinesi olarak, çevre bilgi sistemi bildirimi ise gerçek bir "
  "şema doğrulamasıyla işlemektedir. Bu akışlarda yalnızca gerçek ödeme mutabakatı ve kamu "
  "sistemlerine ağ üzerinden iletim, üretim aşamasına bırakılan örnek adımlardır. Saha koşullarında "
  "henüz bir pilot uygulama yürütülmemiş olup bu adım yol haritasında yer almaktadır.")
figure("sekil3_pazar.png", 6.3,
       "Şekil 3. Pazar ve eşleştirme ekranı: sıralı adaylar, açıklanabilir skor kırılımı ve "
       "menzil haritası.")
figure("sekil4_dashboard.png", 6.3,
       "Şekil 4. Kamu ve OSB gösterge paneli: gömülü Türkiye haritasında pilot bölge dağılımı.")
p("Geliştirme sürecinde iki tür test gerçekleştirilmiştir. Birincisi, arayüzdeki JavaScript "
  "motorunun Python motoruyla birebir aynı sonucu ürettiğini denetleyen otomatik bir parite "
  "testidir. Bu test, arayüz kurulumunu, beş sekmenin tamamının hesaplama yollarını, kamu panosu "
  "sayılarını, örnek senaryoyu ve bildirim yükünün şema doğrulayıcısını kapsayan on sekiz kontrolün "
  "tamamını geçmiştir. İkincisi, pasaport tutarsızlık denetiminin sınanmasıdır. Sentetik veriye "
  "kasıtlı olarak yerleştirilen on beş tutarsızlığın tamamı denetim tarafından yakalanmıştır. "
  "Motorun sentetik veri üzerindeki bulguları da somuttur. İki yüz elli fire partisinin yüz on "
  "dokuzu eşleşmiş, ortalama uyum skoru yüzde seksen yedi, ortalama mesafe on bir kilometre olarak "
  "elde edilmiştir. Skorların yüzde altmış sekiz ile yüzde doksan dokuz arasında yayılması, "
  "bileşenlerin kademeli olması sayesinde motorun adayları ayırt ettiğini göstermektedir. Sert "
  "filtrenin ardından kalan yayılımı büyük ölçüde lojistik yakınlık ve satıcı güvenilirliği "
  "taşımaktadır (Şekil 5). Raporda örneklenen senaryo, motorda birebir yüzde doksan değerini "
  "üretmiş ve böylece metin ile kod arasında tam tutarlılık sağlanmıştır. Bu bulgular deterministik "
  "biçimde üretilen sentetik veri üzerinde alınmış olup motorun uçtan uca işleyişini ve adayları "
  "ayırt etme yeteneğini ortaya koymaktadır. Doğruluğun gerçek dünya karşılığı ise Uşak Organize "
  "Sanayi Bölgesi'nde yürütülecek saha pilotunda sınanacaktır.")
figure("sekil3_demo.png", 5.6,
       "Şekil 5. Sentetik veri üzerinde en iyi eşleşme skorlarının dağılımı "
       "(ortalama yüzde 87, yayılım yüzde 68 ile 99 arası).")
p("Bundan sonraki süreçte planlanan çalışmalar, çözümün üretim ölçeğine ve sahaya taşınmasını "
  "hedeflemektedir. Gerçek arka uç ile ödeme mutabakatı kurulacak, çevre bilgi sistemlerine kimlik "
  "doğrulamalı entegrasyon tamamlanacaktır. Görüntü işleme ve yakın kızılötesine dayalı otomatik lif "
  "doğrulama geliştirilecek, işlem geçmişi biriktikçe ağırlıklar sıralama öğrenmeyle "
  "güncellenecektir. Son olarak Uşak Organize Sanayi Bölgesi'nde bir saha pilotu yürütülerek "
  "çözümün gerçek koşullardaki karşılığı finalde ortaya konacaktır.")

# ====================== 8. TAMAMLANANLAR ======================
h("8. BUGÜNE KADAR NELER TAMAMLANDI? (5 PUAN)")
p("Fikrin ortaya çıkışından başvuru tarihine kadar bir dizi somut adım tamamlanmıştır. Öncelikle, "
  "pre-consumer tekstil firesi, taraflar arasındaki bilgi asimetrisi ve Türkiye ile Uşak özelindeki "
  "veriler üzerinden kapsamlı bir problem ve pazar analizi yapılmıştır. Ardından, Reverse Resources, "
  "Swatchloop, Fibersort ve circular.fashion gibi girişimleri kapsayan bir rakip ve konumlandırma "
  "analizi yürütülmüş, farklılaşma bu girişimler karşısında netleştirilmiştir. Bunun yanında "
  "çevresel etki katsayıları, bölgesel endüstriyel simbiyoz ve otomatik lif tanıma alanlarında bir "
  "literatür taraması gerçekleştirilmiş, Atık Yönetimi Yönetmeliği, Sıfır Atık Yönetmeliği ve çevre "
  "bilgi sistemleriyle entegrasyon çerçevesi incelenmiştir.")
p("Teknik tarafta katmanlı servis mimarisi, veri modeli ve sektöre özgü ontoloji tasarlanmış, iki "
  "aşamalı açıklanabilir eşleştirme motoru ise yalnızca tasarımda kalmayıp çalışır biçimde "
  "kodlanmıştır. Çekirdek, seksen fabrika, iki yüz elli fire partisi ve altmış talepten oluşan "
  "sentetik ekosistem üzerinde sınanmış ve Bölüm 7'de sunulan çalışan gösterimde bütünleştirilmiştir. "
  "Böylece proje, bu aşamada yalnızca bir fikir değil, kavramı, mimarisi, doğrulanmış çekirdek "
  "algoritması ve çalışan bir demosu bulunan bir ürün adayı olarak ortaya konmaktadır. Kalan iş, "
  "gerçek arka uç ve ödeme mutabakatı, kamu sistemlerine kimlik doğrulamalı entegrasyon ve Uşak "
  "pilotunun yürütülmesidir.")

# ====================== 9. GERÇEK HAYAT ======================
h("9. GERÇEK HAYAT UYGULAMASI VE KULLANIM SENARYOLARI (8 PUAN)")
p("Çözümün saha karşılığı, Türkiye tekstil geri dönüşümünün büyük bölümünü tek başına "
  "gerçekleştiren Uşak Organize Sanayi Bölgesi üzerinden somutlaşmaktadır [3]. Bu bölgenin ayırt edici "
  "özelliği, fire üreten fabrikalar ile geri dönüşüm tesislerinin aynı coğrafyada yoğunlaşmasıdır. Bu "
  "yakınlık, kısa mesafe ve hızlı eşleşme için elverişli bir zemin oluşturur. Tipik bir senaryoda, "
  "örme kumaş üreten bir fabrika üretim sonunda sekiz yüz kilogram yüzde yüz pamuk süprem firesi "
  "açığa çıkarır ve bunu telefonuyla fotoğraflar. Sistem rengi ve kumaş ailesini tanır, bileşimi "
  "üretim reçetesinden alır ve fabrikanın yalnızca miktar ile asgari fiyatı girmesiyle pasaportu "
  "oluşturur. Aynı bölgedeki bir geri dönüşüm tesisi ise mekanik geri dönüşüm için elastansız, en az "
  "yüzde doksan beş pamuk içeren bin kilogramlık bir talebi sisteme önceden girmiştir.")
p("Eşleştirme motoru önce sert filtreyi uygular. Elastan içermeyen, yüz kilogramın üzerinde, kalite "
  "tabanını karşılayan ve bölge yarıçapı içindeki parti bu aşamayı geçer. Ardından ağırlıklı skor "
  "hesaplanır ve parti, yüzde doksan uyum skoruyla talebin başına yerleşir. Sistemin ürettiği "
  "açıklama eşleşmenin gerekçesini şeffaf biçimde iletir: lif saflığı tam, mesafe yaklaşık yirmi beş "
  "kilometre ve fiyat aralığı örtüşmektedir. Sekiz yüz kilogramlık arz bin kilogramlık talebi kısmen "
  "karşıladığından, kalan iki yüz kilogram için toplu parti önerilir. Alıcı, fabrikanın kimliğini "
  "görmeden teklifini verir. Teklif kabul edildiğinde kimlikler açılır ve ödeme emanet hesabına "
  "alınır. Teslimde alıcının fotoğraflı onayıyla ödeme serbest bırakılır, taraflar birbirini "
  "değerlendirir ve işlem anonim biçimde OSB panosuna ve Bakanlık sistemlerine yansır.")
p("Aynı mimari farklı senaryolara da yanıt verir. Yüz kilogramın altındaki küçük fireler toplu bir "
  "partide birleştirilerek değerlendirilebilir. Acil ihtiyaç duyan alıcı, piyasa ortalamasına göre "
  "önerilen fiyatı anında kabul ederek süreci hızlandırır. Düzenli tedarik sözleşmesi kuran taraflar "
  "her sevkiyatı sistem üzerinden izleyebilir. OSB yönetimi bölgesel geri kazanım ve karbon raporunu "
  "doğrudan panodan alırken, ihracatçı fabrika aynı pasaport kaydını Avrupa Birliği'nin izlenebilirlik "
  "talebi için kullanır. Böylece telefon ve kişisel ağlara dayalı mevcut süreç, doğrulanmış, şeffaf ve "
  "kayıtlı bir işleyişe taşınır.")

# ====================== 10. BEKLENEN ETKİ ======================
h("10. BEKLENEN ETKİ (8 PUAN)")
p("Projenin etkisi tek bir gösterişli sayı yerine, platformun işlem verisinden ürettiği "
  "karşılaştırmalı ölçütlerle sunulur. Her nicel iddia, varsayımı, yöntemi ve kaynağıyla birlikte "
  "verilir (Şartname md.10.9). Temel gösterge, platform kullanılmadan geçen ortalama satış süresi ve "
  "oluşan değer kaybının, platformla elde edilen süre ve kayba göre farkıdır. Geri kazanılan miktar "
  "ile buna karşılık gelen karbon ve su tasarrufu ise her işlemde pasaport verisinden türetilir.")
p("Çalışan çekirdek, bu ölçüm mantığını sentetik veri üzerinde şimdiden somutlaştırır. İki yüz elli "
  "fire partisinin yüz on dokuzu eşleşmiş (%48 başarı), ortalama on bir kilometrelik mesafeyle "
  "yaklaşık 86,2 ton malzemenin yeniden ekonomiye kazandırılma potansiyeli ortaya çıkmıştır. Bu "
  "tonaja bağlı çevresel tasarruf, açıkça varsayım olarak etiketlenen katsayılarla (karbon: 1,6 kg "
  "CO₂e/kg konservatif [ecoinvent üst ~2,93]; su: ~2.100 L/kg) hesaplanır ve sentetik senaryoda "
  "yaklaşık 138 ton CO₂e ile 181 milyon litre su tasarrufuna karşılık gelir. Bu değerler konservatif "
  "tahminidir: tamamlanmış işlemi değil önerilen eşleşmeyi esas alır, harmanlı partileri de kapsar ve "
  "nihai raporlamada Türkiye'ye özgü birincil yaşam döngüsü (LCA) katsayılarıyla kesinleştirilecektir.")
p("Katsayıların büyüklük mertebesi savunulabilir bir tabana oturur. Kaynak [2]'ye göre birincil "
  "(virgin) pamuğun su ayak izi bir tişört (~250 g pamuk) başına yaklaşık 2.700 litre, kilogram "
  "başına ise on bin litre mertebesindedir. Geri kazanılan pamuk bu yükün büyük bölümünü ortadan "
  "kaldırır. İpliğe dönüşte karbon tarafında da kilogram başına anlamlı bir azaltım elde edilir [12]. "
  "Türkiye'de yıllık tekstil atığı sektör kaynaklarınca yaklaşık bir milyon ton olarak tahmin "
  "edilirken, dünya genelinde bu atığın yüzde birinden azı yeni tekstile dönüşmektedir [1]. Bu "
  "tabloda, pre-consumer akışının kayıt altına alınıp doğru alıcıya yönlendirilmesindeki küçük bir "
  "iyileşme dahi ölçekte büyük karşılık bulur.")
p("Ekonomik düzlemde üretici daha yüksek satış fiyatı, daha kısa satış süresi ve azalan depolama "
  "maliyetiyle kazanırken, geri dönüşümcü doğrulanmış ve sürekli bir hammadde kaynağına kavuşur. "
  "Uşak örneğinde tekstil geri dönüşümünün ülke ekonomisine yıllık yaklaşık bir milyar dolara varan "
  "katkı sağladığı hatırlandığında [3], verimliliği artıran bir altyapının bölgesel getirisi açıktır. "
  "Toplumsal boyutta enformel atık ticareti şeffaflaşıp kayda geçer. Aynı bölgedeki fabrikaların "
  "birbirinin firesini hammadde olarak kullanması, güvencesiz çalışma yerine kurumsallaşan bir "
  "endüstriyel simbiyoz doğurur. Kamusal fayda ise Bakanlık ve OSB yönetimlerinin gerçek zamanlı ve "
  "ölçülebilir endüstriyel atık verisine erişmesi, böylece Sıfır Atık ve Genişletilmiş Üretici "
  "Sorumluluğu hedeflerine somut katkı sunulmasıdır. Platform bu etkiyi ortalama eşleşme süresi, "
  "eşleşme başarı oranı, geri kazanılan toplam tonaj, toplam karbon ve su tasarrufu ile kullanıcı "
  "memnuniyeti göstergeleriyle sürekli izler.")

# ====================== 11. ÖLÇEKLENEBİLİRLİK ======================
h("11. ÖLÇEKLENEBİLİRLİK VE YAYGINLAŞTIRMA POTANSİYELİ (5 PUAN)")
p("ReLoop, tek bir organize sanayi bölgesinde kanıtlanıp ulusal ve sektörler arası ölçeğe taşınacak "
  "biçimde tasarlanmıştır. Mimarisi sektörden bağımsız olduğundan, yeni bir sektörün eklenmesi çekirdek "
  "yazılımı değiştirmeden yalnızca ontoloji ve pasaport şemasının genişletilmesini gerektirir. Büyüme "
  "dört fazda kurgulanmıştır. İlk fazda çözüm, arz ve talebin aynı bölgede yoğunlaştığı Uşak'ta "
  "devreye alınacak, ardından Denizli, Bursa ve Gaziantep gibi merkezlere yayılacaktır. İkinci fazda "
  "plastik enjeksiyon ve ambalaj sektörüne geçilecek, pasaporta polimer tipi ve eriyik akış indeksi "
  "gibi parametreler eklenecektir. Üçüncü fazda otomotiv yan sanayi ve metal işleme dâhil edilerek "
  "platform çok sektörlü bir endüstriyel atık altyapısına dönüşecek, dördüncü fazda ise Güneydoğu "
  "Asya ve Kuzey Afrika'daki üretim merkezlerine yönelik uluslararası açılım hedeflenecektir.")
p("Bu yaygınlaşmanın ticari sürdürülebilirliği tek bir gelir kalemine değil, katmanlı bir modele "
  "dayanır. Ana gelir, yalnızca tamamlanan eşleşmelerden alınan başarıya dayalı işlem komisyonudur; "
  "platform ancak taraflar kazandığında kazanır. Bunun üzerine OSB yönetimleri ve çok tesisli "
  "kurumsal gruplar için raporlama ile merkezî hesap sunan bir abonelik katmanı ve isteğe bağlı "
  "laboratuvar doğrulaması, entegre lojistik ve kalite garanti fonu gibi katma değerli hizmetler "
  "eklenir. Birim ekonomisi henüz saha verisiyle kalibre edilmemiş olsa da, işlem başına yüzde iki "
  "ilâ dört bandındaki bir komisyonun (çalışma varsayımı) sabit maliyeti düşük ve marjinal maliyeti "
  "neredeyse sıfır olan yazılım altyapısında, bölge doygunluğuyla birlikte pozitif katkıya ulaşması "
  "beklenir. Emanet ödeme ve platform içinde biriken izlenebilirlik kaydı, tarafların sistemi aşarak "
  "işlem yapma eğilimini sınırlayarak bu gelir tabanını korur.")
p("Arz ile talebin eşzamanlı oluşmasını gerektiren ikilemi aşmak için benimsenen bölge temelli lansman, "
  "tek bir sanayi bölgesinde çok "
  "sayıda fabrika ile geri dönüşümcünün eşzamanlı katılımını sağlar ve OSB yönetimiyle bölgesel atık "
  "dijitalleştirme pilotu olarak konumlanır. Birden çok tesise sahip büyük gruplar için sunulan "
  "holding hesabı yapısı, merkezî raporlamayı korurken her lokasyonun kendi envanterini yönetmesine "
  "olanak tanır. Durumsuz API, yatay ölçekleme ve taşınabilir veri biçimleri bu genişlemenin teknik "
  "altyapısını oluşturur. Nitekim ReLoop adı da bu vizyon gözetilerek, tekstile özgü olmayan ve tüm "
  "endüstriyel döngüsel eşleştirmeyi kapsayabilecek bir çatı ismi olarak seçilmiştir.")

# ====================== 12. RİSKLER ======================
h("12. RİSKLER VE ÇÖZÜM YAKLAŞIMINIZ (5 PUAN)")
p("Projenin geliştirme ve saha uygulaması aşamalarında öngörülen başlıca riskler ile bunlara karşı "
  "kurgulanan önlemler Tablo 3'te özetlenmiştir. Riskler, hem iş modeli hem de teknik boyutta ele "
  "alınmış; her biri için uygulanabilir bir tedbir tanımlanmıştır.")
table(["Risk", "Önlem / B planı"],
      [["Tarafların platformu aşarak işlem yapması ",
        "Emanet ödeme, kalite garanti fonu, entegre lojistik ve yalnızca platformda oluşan "
        "izlenebilirlik kaydı platformda kalmayı avantajlı kılar"],
       ["Düşük likidite (tavuk-yumurta)",
        "Arz ve talebin aynı bölgede olduğu Uşak ile başlama, çift yönlü talep girişi, OSB ile "
        "toplu katılım"],
       ["Lojistik maliyeti (hacimli, düşük değerli fire)",
        "Skorda nakliye maliyetinin somut gösterimi, bölge içi eşleştirme, ileride konsolidasyon"],
       ["Fiziksel muayene olmadan güven açığı",
        "Kalibre fotoğraf, isteğe bağlı laboratuvar doğrulaması, doğrulanmış parti niteliği ve "
        "güvenli mod"],
       ["Yapay zekâdan lif oranı beklentisi",
        "Bileşim fotoğraftan değil üretim kaydından alınır. Görüntü işleme yalnızca renk, kumaş ve "
        "kusurla sınırlıdır"],
       ["Düşük dijital adaptasyon",
        "WhatsApp, fotoğraf ve çevrimdışı senkronizasyonla asgari veri girişi"],
       ["Veri güvenliği ve KVKK",
        "Yurt içi/uç yapay zekâ, şifreleme, rol tabanlı erişim; demo ortamında sentetik veri"]],
      widths=[2.3, 4.2])
p("Tablo 3. Başlıca riskler ve önlemler.", italic=True, align="c", size=10)

# ====================== 13. TAKIM ======================
h("13. TAKIM YETKİNLİĞİ (4 PUAN)")
p("Takım, üçü bilgisayar mühendisliği ve matematik alanlarında öğrenim gören üç öğrenci ile bir "
  "bilgisayar mühendisi danışmandan oluşmaktadır. Üyelerin yetkinlikleri; projenin yazılım mimarisi, "
  "veri ve modelleme ile ürün ve iş modeli boyutlarını bütünüyle kapsayacak biçimde dağıtılmıştır. "
  "İletişim sorumluluğu takım kaptanında olup Bakanlık ve TEKNOFEST ile yürütülecek yazışmalar bu "
  "kişi üzerinden yapılacaktır.")
table(["Ad Soyad", "Bölüm / Sınıf", "Rol ve katkı"],
      [["Beyzanur Yavuz", "Bilgisayar Müh. — 3. sınıf",
        "Takım kaptanı ve iletişim sorumlusu; proje koordinasyonu, iş modeli ve arka uç geliştirme"],
       ["Şevval [Soyadı]", "Bilgisayar Müh. — 4. sınıf",
        "Yazılım mimarisi, eşleştirme motoru ve görüntü işleme bileşenleri"],
       ["Zehra [Soyadı]", "Matematik — 3. sınıf",
        "Skor fonksiyonu ve ağırlık modeli, veri analizi ile çevresel/ekonomik etki metrikleri"],
       ["Tuğçem Partal", "Bilgisayar Mühendisi — Danışman",
        "Teknik danışmanlık; mimari ve algoritma gözetimi"]],
      widths=[1.7, 1.9, 2.9])
p("Tablo 4. Takım üyeleri ve görev dağılımı.", italic=True, align="c", size=10)

# ====================== 14. TAKVİM ======================
h("14. PROJE TAKVİMİ (4 PUAN)")
p("Yarışma takvimiyle hizalı olan yol haritası, projenin bugünden final sunumuna kadar adım adım "
  "nasıl ilerleyeceğini Tablo 5'te ortaya koyar. Çalışma, her özelliğin çalışır bir dilim "
  "olarak eklendiği kısa haftalık yinelemelerle yürütülür. İş bölümü Tablo 4'teki rollere göre "
  "dağıtılmaktadır.")
table(["Dönem", "Hedef ve çıktı"],
      [["12–14 Ağustos", "Ön Değerlendirme Raporu'nun tamamlanıp teslimi; eşleştirme motoru çekirdeği "
        "ve sentetik veri tabanının kurulması"],
       ["15–21 Ağustos", "Pasaport oluşturma akışı, blind eşleştirme arayüzü ve kamu panosunun ilk "
        "sürümü"],
       ["25 Ağustos", "Çevrimiçi açılış buluşması; Bakanlık veri setleri ve gereksinimlerinin "
        "incelenmesi"],
       ["26 Ağustos – 4 Eylül", "Mentorluk süreci; görüntü işleme demo modeli, WhatsApp bildirim "
        "akışı ve emanet/işlem akışının entegrasyonu; proje sunumunun hazırlanması"],
       ["4–9 Eylül", "Uçtan uca demonun kararlı hâle getirilmesi, demo videosu ve teknik "
        "dokümantasyon; final provası"],
       ["9 Eylül", "Final sunumu"]],
      widths=[1.8, 4.7])
p("Tablo 5. Proje takvimi ve yol haritası.", italic=True, align="c", size=10)

# ====================== 15. EK / KAYNAKLAR ======================
h("15. EK AÇIKLAMALAR")
p("Bu bölüm, Şartname'nin katılımcı yükümlülüklerine (md.10.3–10.10) ilişkin beyanları ve rapordaki "
  "nicel ifadelerin dayandığı kaynakları içerir.")


def sub(label, text, size=11):
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(6)
    r = par.add_run(label + " "); r.bold = True; r.font.size = Pt(size)
    par.add_run(text).font.size = Pt(size)
    return par


def blok(baslik):
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(6)
    r = par.add_run(baslik); r.bold = True; r.font.color.rgb = KOYU; r.font.size = Pt(11.5)
    return par


# --- Yapay Zekâ Kullanım Beyanı (md.10.5) ---
blok("Yapay Zekâ Kullanım Beyanı (md.10.5)")
sub("Modeller ve veri kaynağı:",
    "Renk, kumaş ailesi ve kusur sınıflandırması için hafif bir evrişimli sinir ağı (MobileNet / "
    "EfficientNet ailesi; Apache-2.0), kamuya açık kumaş görsel veri kümeleri ve ekibin etiketlediği "
    "küçük bir küme üzerinde ince ayarlanacaktır. Etiket ve lot okuma için Tesseract OCR (Apache-2.0) "
    "kullanılır. Eşleştirme mevcut hâlde kural tabanlı ağırlıklı skordur; işlem verisi biriktikçe "
    "sıralama öğrenimi (LightGBM; MIT) devreye alınacaktır. Lif kompozisyonu modelden değil, "
    "fabrikanın üretim reçetesi veya ERP beyanından alınır.")
sub("Dış API ve veri egemenliği:",
    "Bildirim amacıyla WhatsApp Business API kullanılır. Yapay zekâ çıkarımı yurt içi veya uç "
    "altyapıda çalışır; Bakanlık verileri açık izin olmaksızın üçüncü taraf yapay zekâ ya da bulut "
    "model sağlayıcılarına gönderilmez.")
sub("Çıktı doğrulama:",
    "Her öneri açıklanabilir bileşen skoruyla sunulur ve taraf onayı (teklif–kabul akışı) ile teyit "
    "edilir. Görüntü modeli, güven eşiğinin altındaki tahminleri manuel girişe düşürür; DMP "
    "tutarsızlık denetimi beyanı çapraz kontrol ederek hatalı veriyi işaretler.")
sub("Hata ve yanlılık (bias) riski, azaltım:",
    "Başlıca riskler sınırlı temsil gücüne sahip veriyle eğitim, bölgesel veya sınıf dengesizliğinden "
    "doğan yanlılık ve modelin aşırı güven göstermesidir. Azaltım olarak insanın döngüde olduğu onay, güven eşikleri, "
    "kompozisyonun beyandan alınması, düzenli performans izleme ve modelin yalnızca renk/kumaş/kusur "
    "ile sınırlandırılması uygulanır.")
sub("Açıklanabilirlik:",
    "Her eşleşme; lif, lojistik, miktar, fiyat, kalite ve güven bileşenlerinin katkısıyla birlikte "
    "kısa bir gerekçe metni üzerinden şeffaf biçimde açıklanır.")

# --- Açık Kaynak ve Lisans Beyanı (md.10.4) ---
blok("Açık Kaynak ve Lisans Beyanı (md.10.4)")
p("Kullanılan ve kullanılması planlanan bileşenler ile lisansları Tablo 6'da beyan edilmiştir. "
  "Projede GPL/AGPL lisanslı bir bileşen kullanılmamaktadır. İleride kullanılması hâlinde ayrıca "
  "belirtilecektir.")
table(["Bileşen", "Lisans", "Kullanım"],
      [["Python 3", "PSF License", "Çekirdek dil, demo motoru"],
       ["python-docx", "MIT", "Rapor/doküman üretimi"],
       ["Matplotlib", "Matplotlib (BSD uyumlu)", "Şekiller"],
       ["FastAPI (planlanan)", "MIT", "Backend REST API"],
       ["PostgreSQL (planlanan)", "PostgreSQL License", "Veri tabanı"],
       ["Tesseract OCR (planlanan)", "Apache-2.0", "Etiket/lot OCR"],
       ["MobileNet/EfficientNet ağırlıkları (planlanan)", "Apache-2.0", "Görüntü sınıflandırma"],
       ["LightGBM (planlanan)", "MIT", "Sıralama öğrenimi"],
       ["Valkey / Redis (planlanan)", "BSD-3 (Valkey)", "Önbellek, kuyruk"],
       ["WhatsApp Business API", "Meta ticari şartları", "Bildirim (ticari; servis şartına tabi)"]],
      widths=[2.5, 1.9, 2.1])
p("Tablo 6. Bileşen ve lisans beyanı. Ticari/servis şartına tabi tek bileşen WhatsApp Business "
  "API'dir; Redis'in SSPL sürümü yerine BSD lisanslı Valkey tercih edilecektir.",
  italic=True, align="c", size=10)
doc.add_paragraph()

# --- Veri Güvenliği, KVKK ve İdarenin Kullanım Hakkı (md.10.6, 10.7, 10.10) ---
blok("Veri Güvenliği, KVKK ve İdarenin Kullanım Hakkı (md.10.6, 10.7, 10.10)")
sub("KVKK (6698 sayılı Kanun):",
    "Demo ve geliştirme ortamlarında yalnızca sentetik ve anonim veri kullanılır; kimliği "
    "belirlenebilir gerçek kişiye ait veya hassas nitelikli veri işlenmez. Kurumsal kayıt verileri "
    "(vergi levhası, ticaret sicil) 6698 sayılı Kanun'a uygun, açık rıza ve amaçla sınırlı biçimde "
    "işlenir.")
sub("Veri silme (md.10.6):",
    "Bakanlıkça sağlanan veri setleri yalnızca yarışma amacıyla kullanılır. Finalist olmayan takımlar "
    "15 gün, finalist takımlar Bakanlıkça aksi bildirilmedikçe 30 gün içinde bu verileri tüm cihaz, "
    "bulut, yedek ve geliştirme ortamlarından siler ve talep hâlinde silme beyanı sunar.")
sub("İdarenin kullanım hakkı (md.10.10):",
    "Katılımcılar; proje çıktılarının Bakanlıkça değerlendirilmesine, tanıtım amacıyla "
    "gösterilmesine ve kamu yararına yönelik pilot uygulama için ayrıca görüşülmesine muvafakat eder.")

# --- Teknik Teslim Taahhüdü (md.10.3) ---
blok("Teknik Teslim Taahhüdü (md.10.3)")
p("Finale kalınması hâlinde kaynak kodu, kurulum ve kullanıcı kılavuzu, teknik mimari ve veri modeli "
  "dokümanı, kullanılan kütüphane–lisans listesi, demo videosu ve bağımsız bir ortamda kurulup "
  "çalıştırılabilen uygulama paketi teslim edilecektir.")

# --- Kaynakça ---
blok("Kaynakça")
p("Rapordaki nicel ifadeler aşağıdaki kaynaklara dayanır. Metindeki köşeli parantez içi numaralar bu "
  "listeye atıf yapar. Kaynak niteliği açıkça belirtilmiş; birincil (bilimsel/resmî) ve ikincil "
  "(haber/sektör beyanı) kaynaklar ayrıştırılmıştır. Sistem sınırına duyarlı çevresel etki "
  "katsayıları, final öncesinde ilgili birincil kaynağın tam künyesiyle kesinleştirilecektir.")
p("Not — kaynak dürüstlüğü: Türkiye için yıllık ~1 milyon tonluk tekstil atığı bir sektör "
  "tahminidir; \"%1'inden azının geri dönüştürülmesi\" ise dünya geneli tekstilden tekstile geri "
  "dönüşüm oranıdır [1]. Uşak'a ilişkin kapasite rakamları sektör yetkililerinin basına "
  "yansıyan beyanlarına dayanır ve kaynağa/yıla göre günde ~1.700–2.716 ton aralığında değişir "
  "[3], [4].", italic=True, size=10.5)

KAYNAKLAR = [
    ("Ellen MacArthur Foundation (2017). A New Textiles Economy: Redesigning Fashion's Future. "
     "Cowes: EMF. — Dünya genelinde tekstilin %1'inden azının yeni tekstile geri dönüştürüldüğü "
     "verisinin birincil kaynağı. "
     "https://ellenmacarthurfoundation.org/a-new-textiles-economy"),
    ("Chapagain, A. K., Hoekstra, A. Y., Savenije, H. H. G. & Gautam, R. (2005). The Water "
     "Footprint of Cotton Consumption (Value of Water Research Report Series No. 18). Delft: "
     "UNESCO-IHE. — WWF'in ~2.700 L/tişört (≈250 g pamuk) figürünün dayandığı birincil su ayak izi "
     "verisi. https://www.waterfootprint.org/resources/Report18.pdf"),
    ("Anadolu Ajansı. Uşak'ta tekstil atıklarından geri dönüşümle 62 ülkeye ihracat. — Uşak: "
     "~1.700 ton/gün işleme, ~484.500 ton/yıl elyaf, ~750 milyon–1 milyar $ ekonomik katkı "
     "(sektör beyanı). https://www.aa.com.tr"),
    ("Ege İhracatçı Birlikleri. Türkiye'nin geri dönüşüm merkezi Uşak. — Alternatif kapasite "
     "figürleri (~2.716 ton/gün); rakam aralığının teyidi için. https://eib.org.tr"),
    ("Avrupa Komisyonu (2025). Ecodesign for Sustainable Products and Energy Labelling Working "
     "Plan 2025–2030 [COM(2025) 187, 16 Nisan 2025]. — Tekstil için DPP/ESPR delege düzenlemesinin "
     "~2027 kabulü ve 2028+ aşamalı uyumu (gösterge; henüz kabul edilmedi). "
     "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:52025DC0187"),
    ("Reverse Resources (Estonya, 2014). Pre-consumer tekstil atığı izleme ve eşleştirme SaaS "
     "platformu. https://reverseresources.net"),
    ("Swatchloop (Türkiye, 2022). Yapay zekâ destekli tekstil atığı yönetimi ve dijital ürün "
     "pasaportu (B2B). https://www.swatchloop.co — ayrıca: Anadolu Ajansı, Yeşilhat, "
     "\"Yapay zekâ destekli platformla tekstil atıkları uçtan uca yönetiliyor.\""),
    ("Atık Yönetimi Yönetmeliği (Resmî Gazete, 2 Nisan 2015, Sayı 29314). Tekstil üretim firesi "
     "(atık kodu 04 02 21 / 04 02 22) tehlikesiz atık sınıfındadır. "
     "https://www.resmigazete.gov.tr/eskiler/2015/04/20150402-2.htm"),
    ("Sıfır Atık Yönetmeliği (Resmî Gazete, 12 Temmuz 2019, Sayı 30829). "
     "https://www.resmigazete.gov.tr/eskiler/2019/07/20190712-9.htm"),
    ("T.C. Çevre, Şehircilik ve İklim Değişikliği Bakanlığı — Entegre Çevre Bilgi Sistemi (EÇBS). "
     "TABS, EÇBS altındaki atık beyan modülüdür. https://ecbs.cevre.gov.tr"),
    ("Akerlof, G. A. (1970). The Market for 'Lemons': Quality Uncertainty and the Market Mechanism. "
     "The Quarterly Journal of Economics, 84(3), 488–500. — Bilgi asimetrisinin piyasa verimliliğini "
     "bozduğunu ortaya koyan temel iktisat çalışması; projenin çekirdek problem tanımının kuramsal "
     "dayanağı. https://doi.org/10.2307/1879431"),
    ("Sandin, G. & Peters, G. M. (2018). Environmental impact of textile reuse and recycling — A "
     "review. Journal of Cleaner Production, 184, 353–365. — Tekstil yeniden kullanım ve geri "
     "dönüşümünün karbon/su etkilerine ilişkin birincil derleme; §10'daki çevresel katsayıların "
     "büyüklük mertebesinin dayanağı. https://doi.org/10.1016/j.jclepro.2018.02.266"),
    ("Du, W. vd. (2022). Efficient recognition and automatic sorting of waste textiles based on "
     "online near-infrared spectroscopy and convolutional neural network. Resources, Conservation "
     "and Recycling, 180, 106157. — Yakın kızılötesi tayfı ile evrişimli sinir ağını birleştiren "
     "otomatik lif tanımanın %97,1 doğrulukla uygulanabilir olduğunu gösteren birincil çalışma; "
     "§5'teki NIR yol haritasının fizibilite dayanağı. "
     "https://doi.org/10.1016/j.resconrec.2022.106157"),
]
for i, s in enumerate(KAYNAKLAR, 1):
    b = doc.add_paragraph()
    b.paragraph_format.left_indent = Inches(0.3)
    b.paragraph_format.first_line_indent = Inches(-0.3)
    r0 = b.add_run(f"[{i}] "); r0.bold = True; r0.font.size = Pt(10.5)
    b.add_run(s).font.size = Pt(10.5)

doc.save(OUT)
print("Kaydedildi:", os.path.abspath(OUT))
print("Paragraf sayısı:", len(doc.paragraphs), "| Tablo:", len(doc.tables))
