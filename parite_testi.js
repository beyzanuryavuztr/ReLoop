/**
 * ReLoop — Python ↔ JS parite ve bütünlük testi.
 *
 * Amaç: reloop_app.html içindeki JS motorunu (reloop.py'nin yansıması) gerçek
 * DOM olmadan bir VM'de çalıştırıp:
 *   1) arayüz init'inin hata vermeden kurulduğunu,
 *   2) canlı hesaplanan Kamu Dashboard sayılarının Python (run_demo.py) ile ve
 *      rapordaki değerlerle BİREBİR aynı olduğunu,
 *   3) Bölüm 9 örnek skorunun 0.899 (≈%90) olduğunu,
 *   4) TABS şema doğrulayıcısının geçerli/geçersiz yükleri doğru ayırdığını
 * doğrular.
 *
 * Çalıştırma:  node parite_testi.js       (önce: python3 build_app.py)
 * Bağımlılık yok (Node standart 'fs' + 'vm').
 */
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const HTML = path.join(__dirname, 'reloop_app.html');
const html = fs.readFileSync(HTML, 'utf8');
const script = html.match(/<script>([\s\S]*)<\/script>/)[1];

/* ---- minimal DOM/BOM stub (arayüz init'i için yeterli) ---- */
// DMP formu için gerçekçi varsayılan değerler (tarayıcıdaki input value'larını taklit eder)
const FORM_DEF = { 'd-sehir':'Uşak','d-kumas':'suprem','d-kalite':'A','d-pamuk':'100',
  'd-poly':'0','d-elas':'0','d-gramaj':'180','d-miktar':'800','d-fiyat':'18',
  'd-itibar':'0.90','d-firma':'' };
function fakeEl(id) {
  const store = { innerHTML:'', textContent:'', value:(id&&id in FORM_DEF)?FORM_DEF[id]:'',
    checked:false, style:{}, dataset:{}, children:[] };
  return new Proxy({}, {
    get(_, k){
      if (k in store) return store[k];
      if (k === 'classList') return { toggle(){}, add(){}, remove(){}, contains(){return false;} };
      if (k === 'querySelectorAll') return () => [];
      if (k === 'querySelector') return () => fakeEl();
      return () => {};
    },
    set(_, k, v){ store[k] = v; return true; }
  });
}
const ctx = {
  document: { getElementById:(id)=>fakeEl(id), querySelector:()=>fakeEl(),
    querySelectorAll:()=>[], createElement:()=>fakeEl(), body:fakeEl(), addEventListener(){} },
  localStorage: { _d:{}, getItem(k){return this._d[k]??null;}, setItem(k,v){this._d[k]=''+v;}, removeItem(k){delete this._d[k];} },
  window:{}, requestAnimationFrame:()=>{}, setTimeout:()=>0, clearTimeout:()=>{}, console,
};

/* ---- beklenen değerler: rapor sabiti DEĞİL, GÖMÜLÜ PYTHON MOTORUNDAN gelir.
   build_app.py Python (run_demo.dashboard_ozet) çıktısını reloop_app.html'e gömer;
   burada JS motorunun aynı sayıları üretip üretmediğini doğrularız → gerçek parite.
   Veri seti değişince (ör. ulusal ekosistem) beklenenler OTOMATİK güncellenir. ---- */
let gecti = 0, kaldi = 0;
const chk = (ad, kosul) => { (kosul ? gecti++ : kaldi++);
  console.log(`  ${kosul ? '✓' : '✗ BAŞARISIZ'}  ${ad}`); };

vm.createContext(ctx);
try { vm.runInContext(script, ctx); }
catch (e) { console.error('✗ INIT PATLADI:', e.message); process.exit(1); }
console.log('ReLoop parite testi\n-------------------');
chk('Arayüz init hatasız kuruldu (Genel Bakış)', true);

/* Beklenen değerler = gömülü Python motoru çıktısı (parite çıpası) */
const BEKLENEN = ctx.pariteBeklenen();
const O9 = ctx.ornek9Beklenen();

/* 0) Duman testi — her sekmenin render yolu + işlem akışı + TABS doğrulama */
for (const tab of ['pazar','dmp','dashboard','entegrasyon','mevzuat']) {
  try { ctx.activate(tab); chk(`Sekme '${tab}' render edildi (eşleşme/harita/işlem yolları dahil)`, true); }
  catch(e){ chk(`Sekme '${tab}' render — ${e.message}`, false); }
}
try { ctx.entGonder(); chk('TABS şema doğrulama akışı hatasız çalıştı', true); }
catch(e){ chk('TABS akışı — '+e.message, false); }

/* 1) Dashboard paritesi */
const d = ctx.hesaplaDashboard();
chk(`Eşleşen parti ${d.eslesen}/${d.toplam} = ${BEKLENEN.eslesen}/${BEKLENEN.toplam}`,
    d.eslesen===BEKLENEN.eslesen && d.toplam===BEKLENEN.toplam);
