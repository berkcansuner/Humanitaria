# Frontend Denetimi & Geliştirme Yol Haritası — 2026-06-25

Canlı test (Playwright) + performans/erişilebilirlik ölçümü (Chrome DevTools Lighthouse + CWV)
+ UX/tasarım kod denetimi (web-design-guidelines & emil-design-eng skill'leri) sonuçları ve
önceliklendirilmiş yol haritası. **Bu denetimde kod DEĞİŞTİRİLMEDİ** (yalnız ölçüm + planlama).

**Genel sonuç:** Uygulama temel akışlarda **sağlam ve üretime yakın**. Otomatik erişilebilirlik ve
Best Practices skorları kusursuz (100/100). En yüksek getirili işler: (1) **atıf render bütünlüğü**
(ürünün çekirdek vaadi), (2) **klavye/odak erişilebilirliği** (Lighthouse'un göremediği gerçek WCAG AA
açıkları), (3) çok-satırlı composer ve "his" cilası. Audit'in iki iddiası (dark contrast, 44px touch
target) **ölçümle gevşetildi** (aşağıda).

---

## ✅ Uygulama Durumu (branch `feat/frontend-roadmap-p0`, yalnız yerel commit — push yok)

- **Tur 1 (P0) — commit `3375e63`:** ① atıf bütünlüğü (gruplar→çip, dangling→düz metin) · ② atıf klavye erişimi (Enter/Space) · ③ `:focus-visible` halkaları. TDD +11 test; canlı doğrulandı.
- **Tur 2 (P1) — commit `edb5fb7`:** ④ çok-satır composer (Enter gönder / Shift+Enter satır, auto-grow) · ⑤ reduced-motion + streaming `role="status"` + typing `scale(0)→scale(0.6)` · ⑦ `color-scheme` + `theme-color`. Canlı doğrulandı.
- **Tur 2 ek — commit `c85c8ba`, `9231254`:** ⑥ `:active` basış geri bildirimi (butonlar + prompt kartları) · diacritic-duyarsız konuşma araması (TDD +1 test, "guvenligi"→"güvenliği").
- **P2 cila:** ⑨ asistan yanıtı `max-width: 70ch` (okuma ölçüsü).
- **Item 8 (mobil sidebar dismiss):** GEREKSİZ — `.sidebar-backdrop` drawer'ı kullanıcı composer'a/prompt'a ulaşmadan zaten kapatıyor. P1-8 düşürüldü.
- **Kalan (hepsi P2 cila, sonraki tur):** skeleton + yük-hatası banner oto-kapatmayı kaldırma · **self-host font** (perf+gizlilik) · ölü footer linkleri (About/Privacy/Contact → `#`) · token sistemlerini birleştirme + off-grid px · aktif kaynak vurgusunu kalıcılaştırma · `/auth/me` console-401 gürültüsü · marketing modal a11y · React adası belgeleme.

**Tüm tur testleri yeşil: 74 frontend.** PR: [Humanitaria#2](https://github.com/berkcansuner/Humanitaria/pull/2).

---

## Test Kapsamı & Yöntem

| Araç | Kullanım |
|------|----------|
| Playwright MCP | Canlı fonksiyonel sürüş: auth, chat+SSE, çok dillilik, tema, mobil, greeting |
| Chrome DevTools MCP | Lighthouse (a11y/BP/SEO, desktop+mobile, navigation+snapshot) + Core Web Vitals trace |
| Skill: web-design-guidelines, emil-design-eng | Salt-okunur UX/tasarım kod denetimi (`file:line` kanıtlı) |

Sunucu: `uvicorn api.main:app` @ **port 8000** (build edilmiş SPA, tek-origin). Test kullanıcısı:
`frontend_audit@test.local` (signup ile). Pinecone **okuma** çalışıyor (default ns, 31.628 vektör).

---

## Faz 1 — Canlı Fonksiyonel Test

### ✅ Geçen akışlar (kanıt: screenshot + DOM ölçümü)
| Akış | Sonuç |
|------|-------|
| Landing (`/`) light + dark, tema toggle | ✅ render + `data-theme` light↔dark |
| Auth guard: girişsiz `/app` | ✅ → `/login?redirect=/app` |
| Signup → `/app` | ✅ httpOnly cookie, otomatik giriş |
| Login (e-posta/şifre) → `/app` | ✅ |
| **Chat EN** (Sudan) | ✅ SSE streaming, 3744 krk gerekçeli yanıt, 12 çip + 3 kaynak |
| **Chat TR** (Ukrayna) çok dillilik | ✅ akıcı Türkçe yanıt + 5 kaynak |
| Light/dark chat | ✅ ikisi de temiz kontrast |
| Mobil (390px) | ✅ hamburger drawer + tam-genişlik mesaj + composer |
| Greeting kısayolu ("merhaba") | ✅ sabit yanıt, **0 kaynak** (retrieval atlandı) |

### 🐞 Bulunan bug'lar
| ID | Önem | Bulgu | Kanıt | Kök |
|----|------|-------|-------|-----|
| **B1** | P0 | **Çoklu atıf grupları çipe dönüşmüyor**: `[1, 3, 4]`, `[1, 3, 4, 5]` düz metin kalıyor; yalnız tekli `[n]` yeşil çip oluyor. | Sudan yanıtında 9 grup düz metin; `renderMarkdown.js:11` regex `/\[(\d+)\]/g` tek sayı yakalıyor | `renderMarkdown.js:11` |
| **B2** | P0 | **Sarkan atıflar**: yanıt `[4]`/`[5]`'e atıf yapıyor ama yalnız 3 kaynak var → `#src-4/5` hiçbir yere gitmiyor. Aralıklı (Ukrayna 5/5 sağlıklıydı). | Sudan `danglingCitations:[4,5]`; B1 bunu besliyor (gruplar renumber'a girmiyor) | `renderMarkdown.js` + `renumberCitations.js` + `SourceList.isValidSource` |
| n1 | P2 | Footer About/Privacy/Contact ölü `#` linkleri | `AuthView`/marketing footer `url="…/#"` | marketing footer |
| n2 | P2 | Girişsizken `/auth/me` 401 → console'da hata gürültüsü (zararsız ama kirli) | her sayfa yükünde 1 console error | `authStore` refresh |
| n3 | P2 | Türkçe "merhaba" → İngilizce greeting (bilinçli template; çok dilli tutarlılık için gözden geçirilebilir) | greeting "Hello!…" | template (backend) |

