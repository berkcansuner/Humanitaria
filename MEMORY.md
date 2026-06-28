# MEMORY — ReliefWeb RAG (oturum sürekliliği)

> **Her oturum başında bu dosyayı oku. Her önemli ilerlemeden sonra güncelle.**
> Bu bir tarihçe değil — GÜNCEL durumu yansıtır. Eskiyen satırları sil/değiştir.
> "Nerede kalmıştık?" sorusunun cevabı burasıdır.

**Son güncelleme:** 2026-06-27

---

## 📍 NEREDE KALMIŞTIK (10 saniyelik özet)

**🌐 ARTIK CANLI YAYINDA: https://humanitaria.onrender.com** (Render ücretsiz Docker; servis adı `humanitaria`, id `srv-d8uo70ernols73fgenr0`, bölge frankfurt). Uygulama sağlıklı: Gemini `gemini-2.5-flash` (chat) + `gemini-embedding-001` (3072) + Pinecone (default namespace, **31.628 vektör**) — tamamen bulut. Vue 3 SPA, zorunlu giriş (Google + e-posta/şifre), **Humanitaria** markası. GitHub: **`berkcansuner/Humanitaria`** (master = origin, güncel).

**Bu seansta (2026-06-27) bitirilen — frontend P2 cilası + citation prompt (PR #3 MERGED → master, Render deploy):** self-host font (`@fontsource`, Google Fonts `<link>` kaldırıldı) · liste/geçmiş skeleton (paylaşılan `.skeleton` shimmer) · `/auth/me` 401→200 (anonim'de 200+`null`) · citation menzil-dışı `[n]` kısıtı. 4 commit (`6d20c73`,`2874796`,`ce47b9b`,`8ae82f7`), TDD, **340 backend + 76 frontend yeşil**, canlı doğrulandı (Chrome DevTools). **Token birleştirme ARTIK YAPILDI** (ayrı seans, commit `608a043` → master'a merge+push, Render auto-deploy — bkz. aşağıdaki CSS token isim birliği bölümü). Detay: aşağıdaki 2026-06-27 bölümü.

**Bu seansta (2026-06-27, admin paneli) — yeni özellik turu başladı:** sadece sahibe (`ADMIN_EMAILS`) açık **ingestion durum & yönetim paneli** (`/admin/ingestion`): son/sonraki run, Pinecone vektör sayısı, scheduler durumu + "şimdi çek" butonu. `threading.Lock` ile zamanlı/manuel ingest asla örtüşmez. **352 backend + build yeşil**, adversarial review (3 boyut) geçti. Commit `ec67b5b` → **[PR #4](https://github.com/berkcansuner/Humanitaria/pull/4) AÇIK** (manuel e2e + merge kullanıcıda). Yol haritası kalanı (M&E analiz, RAG kalite cilası, sohbet export/paylaş) sonraki PR'lar. **Panele veri-kırılımı (breakdown) eklendi** (kaynak/ülke/tarih/tema/format; aktif namespace `list`+paralel `fetch` taraması ~4dk, cache'li, `(other)` yerine "top N / M" notu, yıl barları). **Kullanıcı: sistemde sadece SON 5 YIL kalsın** → `prune_old_vectors.py --before 2021-06-28` (5.910 rapor / 7.197 chunk, default ns) denendi AMA **Pinecone yazma kotası silmeyi de blokluyor (429, "write unit limit")** → **1 TEMMUZ'a ERTELENDİ** (hiç vektör silinmedi, index sağlam). Gösterim şimdiden temiz: "before 2021" gruplaması + `INGEST_LOOKBACK_YEARS=5`. PR #4 = 6 commit. Detay: aşağıdaki admin paneli bölümü.

**Bu seansta (2026-06-26) bitirilen — production'da 4 canlı bug fix + temizlik:** Kullanıcı canlı deploy'da Google girişinde "Internal Server Error" aldı; arkasından 4 AYRI kök neden çıktı, her biri logdan/canlı testten kanıtlanıp çözüldü: **(1)** Google login 500 → callback `authorize_access_token` Google JWKS'i `www.googleapis.com`'dan çekiyordu (Render bölgesinden **403**); callback **userinfo endpoint**'ine çevrildi (`acba8a9`). **(2)** "Google login is not configured" 503 → yanlış/bayat servise deploy; doğru servise (id ile) redeploy. **(3)** chat "No response received" → **Render Frankfurt IP'si Gemini host'undan engelli** (anahtar geçerli, IP engelli); **Cloudflare AI Gateway** ile aşıldı (`GEMINI_BASE_URL` env, kod değişmez). **(4)** ölü `[2][3][4][5]` atıflar → kaynağı olmayan `[n]`'ler artık siliniyor (`11a4f23`+`dbd4f5c`). **Kopya `reliefweb-rag` servisi (srv-d8te) SİLİNDİ** → tek temiz servis kaldı. Detay: aşağıdaki 2026-06-26 bölümü. (Önceki seans 2026-06-25: frontend yol haritası P0/P1/P2 merge, PR #2.)

**SIRADAKİ — açık başlıklar (öncelik sırasıyla):**
1. **🔴 KULLANICININ MANUEL İŞİ — sızan kimlikleri rotate et:** **Render API key** + **Google client secret** (bu seansta sohbete düz metin yapıştırıldı; değerler memory'ye YAZILMADI). Kullanıcı "Render key'i sonra manuel değiştireceğim" dedi → Render Dashboard → API Keys revoke+yeni; Google Console'da yeni secret → Render `GOOGLE_CLIENT_SECRET` güncelle.
2. **🔴 EN BÜYÜK AÇIK DEV İŞİ — Pinecone write-kotası TIKALI; kota 2026-07-01'de yenilenir** (dashboard-onaylı: "Writes paused until July 1, 2026"). v2 rollout **8/10 ülkede** kaldı (Palestine + Ukraine eksik); index 3 namespace birden tutuyor (v2 68.936 + default 31.628 + pilot 4.892 = ~1.51 GB / 2 GB free, **~%75**). **1 Temmuz'da/sonrasında:** v2'yi tamamla → 10-ülke A/B → **cutover** (`PINECONE_NAMESPACE=v2`) → eski `default`+`pilot` temizliği (depolama ~%55'e iner). **Tam prosedür plan dosyasında park edildi** (`~/.claude/plans/nerede-kalm-t-k-noble-star.md`); 1 Temmuz hatırlatıcısı kuruldu.
3. ~~**Ertelenen frontend yapısal P2 — token birleştirme**~~ → **YAPILDI (2026-06-27, commit `608a043` → master'a MERGE+PUSH, Render auto-deploy):** marketing `.mkt-scope` token'ları chat `--color-*`/`--font-*` adlandırmasına taşındı, farklı değerler scoped override olarak KORUNDU → **sıfır görsel değişiklik** (computed-value ile kanıtlandı). Yalnız `marketing.css`+`AuthView.vue`; chat dokunulmadı. 76 frontend test yeşil. ("200+ px" notu abartıydı → gerçekte ~30 tam-eşleşen tek-değer çevrildi.)
4. **(Opsiyonel)** Cloudflare gateway'e `cf-aig-authorization` ekleme. **(Citation prompt cilası — menzil-dışı `[n]` kısıtı — 2026-06-27'de YAPILDI, PR #3.)**

---

## ✅ Bu seansta UYGULANAN — Admin ingestion paneli (2026-06-27, branch `feat/admin-ingestion-panel` → PR #4 AÇIK)

Kullanıcı yeni özellik turu başlattı; önceliklendirme (4 alan: RAG kalitesi, sohbet/UX, M&E analiz, ingestion yönetimi) → **ilk kilometre taşı: admin-only ingestion paneli** (kalanlar sonraki PR'lar). Plan-mode'da tasarlandı (Explore×3 keşif + Plan ajanı), tam testli, 3-boyutlu adversarial review'dan geçti.

**Ne yapıldı (16 dosya, +851):**
- **Admin kavramı (DB şeması YOK):** `config.ADMIN_EMAILS` allowlist + `api/routes/auth.py` `get_admin_user` dependency (anon→401, non-admin→403); `is_admin` `UserOut`'a eklendi, tek `_user_out` helper'ı login/signup/me üçünde de **sunucuda hesaplar** (client'a güvenilmez).
- **`ingestion/runner.py` (YENİ):** `threading.Lock` örtüşme guard'ı + bellek-içi `RunState`. Zamanlanmış job (APScheduler thread) **ve** manuel tetikleme (`anyio.to_thread` worker) aynı kilidi paylaşır → asla örtüşmez. `scheduler._run_scheduled_ingest` artık runner'a delege eder; runner `sched.run_pipeline`'ı çağırır → **mevcut scheduler testleri değişmedi**.
- **`api/routes/admin.py` (YENİ):** `GET /admin/ingest/status` (son ingest=watermark, sonraki run=APScheduler `next_run_time`, Pinecone vektör sayısı=`describe_index_stats`, scheduler durumu, son-run `IngestionStats`) + `POST /admin/ingest/trigger` (202; çalışıyorsa 409; fire-and-forget task `_bg_tasks` ile referanslı). `main.py`: admin router + `app.state.ingest_scheduler`.
- **Frontend:** `/admin/ingestion` route + `requiresAdmin` guard (`authStore.isAdmin()`); `AdminIngestionView.vue` (durum kartı + "şimdi çek" + poll-while-running + 403/409 işleme); Sidebar'da koşullu kalkan linki (`v-if auth.user?.is_admin`); `api.js` `request()` export → `adminApi.js`. `.env.example`'a `ADMIN_EMAILS`.

**Doğrulama:** **352 backend** (yeni: admin 403/401/200 + status şekli, runner concurrency guard, config default) + `npm run build` temiz (panel ayrı lazy chunk). **Adversarial review (backend/security/frontend):** güvenlik **0 bulgu** (gate uçtan uca doğrulandı, defense-in-depth), 1 orta (poll başarı yolunda `actionError` temizlenmiyor → kalıcı banner) + 2 düşük **giderildi**. **Manuel e2e BEKLİYOR (kullanıcı):** `.env`'e `ADMIN_EMAILS=<email>` → API restart → login → kalkan linki (admin olmayanda yok) → panel → "şimdi çek" → Running→Idle. Commit `ec67b5b` → [PR #4](https://github.com/berkcansuner/Humanitaria/pull/4) AÇIK (merge YOK). **Kapsam-dışı follow-up:** kalıcı çalışma geçmişi (SQLite `ingest_runs`), tetikleme parametreleri (limit/tarih/full-refresh), ülke-tema dashboard'ları + M&E/RAG/export turları.

---

## ✅ Bu seansta UYGULANAN — Frontend P2 cilası + citation prompt (2026-06-27, branch `feat/frontend-p2-polish` → PR #3 MERGED (rebase) → master, branch silindi)

Kullanıcı "nerede kalmıştık" → frontend yol haritası P2'lerinden 3'ü + citation prompt (item 3→4). **Token birleştirme bilinçli ERTELENDİ** (kullanıcı kararı: L refactor, ~%80 çakışan iki token sistemi + marketing.css 200+ hardcoded px, yüksek görsel regresyon riski, sıfır kullanıcı-görünür değişiklik → kendi PR'ına). 4 commit, TDD'li, hepsi canlı doğrulandı (**340 backend + 76 frontend yeşil**):
- **`6d20c73` /auth/me 401→200:** yeni `get_optional_user` (raise YOK); `get_current_user` ona delege eder → diğer route'lar 401'de kalır; `/me` → `Optional[UserOut]`, anonim'de 200+`null`. Frontend `refresh()` zaten null'u doğru işliyordu → yalnız test güncellendi (TDD red→green). Canlı: `curl /auth/me` → 200 + null.
- **`2874796` self-host font:** Google Fonts `<link>` (+2 preconnect) `index.html`'den kaldırıldı → `@fontsource-variable/dm-sans` + `@fontsource/inter` (400/600) + `@fontsource/ibm-plex-mono` (400/500/600), main.js import. DM Sans family **"DM Sans Variable"** (style.css + marketing.css 2 token rename); Inter/IBM statik (family aynı). DM Sans italic kullanılmıyor + Inter italic zaten faux → italic import yok. Canlı: **0 googleapis isteği**, lokal woff2; opsz size-responsive bırakıldı (weight'ler tam).
- **`ce47b9b` skeleton:** paylaşılan `.skeleton` shimmer utility (style.css; `--color-surface-container*` ile tema-duyarlı; global reduced-motion bloğu otomatik durdurur). Liste: `ChatView.isLoadingConversations` → Sidebar → ConversationList (`v-if="loading && !groups.length"` → yalnız ilk yük, refresh flicker yok). Mesaj geçmişi: `Chat.vue.isLoadingMessages` (watcher stale mesajları temizler). Canlı: liste shimmer screenshot'ta yakalandı (initScript ile /conversations geciktirildi).
- **`8ae82f7` citation prompt:** `chain.py` kural 6a'ya "yalnız Context'te görünen [n]'leri kullan, menzil dışı yazma" eklendi + guard test (rule-9 testi deseni). Canlı: Syria sorgusu → yanıt **[1]-[5] hepsi 5 kaynağa eşleşiyor, ölü/uydurma atıf yok**.

**Doğrulama:** uvicorn :8010 + Chrome DevTools MCP (signup→/app→gerçek RAG sorgusu). Dev test kullanıcısı `p2verify@test.local` + yetim sohbeti sonradan lokal `conversations.db`'den SİLİNDİ (diğer test kullanıcılarına dokunulmadı). **[PR #3](https://github.com/berkcansuner/Humanitaria/pull/3) MERGED (rebase) → master** (`e8e0934..7e03c70`); branch silindi; Render production auto-deploy tetiklendi. Yukarıdaki branch SHA'ları (`6d20c73` vb.) rebase'de master'da yeni SHA aldı.

---

## ✅ Bu seansta UYGULANAN — Frontend P2: CSS token isim birliği (2026-06-27, commit `608a043` → master, PUSH'LANDI, Render auto-deploy)

Kullanıcı "ertelenen frontend P2'yi ele alalım" dedi → token birleştirme (yol haritası item 3). **Plan-mode'da 2 karar netleşti:** (1) hedef = **görünmez temizlik** (yalnız isim birliği, değerler korunur; "gerçek değer birliği" REDDEDİLDİ — landing'i görünür değiştirir); (2) px = **yalnız tam-eşleşen tek-değerliler**.

**Kritik keşif:** iki sistem kavramsal ~%70 örtüşse de DEĞERLER bağımsız ayarlanmış (marketing prototipten birebir): buton yeşili marketing `oklch(0.40)` vs chat `oklch(0.52)`; muted marketing nötr-gri `#8a857e` vs chat sıcak-kahve `#8e706b`; max-width 1160 vs 1280; dark'ta tüm yüzeyler hafif farklı → değer-merge görsel regresyon demek. Bu yüzden **isim birliği + scoped override**.

**Uygulanan (yalnız 2 dosya; chat'in 11 dosyası/165 ref DOKUNULMADI):**
- `marketing.css`: `.mkt-scope` token tanımları + 85 `var()` kullanımı → `--color-*`/`--font-*`. Marketing'in farklı değerleri `.mkt-scope` scoped override olarak korundu. `--color-text` override DROP (her iki modda `:root` ile birebir → miras). `--maxw`→`--content-max-width:1160px` override. Marketing-özel → `--color-border-strong`/`--color-ink`/`--color-ink-2` (hâlâ `.mkt-scope`-scoped). Fontlar global `--font-display/body/mono`'ya bağlandı (tek önemsiz fark: `-apple-system` fallback kazandı; `system-ui` zaten önde, aynı render).
- `AuthView.vue`: `<style scoped>` 15 token kullanımı aynı şekilde. Hardcoded `#ba1a1a` (error) DOKUNULMADI — chat `--color-error` dark'ta `#ffb4ab`, substitution görünür değiştirirdi.
- **px:** yalnız tam-eşleşen tek-değerli spacing/radius → token (`gap:24px`→`--space-5`, `border-radius:12px`→`--radius-xl`, `padding:24px`→`--space-5`...). ~30 dönüşüm. Çok-değerli shorthand (`64px 48px`, `96px 0 64px`), font-size, tuhaf değerler (11px/13px/9px radius) bilinçli RAW.

**Doğrulama (sıfır görsel değişiklik KANITLANDI):** Chrome DevTools, refactor ÖNCESİ+SONRASI computed değerler — 19 light + 15 dark token byte-identical; tüm resolved sample stiller (renk→rgb/oklch, spacing/radius px, maxWidth) birebir (landing+auth, light+dark). [Tek anomali: before-dark `btn-solid` bg'si transition-ortası ölçüm artefaktıydı; settled = token = aynı, ayrıca kanıtlandı.] Grep guard: öneksiz token **0**. **76 frontend test yeşil, vite build temiz.** Görsel: landing+auth her iki temada kusursuz.

**Entegrasyon:** master'a fast-forward merge + push edildi (kullanıcı kararı) → Render production auto-deploy tetiklendi; feature branch silindi. **Bilinçli ERTELENEN kalan:** "gerçek değer birliği" (görsel redesign) + tuhaf/çok-değerli px tokenizasyonu (düşük değer, tek-kullanımlık token riski).

---

## ✅ Bu seansta UYGULANAN — Production'a alış + 4 canlı bug fix (2026-06-26, master'a PUSH + Render canlı)

Kullanıcı **canlı Render deploy**'unda (ilk kez bu seansta devreye alındı) Google girişinde "Internal Server Error" raporladı. Tek belirti **4 ayrı kök neden**di; sırayla çözüldü. **Teşhis yöntemi (tekrar kullan):** Render `/v1/logs` API'sinden gerçek traceback çek (`ownerId`+`resource=srv-...`); şüpheli host'u **kendi IP'nden** anahtarla test et → IP-engeli mi key/proje mi ayrılır.

**İki servis tuzağı:** Hesapta neredeyse aynı isimli İKİ servis vardı — `humanitaria` (srv-d8uo → humanitaria.onrender.com) ve `Humanitaria` (srv-d8te → reliefweb-rag.onrender.com). İlk düzeltme yanlışlıkla yanlış servise gitti (script `name -match` + `First 1`). **Ders: çok servis varsa id ile hedefle.** Sonunda kullanıcı **humanitaria.onrender.com**'u seçti → env'ler srv-d8uo'ya taşındı, srv-d8te SİLİNDİ.

1. **Google login 500** (`c540850` callback hardening + `acba8a9` userinfo): `api/routes/auth.py` `authorize_access_token()` token exchange'i başarıyla yapıyor AMA sonra `id_token` imzasını doğrulamak için Google JWKS'i (`www.googleapis.com/oauth2/v3/certs`) çekiyor → Render bölgesinden **403** → ham 500. Fix: yeni `_google_userinfo()` helper — state doğrula + kod→token exchange + profili **userinfo endpoint**'inden (`openidconnect.googleapis.com`, erişilebilir) al, JWKS'i TAMAMEN atla. Callback artık `try/except` ile 500 yerine `/login?error=google`'a düşer + sebebi loglar.
2. **"Google login is not configured" 503:** doğru servisteki çalışan instance bayattı (OAuth client import anında `get_settings()` lru_cache ile okunuyor; env bir an boşken başlamış). Fix: doğru servisi redeploy → taze instance.
3. **Chat "No response received"** (frontend `Chat.vue` `empty_response`): Render logunda Google'ın GENEL 403 HTML'i (`/v1beta/openai/embeddings`+`/chat/completions`). Aynı GEMINI_API_KEY benim IP'mden 200, Render'dan 403 → **Render Frankfurt çıkış IP'si `generativelanguage.googleapis.com`'dan engelli** (anahtar/proje değil; auth host'ları engelli değildi, o yüzden login çalıştı). **Fix: Cloudflare AI Gateway (transparent proxy).** Render env'e tek değişken: `GEMINI_BASE_URL=https://gateway.ai.cloudflare.com/v1/<ACCT>/gemini/google-ai-studio/v1beta/openai/` (model adları AYNI; **kod değişmez; YEREL dev hâlâ doğrudan Gemini URL'sini kullanır**). `/compat` endpoint'i de çalışıyor ama `model: google-ai-studio/<m>` prefix'i gerektirir → transparent proxy seçildi.
4. **Ölü `[n]` atıflar** (`11a4f23` backend + `dbd4f5c` frontend): model, gösterilebilir kaynağı olmayan numara atıyordu (over-citation/hallucination veya country-artifact/url'siz doc). Backend `_build_context_and_sources` artık yalnız **gösterilebilir** doc'ları (`_is_displayable_source` = url+title, country-index-artifact değil) numaralıyor; frontend `renumberCitations`+`renderMarkdown` kaynağı olmayan `[n]`'leri **siliyor** (boşluğuyla) + history-load'da da renumber. **339 backend + 75 frontend test yeşil.**

**Sonuç:** dört sorun da çözüldü, kopya servis silindi, tek canlı servis humanitaria.onrender.com. **Kullanıcının manuel işi:** Render API key + Google secret rotate (sızdı).

---

## ✅ Bu seansta UYGULANAN — Frontend denetimi + yol haritası P0/P1/P2 (2026-06-25, MERGED → master PR #2)

Kullanıcı "MCP + skill'lerle frontend'i test et, geliştirmeleri incele, yol haritası çıkar" dedi.
Playwright (fonksiyonel) + Chrome DevTools Lighthouse/CWV (ölçüm) + skill tabanlı UX denetimi (web-design-guidelines,
emil-design-eng) yürütüldü. Önce salt-denetim → yol haritası dokümanı (`docs/frontend-audit-roadmap-2026-06-25.md`, P0/P1/P2, efor/etki); sonra aşağıdaki turlarda uygulandı.

- **Sağlık:** Tüm çekirdek akışlar PASS — landing light/dark, auth guard/signup/login, EN+TR chat (SSE, kaynaklar,
  çok dillilik), mobil 390px reflow, greeting (retrieval atlanıyor). Lighthouse **a11y 100 + BP 100** (desktop+mobile,
  gerçek dark yanıt dahil); `color-contrast` & `target-size` ölçümle GEÇTİ. CWV: LCP 389ms / CLS 0.00 (localhost).
- **2 GERÇEK BUG (canlı bulundu, P0):** (B1) çoklu atıf grupları `[1, 3, 4]` çipe DÖNÜŞMÜYOR, düz metin kalıyor
  (`renderMarkdown.js:11` regex `/\[(\d+)\]/g` yalnız tek sayı yakalıyor); (B2) **sarkan atıflar** — yanıt `[4]`/`[5]`'e
  atıf ama 3 kaynak (B1 besliyor; aralıklı — Ukrayna 5/5 sağlıklıydı). Fix: `renderMarkdown.js`+`renumberCitations.js`+`isValidSource`.
- **Audit'in 2 iddiası ölçümle DÜŞÜRÜLDÜ:** dark contrast (ölçüm geçti → yalnız izle); 44px touch target (axe AA 24px geçti → P2 konfor).
- **En yüksek getirili işler:** atıf bütünlüğü (P0) · görünür `:focus-visible` halkaları (P0, S, en yüksek ROI) · atıf
  klavye erişimi (P0) · çok-satır composer Shift+Enter (P1) · `:active`/reduced-motion/`color-scheme` (P1) · self-host font (perf).
- **Perf:** render-blocking ana CSS + Google Fonts (~1181ms tahmini LCP); React adası `SuggestionCardIsland` 150KB/48.5KB-gzip ama lazy (ilk yükü bloklamıyor).
- Temizlik tamam: kanıt screenshot'ları + `.playwright-mcp/` silindi, uvicorn durduruldu, çalışan ağaç temiz. Test kullanıcısı `frontend_audit@test.local` `conversations.db`'de kaldı (zararsız dev verisi).

**Yol haritası UYGULANDI → MERGED master (PR #2, rebase; branch `feat/frontend-roadmap-p0` silindi):**
- **Tur 1 P0 (`3375e63`):** atıf bütünlüğü (`renderMarkdown`/`renumberCitations` grup genişletme + yeni `utils/sources.js` paylaşılan `isValidSource` → gruplar çip, dangling düz metin) · atıf klavye (`onCiteKeydown`) · global `:focus-visible` halkaları (`--focus-ring`). TDD +11 test. Canlı: 0 ham grup, 0 dangling çip, 24 çip→3 kaynak, Enter→flash.
- **Tur 2 P1 (`edb5fb7`):** çok-satır `<textarea>` composer (Enter gönder/Shift+Enter satır, `autoGrow`) · `theme.js` `colorScheme` + `theme-color` meta · `prefers-reduced-motion` bloğu + streaming `role="status"` + typing `scale(0)→0.6`. Canlı doğrulandı.
- **P2:** asistan `max-width:70ch`. **Item 8 (mobil-dismiss) GEREKSİZ** — backdrop zaten kapatıyor.
- **Tur 2 ek (`c85c8ba`,`9231254`):** ⑥ `:active` press feedback (global ikon-buton kuralı + send-btn scale) + diacritic-duyarsız konuşma araması (`conversationOps._fold`, NFD+strip, TDD).
- **Test: 74 frontend** yeşil (62→74). Yol haritası: `docs/frontend-audit-roadmap-2026-06-25.md`.
- **PUSH'LANDI → [PR #2](https://github.com/berkcansuner/Humanitaria/pull/2).** Repo **`reliefweb-rag`→`Humanitaria`** yeniden adlandırıldı; `origin` URL **Humanitaria'ya güncellendi** (`git remote set-url`) + docs/render.yaml referansları da. **MERGED → master** (PR #2, rebase, 2026-06-25). Yukarıdaki commit ref'leri branch-öncesi SHA'lar; rebase'de master'da yeni SHA aldılar.
- **Tur 3 P2 cila (`16af40e`,`5f3c4a3`):** ölü footer linkleri→gerçek route, marketing modal a11y (`aria-hidden` açık-durumu yansıtır + focus + Tab trap), **kalıcı aktif-kaynak sol-accent bar** (SourceList `.active` + Chat scrollToCitedSource), React adası belgelendi. Test **74** yeşil.
- **Bilinçli ERTELENEN (yapısal, "cila" değil):** self-host font (binary asset), token sistemlerini birleştirme (L refactor), liste/geçmiş skeleton, `/auth/me` 401→200 (backend+test değişikliği).

---

## ✅ Bu seansta UYGULANAN — Canlı test + 8 iş kolu geliştirme (2026-06-24, MERGED → origin/master, PR #1)

Kullanıcı "canlı test et → geliştir" dedi. **Canlı test P0 buldu:** chat modeli `gemini-3.5-flash`
kronik **503 "high demand"** → uygulama hiçbir RAG sorusuna cevap veremiyordu (embedding/Pinecone/
query-proc sağlıklıydı; tek kırılma chat modeliydi; MEMORY'de 17 gün önce de aynı 503). Plan onaylandı
(4 alan), 8 iş kolu uygulandı (hepsi test + canlı doğrulandı):

- **İK1 Güvenilirlik (P0):** chat modeli → **`gemini-2.5-flash`** (config.py + .env + tüm docs;
  reasoning_effort=low 2.5-flash'te çalışıyor). Non-stream `/chat`'e `_ainvoke_with_retry` (transient
  503 retry) + `_is_high_demand` helper (stream+non-stream paylaşır). Geniş `except→503` daraltıldı:
  busy→503 net mesaj, beklenmeyen→`logger.exception`+**500**. **Canlı: EN+TR chat 200 + 5 kaynak.**
- **İK2 Güvenlik:** auth signup/login **rate-limit** (yeni paylaşılan `api/limiter.py` — chat↔auth
  circular import'tan kaçınmak için; `AUTH_LOGIN_RATE_LIMIT=5/min`, `AUTH_SIGNUP_RATE_LIMIT=3/min`).
  **Canlı: login #6→429.** Login **timing-attack** fix (`users.DUMMY_PASSWORD_HASH` — kullanıcı yoksa da
  bcrypt çalışır). Ölü config temizliği (.env'den CHROMA_*/OLLAMA_*/*_PROVIDER; config'ten kullanılmayan
  `API_KEY`). **+ yan-bug:** `.env` `CHUNK_SIZE=800/100` eski word-count kalıntısıydı → **1500/200** (config
  intent'i; ingest kotada bloklu, anlık etki yok ama gelecekteki ingest doğru chunk üretir).
- **İK3 RAG kalitesi:** MMR/aday-havuzu/truncate A/B (`eval_rag.py --metrics`, 15 etiketli sorgu).
  **3 varyant da baseline'dan KÖTÜ** (havuz×8+fetch40 → nDCG 0.351; fetch40 MMR-div → 0.273; truncate=START
  → recall düştü). → **KOD DEĞİŞİKLİĞİ YOK; default'lar optimal** (baseline recall@5=**0.224** MRR=**0.672**
  nDCG=**0.426**). Audit'in "büyük havuz→recall" hipotezi YANLIŞ; reranker dar/alaka-odaklı havuzla daha iyi.
  Gerçek lever hâlâ v2 namespace cutover (Pinecone kotası bloklu).
- **İK4 Test & UX:** `apply_date_filter` (testsizdi, 5 test) + `chat_stream` busy-503 testi + non-stream
  resilience testleri. **Frontend:** session-expiry **401→/login yönlendirme** (`authStore.handleSessionExpired`,
  api.js request() + Chat.vue stream); sessiz sidebar hataları → görünür banner (ChatView); a11y aria-label'ları
  (chat input, mesaj balonu role/aria, edit textarea). EmptyState i18n ATLANDI (UI bilinçli İngilizce).

**Test: 335 backend (+13) + 62 frontend (+1) yeşil. Build OK.** **MERGED → origin/master** ([PR #1](https://github.com/berkcansuner/Humanitaria/pull/1), rebase; commit'ler `acba6fe..1a0f21e`). `.env` değişiklikleri (model + CHUNK_SIZE 1500/200 + ölü anahtar temizliği) gitignored → yerel; `.env.example` commit'lendi.
Canlı test kullanıcısı `claude_smoke@test.local` + birkaç sohbet conversations.db'de kaldı (zararsız).

---

## 🚀 DEPLOY — Render (ücretsiz, Docker) — ✅ CANLI (2026-06-26)

**CANLI: https://humanitaria.onrender.com** — servis `humanitaria` / **srv-d8uo70ernols73fgenr0** / frankfurt. Tek kalan servis (kopya `reliefweb-rag` / srv-d8te SİLİNDİ). **Render auto-deploy AÇIK** (master'a push → otomatik Docker build; frontend dist'i build'de üretilir). Dashboard env render.yaml'a EK olarak: **`GEMINI_BASE_URL` = Cloudflare AI Gateway** (Gemini IP engeli için; bkz. 2026-06-26 bölümü) + tüm `sync:false` secret'lar. Google Console "Authorized redirect URIs"e `https://humanitaria.onrender.com/auth/google/callback` eklendi. ⚠️ Ücretsiz tier: SQLite (kullanıcı/sohbet) deploy/uykuda SIFIRLANIR + 15dk boşta uyur.

`Dockerfile` (multi-stage: Vue build → FastAPI runtime) + `render.yaml` (Blueprint, free, frankfurt, `/health`) + `DEPLOY.md` (adım adım). Tek servis API+SPA'yı aynı origin'den sunar (CORS yok). Prod env: `SESSION_COOKIE_SECURE=true`, `INGEST_SCHEDULE_HOURS=0` (scheduler kapalı; kota dolu), `GEMINI_REASONING_EFFORT=low`, URL'ler `https://humanitaria.onrender.com` varsayımıyla; `AUTH_SESSION_SECRET` Render üretir; secret'lar (GEMINI/PINECONE/RELIEFWEB/GOOGLE) dashboard'da `sync:false`. **Ücretsiz tier:** disk yok → SQLite (kullanıcı/sohbet) uyku/deploy'da SIFIRLANIR + 15dk boşta uyur (ilk istek ~30-60s). Kalıcı için: paid+disk veya Postgres göçü. Google Console'a prod redirect eklenecek. Adımlar `DEPLOY.md`'de.

---

## ✅ Bu seansta UYGULANAN — Chat latency: enstrümantasyon + reasoning_effort + dayanıklılık (2026-06-07, commit bekliyor)

Kullanıcı 8000'de chat'i yavaş buldu. **Ölçüm bulgusu:** Gemini o sırada hem chat
(gemini-3.5-flash) hem query (gemini-2.5-flash) modelinde **503 "high demand"** veriyordu
(dış/geçici). Ayrıca chat LLM'de timeout/retry kontrolü yoktu → OpenAI client 503'te ~60s
iç-backoff yapıp asılıyordu.
- **Enstrümantasyon** (`api/routes/chat.py`): her yanıtta `chat latency: filter=..ms
  retrieval=..ms ttft=..ms total=..ms ns=..` INFO logu (ölç-önce-optimize-et).
- **`reasoning_effort=low`** (`config.GEMINI_REASONING_EFFORT` + `chain.py`): chat thinking
  bütçesini düşürür → TTFT azalır. Kill-switch ("" = gönderme). **Canlı DOĞRULANMADI (Gemini
  503'teydi); Gemini düzelince logdan TTFT + 400-yok kontrolü yapılmalı** (verirse kill-switch).
- **Dayanıklılık** (`chat.py _astream_with_retry` + `chain.py max_retries=0`/`timeout`):
  OpenAI client'ın ~60s iç-backoff'u kapatıldı; ilk-token ÖNCESİ kısa kontrollü retry (geçici
  503'ü atlatır), başarısızsa "model meşgul, tekrar dene" mesajı. Ölçüm: 503'te **~60s → ~19s**
  (kalan ~19s, Gemini tümden 503'te filter+embedding retry'larından; normal çalışmada tetiklenmez).
- Yeni config: `GEMINI_REASONING_EFFORT=low`, `CHAT_LLM_TIMEOUT=45`, `CHAT_LLM_MAX_RETRIES=2`.
- **Test: 322 backend** (+4 stream-retry) + 61 frontend yeşil.

---

## ✅ Bu seansta UYGULANAN — İş Kolu 2 (RAG kalite & ölçüm) + İş Kolu 3 (veri derinliği) (2026-06-07, commit `6c7a70a` → origin/master)

**İş Kolu 2A — Retrieval eval metrikleri (READ-only, kotadan etkilenmez):**
- `rag/eval_metrics.py` (YENİ, TDD): recall@k / reciprocal_rank (MRR) / nDCG@k (binary relevance).
- `scripts/build_eval_labels.py` (YENİ): default+v2'den aday havuzu + LLM relevance (TREC-tarzı pooled, silver) → `scripts/eval_data/labeled_queries.json` (15 sorgu, v2'nin 8 ülke kapsamı). Düz JSON-dizi parse + 503 retry.
- `scripts/eval_rag.py --metrics`: etiketli sette current namespace'in recall@k/MRR/nDCG'si. `PINECONE_NAMESPACE=v2` vs `''` ile A/B.
- **A/B SONUCU (k=5):** default recall@5=**0.208** MRR=**0.650** nDCG=**0.396** · v2 recall@5=**0.201** MRR=**0.622** nDCG=**0.370**. → **Doküman düzeyinde v2 ≈ default (regresyon YOK, belirgin kazanım YOK).** v2'nin değeri granülarite (küçük chunk → reranker/LLM %100 görür), doküman recall'u değil. **Cutover retrieval'ı bozmaz.** Caveat: 15 sorgu, silver label, iki-namespace havuz → kapsam gürültüsü.

**İş Kolu 2B — Konuşma-bağlamlı sorgu yeniden yazımı:**
- `rag/query_rewriter.py` (YENİ, TDD): follow-up'ı ("ya kuzeyde?") chat history ile standalone retrieval sorgusuna çevirir (gemini-2.5-flash, 5s, hata→orijinal). **Yanıt hâlâ orijinal mesajdan** üretilir; yalnız RETRIEVAL sorgusu yeniden yazılır.
- `chat.py` `_resolve_retrieval_query` (her iki route, retrieval ÖNCESİ, yalnız in-memory history varsa). `config.QUERY_REWRITE_ENABLED` kill-switch. (Faz C multi-query atlandı — A/B recall açığı göstermedi.)

**İş Kolu 3 — Veri derinliği (kod HAZIR; çalıştırma kota reset'inde):**
- `parser.py` parse_report: `iso3` (upper), `language`, `themes` (TÜM temalar; `theme`=ilk, back-compat), `glide` (linked disaster).
- `chunker.py`: bu alanları metadata'ya yazar (themes boşsa atlar — Pinecone empty-list).
- `client.py` reports fields: +`primary_country.iso3`, `language.name`, `disaster.glide`.
- `retriever._build_pinecone_filter`: tema filtresi `$or(theme $eq, themes $in)` → eski string + yeni liste kayıtları (eski namespace REGRESSİZ).
- **Reindex:** yeni script GEREKMEDİ — `ingest.py` zaten delete-before-upsert ile re-index. Kota reset'inde `PINECONE_NAMESPACE=v2 ingest.py --country PSE UKR --date-from 2023-06-05` yeni chunker+zenginleştirmeyi uygular.

**Test:** **318 backend** (yeni: eval_metrics 10, query_rewriter 5, parser/chunker/retriever enrichment 6) + 61 frontend yeşil.

---

## ✅ Bu seansta UYGULANAN — Auth (Login/Signup) sistemi (2026-06-07, commit `2198891` → origin/master)

Zorunlu giriş + e-posta/şifre **ve** Google OAuth, **httpOnly cookie** oturum. TDD ile.
Aynı zamanda **conversation IDOR açığını kapattı** (sohbetler artık kullanıcıya ait).

**Backend (yeni/değişen):**
- `rag/users.py` (YENİ) — users + sessions tabloları (aynı SQLite DB), bcrypt şifre hash, opak session token (DB'de sha256 hash'li). `get_or_create_google_user` (sub→email-link→create).
- `api/routes/auth.py` (YENİ) — `POST /auth/signup|login|logout`, `GET /auth/me`, `GET /auth/google/login|callback` (authlib). `get_current_user` dependency (cookie→user veya 401).
- `rag/conversations.py` — `user_id` kolonu + migration (`_ensure_schema` ALTER) + `is_owner()`; `create_conversation`/`list_conversations` artık `user_id` alır.
- `api/routes/{chat,conversations}.py` — gating `require_api_key` → `get_current_user` (X-API-Key KALDIRILDI); tüm conv işlemleri sahiplik-kontrollü (non-owner **404**). chat'te supplied session_id sahiplik kontrolü. Mesaj-id local'leri `user_msg_id`/`assistant_msg_id` (SSE payload anahtarları aynı: frontend uyumu).
- `api/main.py` — CORS `allow_credentials=True` + `SessionMiddleware` (authlib OAuth state).
- `config.py` — `AUTH_SESSION_SECRET`, `SESSION_COOKIE_NAME/SECURE`, `FRONTEND_URL`, `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`. `requirements.txt` — bcrypt, authlib, itsdangerous, httpx.

**Frontend (yeni/değişen):**
- `utils/authApi.js` + `utils/authStore.js` (YENİ, reactive — Pinia yok). `views/AuthView.vue` (YENİ, login+signup tek `mode` prop'lu view, `.mkt-scope` tasarımı, Google butonu). `router/index.js` — `/login`,`/signup` + `/app` `requiresAuth` guard (`beforeEach` → `refresh()`). `MarketingNav.vue` — authed'de Open app/Log out. `api.js` + Chat.vue SSE — `credentials:'include'`.

**Test/Doğrulama:** **297 backend** (yeni: users 13, auth 10, auth_google 2 [mock], IDOR access-control 3) + **61 frontend** yeşil. Build OK. Testlerde `get_current_user` override (conftest `_auth_override` + `@pytest.mark.real_auth` opt-out). **Canlı smoke (geçici DB):** signup→HttpOnly/SameSite=lax cookie, /me 200, /conversations cookie'li 200 / cookie'siz **401**, logout→**401** (sunucu-tarafı iptal), /login SPA 200, google(yapılandırılmamış) 503.
**Google OAuth canlı DOĞRULANDI** — kullanıcı Google ile giriş yaptı (redirect→accounts.google.com→/app). Cred'ler `.env`'de (gitignored): `GOOGLE_CLIENT_ID/SECRET`, `GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback`, `FRONTEND_URL=http://localhost:8000`, güçlü `AUTH_SESSION_SECRET`. Google consent "App name" = Console ayarı (Humanitaria). **Sidebar footer artık gerçek kullanıcıyı gösterir + Log out** (hardcoded "Alex Morgan" kaldırıldı). vite.config proxy'ye `/auth`+`/conversations` eklendi.

---

## 🎯 SONRAKİ SEANS — Rollout TIKANDI (Pinecone aylık write-unit kotası doldu); v2 8/10 ülke hazır+doğrulandı

Tüm-ülke rollout başlatıldı (3 yıl, 10 ülke, ülke-başı **en yeni 2000 cap**, yeni **`v2` namespace**).
**8 ülke başarıyla v2'ye yazıldı (68.936 vektör) + 8-ülke A/B ile kalite DOĞRULANDI (GO):** granülarite
kesin kazanım (ort. chunk 479 vs default 3070 char → reranker tam görüyor), freshness 160g vs 445g, judge 5.0=5.0.
AMA son 2 ülke (**Palestine kısmi, Ukraine 0**) yazılamadı: **Pinecone AYLIK write-unit kotası (2.000.000) doldu**
(hata gövdesi: "reached your write unit limit for the current month"). Sabit kota — retry/backoff çare değil. Bkz. [[run-gotchas]].

**v2 EKSİK: 8/10 ülke.** Cutover YAPILMADI (eksik v2'ye geçersek default'taki Ukrayna+Filistin kaybolur → regresyon).
**Veri kaybı yok:** default 31.628 + pilot 4.892 + v2 68.936 sağlam, izole.

**KARAR (2026-06-27 güncel): kota 2026-07-01'de yenilenir (Pinecone dashboard onayladı: "Writes paused until July 1, 2026"). O tarihe kadar BEKLE.** Bu arada app default'ta çalışıyor; 1 Temmuz'da plan dosyasındaki cutover prosedürü koşulacak (hatırlatıcı kuruldu).

**RESUME TARİFİ (reset gelince, sırayla):**
0. **(YENİ, kullanıcı isteği) Default namespace'i son-5-yıla indir:** `venv/Scripts/python.exe scripts/prune_old_vectors.py --before 2021-06-28 --apply` → 2021-06-28 öncesi ~7.197 chunk (~5.910 rapor) siler. Kota dolu olduğu için 1 Temmuz öncesi 429 verir; reset sonrası çalışır. Sonra panelde "Refresh breakdown" + vektör sayısı ~24.4K'ya düşer.
1. `PINECONE_NAMESPACE=v2 ./venv/Scripts/python.exe scripts/ingest.py --country PSE UKR --date-from 2023-06-05 --limit 2000` → v2 = 10/10 olur (store'da artık 429-retry var; aynı 2023-06-05 penceresi = diğer 8 ülkeyle tutarlı). Önce stats al; kota gerçekten resetlendi mi diye tek-vektör test upsert ile kontrol et.
2. v2 stats doğrula (PSE/UKR 0 failed) + 10-ülke A/B (v2 vs default).
3. **CUTOVER:** `PINECONE_NAMESPACE=v2` → `config.py` default + `.env` → commit/push → app v2'ye geçer.
4. v2 sağlam çalıştığı teyit edilince → **eski default ('') namespace'i SİL** (yer açılır) + **pilot namespace'i sil** (v2 Suriye'yi kapsıyor). Silmeden önce kullanıcıya son onay.

---

## ✅ Bu seansta UYGULANAN — Suriye Re-ingest Pilotu (2026-06-05, branch `feat/reingest-pilot-syria` → master'a YEREL merge, PUSH YOK)

Plan/spec: `docs/superpowers/{plans,specs}/2026-06-02-reingest-pilot-syria*` (gitignore'da, yerel). `subagent-driven-development` ile yürütüldü.

**Commit'ler (master'a merge edildi, push EDİLMEDİ):**
- `e2c0e7d` — guardrail `INGEST_LOOKBACK_YEARS=3` + `scripts/ingest.py _resolve_date_from` + `scripts/prune_old_vectors.py` (rafta) + testler (devralınan iş checkpoint'i)
- `c23963f` — **chat LLM → `gemini-3.5-flash`** (query-processor `gemini-2.5-flash` DEĞİŞMEDİ). Canlı smoke Türkçe yanıt verdi.
- `79d61f1` — **chunker: word-count → `RecursiveCharacterTextSplitter` ~1500 char/200 overlap**; `CHUNK_SIZE=1500` (artık KARAKTER), `CHUNK_OVERLAP=200`. Metadata + `{doc_id}_{i}` id şeması korundu.
- `01f6d4d` — **PLAN-DIŞI BUG FIX:** `client.py` ReliefWeb tarih filtresi `{operator:"gte"}` (API 400 "Invalid filter operator GTE") → `{value:{from:<ISO8601>}}`. Çıplak `YYYY-MM-DD` reddediliyor → `T00:00:00+00:00` ekleniyor. **Scheduler'ın incremental ingest'ini de düzeltti** (aynı kod yolu, sessizce bozuktu). systematic-debugging ile canlı API'ye karşı kök neden kanıtlandı.
- `2139951` — final-review nit'leri (test fixture model adı, retriever bayat yorum, `INGEST_LOOKBACK_YEARS` docs).

**Pilot ingest (CANLI):** `PINECONE_NAMESPACE=pilot scripts/ingest.py --country SYR --date-from 2025-06-02` → Suriye son-1-yıl: **805 doc OK / 0 failed / 246 skipped** (boş body) → **"pilot" namespace = 4.892 vektör**. **İzolasyon kanıtlandı:** default namespace 31.628 → 31.628 (DEĞİŞMEDİ).

**A/B sonucu (8 Suriye sorgusu TR+EN, pilot vs default; chat 3.5-flash + judge 2.5-flash her ikisinde sabit):**
| Metrik | Pilot (yeni) | Default (eski) |
|---|---|---|
| ort. chunk uzunluğu | **529 char** | 2400 char |
| max chunk | 792 char (~200 tok) | 5913 char (~1480 tok) |
| judge groundedness | 5.00/5 | 5.00/5 |
| judge relevance | 4.88/5 | 5.00/5 |
| freshness (medyan yaş) | **102 gün** | 387 gün |

**Dürüst değerlendirme:** ✅ **granülarite kesin kazanım** (4.5× küçük; reranker artık chunk'ın %100'ünü görüyor — eskiden ~%25-40). ✅ regresyon yok (5 belge/sorgu, groundedness 5.0). ✅ freshness çok daha iyi (AMA kısmen 1-yıl kapsam etkisi, saf chunking değil). ⚠️ **judge doygun (~5/5 tavan) → kaliteyi KANITLAYAMIYOR**; relevance 4.88 vs 5.00 farkı judge gürültüsü + 1-yıl penceresinin deprem içeriğini kaçırması. **Sonuç: koşullu GO** — chunker mekanizması çalışıyor, kalite argümanı yapısal (küçük chunk → ince embedding + tam reranker görüşü).

---

## Hedef
İnsani yardım M&E ekibi için ReliefWeb belgeleri üzerinden RAG sohbet sistemi. **UI İngilizce (global), sohbet çok dilli.** Marka: **Humanitaria**. Yerel geliştirme aşaması.

## Mevcut Durum (çalışıyor)
- **Mimari:** Gemini (chat/query/embed) + Pinecone — tek sağlayıcı, provider flag YOK. Tamamen bulut.
- **Chat LLM:** Gemini **`gemini-2.5-flash`** (GA, çok dilli; thinking modeli, `reasoning_effort="low"`). `gemini-3.5-flash`'ten geçildi (kronik 503 "high demand"). Transient 503'e karşı bounded retry: non-stream `_ainvoke_with_retry` + stream `_astream_with_retry` (ortak `_is_high_demand`); `except` busy→503/beklenmeyen→500. System prompt İngilizce; yanıt kullanıcının dilinde. Rule 9 = recency.
- **Query processor:** Gemini `gemini-2.5-flash` (DEĞİŞMEDİ). **Embedding:** `gemini-embedding-001` (3072-dim).
- **Chunker:** **`RecursiveCharacterTextSplitter` ~1500 char/200 overlap** (yeni default). NOT: mevcut default-namespace verisi hâlâ ESKİ 800-kelime chunk'larda — rollout'a kadar karışık durum.
- **Retrieval:** güncellik-farkında + alaka reranker'ı (truncate=END); recency blend ham alaka skoruyla. `RECENCY_RERANK_POOL=10`, `RECENCY_BOOST_FACTOR=0.6`.
- **Backend:** FastAPI, port `.env`'deki `API_PORT`. SSE streaming. Vue dist'i **SPA history-mode fallback** ile sunar (`api/main.py`: `/assets` mount + index.html catch-all). Kod değişikliğinden sonra restart (`--reload` yok).
- **Frontend:** Vue 3 + **vue-router** SPA, Humanitaria (yeşil/antrasit, dark+light), İngilizce. Rotalar: **`/` Landing** (marketing, `.mkt-scope` izole CSS) + **`/login`+`/signup`** (`views/AuthView.vue`) + **`/app` Chat** (`views/ChatView.vue`, **router guard'lı — zorunlu giriş**). **Pricing sayfası KALDIRILDI** (route+view+CSS); navbar: Product/Sources/Use cases (Citations nav linki de kaldırıldı, sayfa bölümü+footer linki kaldı). Marketing döküman-scroll (global viewport-lock yalnız chat'e özel: `ChatView .app{height:100vh;overflow:hidden}`). `frontend/dist/` gitignore'da.
- **Test:** **335 backend** + 62 frontend yeşil. Judge groundedness 5.0/5 (doygun); etiketli retrieval metrikleri baseline recall@5=0.224/MRR=0.672/nDCG=0.426 (MMR/havuz tuning A/B'de baseline optimal çıktı — bkz. 2026-06-24 İK3).

## Veri Durumu (Pinecone `reliefweb-docs`, 3072-dim)
- **default namespace (''): 31.628 vektör** — ESKİ 800-kelime chunk, 10 ülke. **App bunu kullanıyor** (cutover henüz YOK).
- **"v2" namespace: 68.936 vektör** — rollout, YENİ ~1500-char chunk. **8/10 ülke** (IRN/IRQ/SYR/TUR/YEM/AFG/SOM/SDN). EKSİK: Palestine (kısmi), Ukraine (0) → Pinecone aylık kotası doldu. 8-ülke A/B GO.
- **"pilot" namespace: 4.892 vektör** — Suriye son-1-yıl, YENİ chunk. v2 onu kapsıyor → cutover'da temizlenebilir.
- ⚠️ **Pinecone AYLIK write-unit kotası (2M) DOLU** — kota reset / plan upgrade olmadan YENİ yazma yapılamaz (ingest 429). Reset sonrası PSE+UKR tamamlanır.
- Yalnız `reports` endpoint. Daha fazla veri: `PINECONE_NAMESPACE=v2 scripts/ingest.py --country X --date-from YYYY-MM-DD --limit N` (`--force` KULLANMA; idempotent).

## Önemli Komutlar
| İş | Komut |
|----|-------|
| Sunucu başlat | `./venv/Scripts/python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8010` |
| Backend testleri | `./venv/Scripts/python.exe -m pytest tests/ -q` |
| Frontend build / test | `cd frontend && npm run build` / `npm test -- --run` |
| RAG eval (judge) | `./venv/Scripts/python.exe scripts/eval_rag.py --judge` |
| Pinecone namespace stats | `./venv/Scripts/python.exe -c "from config import get_settings; from pinecone import Pinecone; s=get_settings(); print(Pinecone(api_key=s.PINECONE_API_KEY).Index(s.PINECONE_INDEX).describe_index_stats())"` |

> **Bash gotcha:** kabuk cwd kalıcı; her komutta önce `cd "C:/Projeler/Reliefweb_RAG_System"`. Inline env var (`PINECONE_NAMESPACE=pilot cmd`, `$(...)`) Bash tool'unda çalışır, PowerShell'de DEĞİL.

## Commit / Push Durumu
- **`origin/master`'a PUSH'LANDI (master = origin):** pilot+chunker+model+date-filter-fix (`…5ab02a0`), store 429-retry (`918637d`), marketing entegrasyonu — Landing/Pricing/router/SPA-fallback (`cdc4a95`), marketing scroll fix (`5810e15`), pricing kaldırma (`e81aade`), citations-nav kaldırma (`daa9e1d`) + MEMORY docs.
- **PUSH'LANDI:** Auth (Login/Signup) sistemi — `2198891` (`6d73d9b..2198891 master→master`), 32 dosya. `.env` gitignored → Google/Gemini/Pinecone secret'ları commit'lenmedi.
- **PUSH'LANDI (2026-06-26, production fix'leri → master, Render auto-deploy):** `c540850` (google callback hardening: 500 yerine `/login?error=google` + log) · `acba8a9` (callback → **userinfo akışı**, JWKS host engelini atlar) · `11a4f23` (backend: `_build_context_and_sources` yalnız gösterilebilir doc'ları numaralar) · `dbd4f5c` (frontend: kaynağı olmayan `[n]` işaretlerini siler + history-load renumber). Gemini IP engeli fix'i **kodda değil** — Render dashboard env `GEMINI_BASE_URL`=Cloudflare gateway.
- Remote: **https://github.com/berkcansuner/Humanitaria** (private).

## Sıradaki Adımlar (kullanıcı yönlendirir)
- [ ] **Kotayı çöz** (aylık reset bekle VEYA Pinecone plan upgrade) → `PINECONE_NAMESPACE=v2 ingest --country PSE UKR --date-from 2023-06-05 --limit 2000` ile v2'yi tamamla.
- [ ] v2 tamla → **CUTOVER:** `PINECONE_NAMESPACE=v2` (config default + .env) commit/push → app v2'ye geçer. Eski default rollback olarak TUT; pilot namespace temizle.
- [ ] (Karar) "pilot" + (cutover sonrası) eski default namespace temizliği.
- [ ] Diğer Faz 2 eksenleri: hibrit (keyword+vektör) arama; kaynak snippet/önizleme.
- [x] ~~Conversation kullanıcı modeli / IDOR~~ → **YAPILDI** (auth sistemi, 2026-06-07, commit bekliyor). Kalan deploy-öncesi: conv rate-limit; CORS daraltma; prod `.env`'e güçlü `AUTH_SESSION_SECRET` + Google cred'leri.
- [x] ~~**İş Kolu 2 — RAG kalite & ölçüm**~~ → **YAPILDI** (eval metrikleri + etiketli set + A/B + sorgu yeniden yazımı; commit bekliyor). A/B: v2≈default doküman düzeyinde.
- [x] ~~**İş Kolu 3 — Veri derinliği** (kod)~~ → **YAPILDI** (parser/chunker/client/retriever zenginleştirme; commit bekliyor). **Çalıştırma:** kota reset'inde `ingest.py` ile re-index (yeni alanlar + chunker o zaman uygulanır).

## Bilinen Sorunlar / Kısıtlamalar
- **Pinecone aylık write-unit kotası (2M):** rollout bunu doldurdu → yeni yazma 429 ("write unit limit for the current month"). Sabit kota; retry çare değil. Reset/plan-upgrade gerek. Büyük ingest planlarken hesaba kat.
- **Karışık chunk durumu:** chunker yeni default (~1500 char) ama mevcut default-namespace verisi hâlâ eski 800-kelime — cutover'a kadar böyle. Yeni ingest'ler yeni chunk üretir.
- 1-yıl ingest penceresi tarihsel büyük olayları kaçırır (deprem) → rollout'ta ≥2-3 yıl.
- ~~Conversation IDOR~~ → **ÇÖZÜLDÜ** (auth sistemi; sohbetler `user_id`-sahipli, non-owner 404). Mevcut conversations.db satırları migration'da `user_id=NULL` → görünmez (dev verisi; kabul).
- Şablon/sistem mesajları (greeting, no-docs) İngilizce; yalnız LLM yanıtı çok dilli (bilinçli).
- Session history varsayılan in-memory (restart'ta silinir); `REDIS_URL` ile kalıcı.
- Görseller/infografikler doğrudan sorgulanamaz (246 Suriye raporu boş body → atlandı).