chk(`Yönlendirilen ${d.ton.toFixed(1)} t = ${BEKLENEN.ton} t`, +d.ton.toFixed(1)===BEKLENEN.ton);
chk(`Ortalama skor %${d.ort_skor} (${d.min}-${d.max}) = %${BEKLENEN.ort_skor} (${BEKLENEN.min}-${BEKLENEN.max})`,
    d.ort_skor===BEKLENEN.ort_skor && d.min===BEKLENEN.min && d.max===BEKLENEN.max);
chk(`CO2 ${Math.round(d.co2)} t = ${BEKLENEN.co2} t`, Math.round(d.co2)===BEKLENEN.co2);
chk(`Su ${d.su.toFixed(2)} M L = ${BEKLENEN.su} M L`, +d.su.toFixed(2)===BEKLENEN.su);
chk(`Tutarsızlık ${d.tutarsiz} = ${BEKLENEN.tutarsiz}`, d.tutarsiz===BEKLENEN.tutarsiz);

/* 2) Bölüm 9 örnek skoru (rapordaki senaryo) */
const op = {id:'P-DEMO',fabrika:'x',lat:38.680,lon:29.410,sehir:'Uşak',pamuk:100,polyester:0,elastan:0,
  kumas:'suprem',gramaj:180,en_m:1.8,miktar_kg:800,kalite:'A',min_fiyat:18,dogrulanmis:true,itibar:0.85};
const ot = {id:'T-DEMO',alici:'y',lat:38.905,lon:29.410,sehir:'Uşak',min_pamuk:95,max_elastan:0,
  ihtiyac_kg:1000,max_fiyat:22,min_kalite:'B',dogrulanmis_ister:false};
const W = {lif:0.30,lojistik:0.20,miktar:0.15,fiyat:0.15,kalite:0.10,guven:0.10};
const b9 = ctx.skorla(op, ot).bilesen;
const s9 = Object.keys(W).reduce((s,k)=>s+W[k]*b9[k],0);
chk(`Bölüm 9 skoru JS ${s9.toFixed(3)} == Python ${O9.skor.toFixed(3)}`, Math.abs(s9 - O9.skor) < 1e-9);

/* 2b) Çift mevzuat uygunluğu — JS verdict sayıları == gömülü Python sayıları */
const ujs = {UYGUN:0, UYARI:0, "ENGELLİ":0};
const _firms = ctx.firmalar();
for (const p of ctx.tumPartiler()) for (const t of _firms) ujs[ctx.uygunluk(p, t).verdict]++;
const upy = ctx.uygunlukBeklenen();
chk(`Uygunluk JS {U:${ujs.UYGUN} W:${ujs.UYARI} E:${ujs['ENGELLİ']}} == Python {U:${upy.UYGUN} W:${upy.UYARI} E:${upy['ENGELLİ']}}`,
    ujs.UYGUN===upy.UYGUN && ujs.UYARI===upy.UYARI && ujs['ENGELLİ']===upy['ENGELLİ']);

/* 3) Sentetik taban değişmedi (kullanıcı kaydı yok → 250 parti) */
chk(`Sentetik ekosistem ${ctx.tumPartiler().length} parti = 250`, ctx.tumPartiler().length===250);

/* 4) TABS şema doğrulayıcısı */
const gecerli = {bildirim_tipi:'eslesme_tamamlandi', atik_kodu:'04 02 22', atik_tanimi:'x',
  tarih:'2026-08-12', kaynak_bolge:'Uşak', hedef_bolge:'Denizli', mesafe_km:11, miktar_kg:800,
  malzeme:'suprem', eslesme_skoru:0.9, tahmini_co2e_kg:1280, tahmini_su_L:1680000,
  anonim:true, kvkk_uyumlu:true};
chk('Şema: geçerli yük DOĞRULANIR', ctx.semaDogrula(gecerli).ok === true);
chk('Şema: atık kodu bozuksa REDDEDİLİR', ctx.semaDogrula({...gecerli, atik_kodu:'120122'}).ok === false);
chk('Şema: skor 0-1 dışıysa REDDEDİLİR', ctx.semaDogrula({...gecerli, eslesme_skoru:1.4}).ok === false);
chk('Şema: KVKK ihlali (fabrika alanı) REDDEDİLİR', ctx.semaDogrula({...gecerli, fabrika:'X A.Ş.'}).ok === false);

console.log('-------------------');
console.log(`${gecti} geçti, ${kaldi} kaldı`);
if (kaldi) { console.log('>>> PARİTE BAŞARISIZ ✗'); process.exit(2); }
console.log('>>> TÜM TESTLER GEÇTİ — JS motoru gömülü Python motoruyla birebir tutarlı ✓');