### Bu turda sürülmeyen (düşük risk; takip önerilir)
Edit / Regenerate / Stop-mid-stream / sidebar rename-delete-search. Butonlar mevcut (snapshot +
kod denetimi doğruladı); resend/truncate yolu edit ile paylaşımlı. → Daha sonra smoke veya (atlanan)
**E2E test suite** ile kalıcı kapsama alınmalı.

---

## Faz 2 — Performans + Erişilebilirlik (ÖLÇÜM)

### Lighthouse
| Hedef | A11y | Best Practices | SEO | Agentic |
|-------|------|----------------|-----|---------|
| `/app` desktop navigation (boş) | **100** | **100** | 82 | 67 |
| `/app` desktop snapshot (gerçek yanıt, dark) | **100** | **100** | 60 | 50 |
| `/app` mobile navigation | **100** | **100** | 82 | 67 |

- **`color-contrast`: score 1 (GEÇTİ)** — gerçek dark yanıt metni + muted etiketler + çipler dahil.
- **`target-size`: score 1 (GEÇTİ)** — axe WCAG AA (≥24px) eşiği.
- SEO < 100: authed `/app` için meta açıklama/robots eksikleri (uygulama sayfası — düşük öncelik).

### Core Web Vitals (localhost, throttle yok)
- **LCP 389ms**, **CLS 0.00** — yerelde mükemmel.
- **Render-blocking:** ana CSS bundle (`index-*.css`, ~20KB, uvicorn http/1.1) + **Google Fonts** (harici
  origin, kritik yolda). Throttle altında ~**1181ms** tahmini LCP tasarrufu.
- **Bundle:** React adası `SuggestionCardIsland` = **150KB / 48.5KB gzip** (en büyük chunk) ama
  **code-split/lazy** → ilk yükü bloklamıyor (LCP iyi). Yalnız boyut/bakım maliyeti.

---

## Faz 3 — UX/Tasarım Denetimi (kod) + Ölçüm Düzeltmeleri

Skill tabanlı denetim P0–P2 bulguları `file:line` ile üretti. **Ölçümle yeniden derecelendirildi:**

- **✅ Doğrulandı ve yüksek (Lighthouse göremiyor):** odak halkaları yok (`:focus-visible`); atıf çipleri
  klavyeyle erişilemez; streaming `aria-live` granülaritesi; tek-satır composer; chat'te
  `prefers-reduced-motion` yok; `:active` basış geri bildirimi yok; typing `scale(0)`; `color-scheme`/`theme-color` yok.
- **⬇️ Ölçümle DÜŞÜRÜLDÜ:**
  - *Dark contrast (eski P1):* `color-contrast` ölçümle **geçti** → yalnız **izleme** (muted token'lar değişirse yeniden bak).
  - *Touch target ≥44px (eski P1):* axe `target-size` AA (24px) **geçti**; 44px AAA/konfor hedefi → **P2** (coarse-pointer konforu).

---

## Faz 4 — Önceliklendirilmiş Yol Haritası

> Efor: S(<½ gün) · M(½–1 gün) · L(çok-günlük). Tasarım yönü: **mevcut Humanitaria kimliğini koru, cilala.**

### 🔴 P0 — Doğruluk + erişilebilirlik (önce bunlar)
| # | İş | Dosya(lar) | Efor |
|---|----|-----------|------|
| 1 | **Atıf render bütünlüğü** (B1+B2): regex'i çoklu-grup yakalayacak şekilde genişlet (`[1, 3, 4]` → ayrı çipler); atıf numaralarını filtrelenmiş kaynak listesiyle uzlaştır → sarkan `[n]` kalmasın. *Ürünün çekirdek vaadi.* | `renderMarkdown.js:11`, `renumberCitations.js`, `SourceList.isValidSource` | M |
| 2 | **Atıf çiplerini klavyeyle erişilebilir yap** (Enter/Space) + `:target` highlight; mouse-only handler'a paralel. | `renderMarkdown.js`, `Chat.vue` (onCiteClick), `SourceList.vue` | M |
| 3 | **Görünür odak halkası**: tek global `:focus-visible` token'ı → composer, tüm input'lar, tüm ikon-butonlar. *En yüksek ROI a11y düzeltmesi.* | `style.css` + buton sınıfları | S |

### 🟠 P1 — Yüksek etkili UX
| # | İş | Dosya(lar) | Efor |
|---|----|-----------|------|
| 4 | **Çok-satırlı composer**: `<textarea>` auto-grow, Enter gönder / **Shift+Enter** yeni satır (pattern edit kutusunda zaten var). | `Chat.vue:65` | M |
| 5 | **Streaming duyurusu + reduced-motion**: `role="status"` "Generating…"; chat'e `@media (prefers-reduced-motion)` bloğu; typing `scale(0)`→`scale(0.6)`. | `Chat.vue`, `style.css` | S–M |
| 6 | **`:active` basış geri bildirimi + easing**: paylaşılan `scale(0.97)` + `--ease-out` token'ı (pressable sınıflar). *"His" için büyük kazanım.* | `style.css` + buton sınıfları | M |
| 7 | **`color-scheme` + `theme-color`**: `setTheme()` `documentElement.style.colorScheme`; `<meta theme-color>` toggle'da güncellensin. | `theme.js`, `index.html` | S |
| 8 | **Mobilde mesaj gönderince sidebar drawer kapansın** + empty-state geçişi. | `ChatView.vue`, `Chat.vue` (`sent` event) | M |

### 🟡 P2 — Cila / hijyen
| # | İş | Efor |
|---|----|------|
| 9 | Asistan yanıtına `max-width: 70ch` (okuma ölçüsü) | S |
| 10 | Aktif kaynak vurgusunu kalıcılaştır (sol accent border / outline) | S |
| 11 | Coarse-pointer'da ≥44px hit-area (`@media (pointer:coarse)`) | M |
| 12 | Conversation list / history için skeleton + yük-hatası banner'ını oto-kapatma | M |
| 13 | Ölü footer linkleri (n1) + `/auth/me` console-401 gürültüsü (n2) + greeting i18n (n3) | S |
| 14 | **Font'ları self-host et** (perf: render-blocking harici istek kalkar + gizlilik) | M |
| 15 | Token sistemlerini birleştir (`--color-*` vs marketing) + off-grid px temizliği | L |
| 16 | Empty-state prompt'larını config/endpoint'ten besle + aramada diacritic-folding | S |
| 17 | React adasını "bilinçli tek ada" olarak belgele; CSS'ini focus/motion referansı al (Vue port ileride) | S (belge) / L (port) |
| 18 | Marketing `SampleAnswerModal` a11y (aria-hidden + focus-trap) | M |
| 19 | Dark contrast: yalnız izle (ölçümle geçti) | — |

### Önerilen Sıralama
- **Tur 1 (P0, ~yarım gün):** odak halkaları (#3, S) + atıf bütünlüğü (#1, M) + atıf klavye (#2, M).
  `renderMarkdown`/`renumberCitations` birim testleri mevcut → TDD ile genişlet.
- **Tur 2 (P1 his + a11y):** çok-satır composer, reduced-motion + streaming duyurusu, `:active`, color-scheme.
- **Tur 3 (P2 cila):** measure, skeleton, self-host font, ölü link, token temizliği.
- **Tekrar değerlendir:** atlanan **E2E test suite** (Playwright) — atıf düzeltmeleri tam o render yolunu
  değiştirdiği için Tur 1 sonrası regresyon kilidi olarak yüksek değerli.

---

## Artefaktlar & Notlar
- Screenshot'lar repo kökünde: `01-landing-desktop.png` … `07-app-chat-mobile.png` + `.playwright-mcp/`.
  Commit edilmemeli (gitignore'a eklenebilir veya silinebilir).
- Test kullanıcısı + birkaç sohbet `conversations.db`'de kaldı (zararsız, dev verisi).
- Arka plan uvicorn (port 8000) hâlâ çalışıyor olabilir — incelemek isterseniz açık; istenirse durdurulur.
