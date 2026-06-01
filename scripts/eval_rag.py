"""RAG değerlendirme (eval) harness'i.

İki şeyi ölçer:
  1. Filtre çıkarma doğruluğu — extract_filters() beklenen ülke/tema/tarih
     filtrelerini üretiyor mu? (deterministik; LLM + rule-based fallback)
  2. Retrieval isabeti — sorgu için en az bir belge dönüyor mu ve dönen
     belgeler beklenen ülke ile eşleşiyor mu? (canlı vector store gerektirir)

Kullanım:
    python scripts/eval_rag.py                # tam değerlendirme (retrieval dahil)
    python scripts/eval_rag.py --no-retrieval # yalnız filtre çıkarma (offline, hızlı)

Çıkış kodu: tüm filtre beklentileri geçerse 0, aksi halde 1.
Retrieval bir bilgi metriğidir; sonucu çıkış kodunu etkilemez (LLM/veri değişkenliği).
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Windows konsolu (cp1254) Unicode sembolleri (—, ⚠) encode edemiyor → UTF-8'e geç.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from typing import Optional

from pydantic import BaseModel, Field

import anyio

from rag.query_processor import extract_filters, analyze_query
from rag.retriever import _COUNTRY_RELIEFWEB_ALIASES
from rag.chain import build_chain
from api.routes.chat import _retrieve_docs


# Her vaka: sorgu + beklenen filtreler.
#   country/theme : tam string eşleşmesi beklenir
#   date          : True → bir tarih filtresi ÜRETİLMELİ
#   vague         : True → sorgu belirsiz sayılmalı (ülke/tema/tarih yok)
#   min_results   : retrieval'da beklenen minimum belge sayısı (varsa)
EVAL_CASES = [
    {"query": "Sudan'daki son insani durum",
     "country": "Sudan", "min_results": 1},
    {"query": "health situation in Yemen",
     "country": "Yemen", "theme": "Health", "min_results": 1},
    {"query": "Suriye'de gıda güvenliği raporları",
     "country": "Syria", "theme": "Food and Nutrition", "min_results": 1},
    {"query": "protection concerns in Ukraine",
     "country": "Ukraine", "theme": "Protection and Human Rights", "min_results": 1},
    {"query": "barınma ihtiyaçları nelerdir",
     "theme": "Shelter and Non-Food Items"},
    {"query": "son 3 ayda Afganistan gelişmeleri",
     "country": "Afghanistan", "date": True},
    {"query": "education needs in Somalia",
     "country": "Somalia", "theme": "Education"},
    {"query": "WASH access in Sudan",
     "country": "Sudan", "theme": "Water Sanitation Hygiene", "min_results": 1},
    {"query": "Gazze'deki sağlık hizmetleri",
     "country": "State of Palestine", "theme": "Health"},
    {"query": "genel insani yardım durumu",
     "vague": True},
    # --- ek vakalar (judge + daha geniş kapsam) ---
    {"query": "Yemen'de çocukların beslenme durumu",
     "country": "Yemen", "theme": "Food and Nutrition", "min_results": 1},
    {"query": "Sudan'da yerinden edilme",
     "country": "Sudan", "min_results": 1},
    {"query": "humanitarian needs in Afghanistan",
     "country": "Afghanistan", "min_results": 1},
    {"query": "Somali'de gıda krizi",
     "country": "Somalia", "theme": "Food and Nutrition"},
    {"query": "health services in Syria",
     "country": "Syria", "theme": "Health"},
    # "sivillerin korunması" dolaylı bir tema ifadesi; Protection teması zaten
    # "protection concerns in Ukraine" vakasıyla test ediliyor → burada country-only.
    {"query": "Ukrayna'da sivillerin korunması",
     "country": "Ukraine", "min_results": 1},
    {"query": "shelter needs in Yemen",
     "country": "Yemen", "theme": "Shelter and Non-Food Items"},
    {"query": "Gazze'de eğitime erişim",
     "country": "State of Palestine", "theme": "Education"},
    {"query": "water and sanitation in Somalia",
     "country": "Somalia", "theme": "Water Sanitation Hygiene"},
    {"query": "Afganistan'daki genel insani durum",
     "country": "Afghanistan", "min_results": 1},
    # --- güncellik (freshness) vakaları ---
    {"query": "What is the current humanitarian situation in Sudan?",
     "country": "Sudan", "min_results": 1, "freshness": True},
    {"query": "current humanitarian situation in Yemen",
     "country": "Yemen", "min_results": 1, "freshness": True},
    {"query": "latest situation in Ukraine",
     "country": "Ukraine", "min_results": 1, "freshness": True},
    {"query": "how did the situation in Sudan evolve over 2024",
     "country": "Sudan", "min_results": 1},
]


def _country_matches(expected: str, actual: str) -> bool:
    """Dönen belgenin ülkesi beklenen ülkeyle (kısa veya tam ReliefWeb adı) eşleşir mi?"""
    if not actual:
        return False
    alias = _COUNTRY_RELIEFWEB_ALIASES.get(expected)
    return actual == expected or (alias is not None and actual == alias)


def _check_filters(case: dict, filters: dict) -> list[str]:
    """Beklenen filtrelerle gerçekleşeni karşılaştır; hata mesajları döndür."""
    errors = []
    if case.get("vague"):
        analysis = analyze_query(case["query"], filters)
        if not analysis["is_vague"]:
            errors.append(f"belirsiz beklendi ama filtre üretildi: {filters}")
        return errors
    if "country" in case and filters.get("country") != case["country"]:
        errors.append(f"country: beklenen {case['country']!r}, gelen {filters.get('country')!r}")
    if "theme" in case and filters.get("theme") != case["theme"]:
        errors.append(f"theme: beklenen {case['theme']!r}, gelen {filters.get('theme')!r}")
    if case.get("date") and "date" not in filters:
        errors.append("date: bir tarih filtresi beklendi ama üretilmedi")
    return errors


def _freshness_note(docs) -> str:
    """Dönen kaynakların yaş dağılımı (gün): medyan, en yeni, son 6 ay (≤182g) oranı."""
    from datetime import datetime
    today = datetime.now()
    ages = []
    for d in docs:
        ds = d.metadata.get("date", "")
        if ds and len(ds) >= 10:
            try:
                ages.append((today - datetime.strptime(ds[:10], "%Y-%m-%d")).days)
            except ValueError:
                pass
    if not ages:
        return "freshness: tarih yok"
    ages.sort()
    median = ages[len(ages) // 2]
    within6mo = sum(1 for a in ages if a <= 182)
    return f"freshness: medyan {median}g, en yeni {min(ages)}g, {within6mo}/{len(ages)} ≤6ay"


def _run_retrieval(case: dict, filters: dict):
    """Route ile birebir retrieval (boost dahil); (özet metni, docs) döndür. Hata → (mesaj, [])."""
    try:
        docs = anyio.run(_retrieve_docs, case["query"], filters)
    except Exception as e:
        return f"retrieval HATASI: {e}", []

    n = len(docs)
    note = f"{n} belge"
    if "country" in case and n:
        matched = sum(1 for d in docs if _country_matches(case["country"], d.metadata.get("country", "")))
        note += f", {matched}/{n} {case['country']} eşleşti"
    min_results = case.get("min_results")
    if min_results is not None and n < min_results:
        note += f"  ⚠ min {min_results} beklendi"
    if case.get("freshness"):
        note += "  |  " + _freshness_note(docs)
    return note, docs


class JudgeScores(BaseModel):
    """LLM-judge çıktısı (1-5 ölçek)."""
    groundedness: int = Field(description="Yanıt yalnızca verilen Context'e mi dayanıyor? 1=uydurma, 5=tamamen dayanaklı")
    relevance: int = Field(description="Yanıt soruyu ne kadar karşılıyor? 1=ilgisiz, 5=tam yanıt")
    # Gemini json_mode bazen reason'ı atlıyor → opsiyonel, puanları kaybetme.
    reason: Optional[str] = Field(default="", description="Kısa gerekçe (tek cümle)")


_JUDGE_PROMPT = (
    "Bir RAG sisteminin yanıtını değerlendiren tarafsız bir hakemsin.\n"
    "İki ölçütü 1-5 arası puanla:\n"
    "- groundedness: Yanıttaki iddialar SADECE Context'teki belgelerle destekleniyor mu? "
    "Context dışı/uydurma bilgi varsa düşük puan ver.\n"
    "- relevance: Yanıt kullanıcının sorusunu ne kadar karşılıyor?\n"
    "Yalnızca JSON döndür.\n\n"
    "SORU:\n{question}\n\nCONTEXT:\n{context}\n\nYANIT:\n{answer}\n"
)

_judge = None


def _get_judge():
    global _judge
    if _judge is None:
        from langchain_openai import ChatOpenAI
        from config import get_settings
        settings = get_settings()
        llm = ChatOpenAI(
            model=settings.GEMINI_QUERY_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            api_key=settings.GEMINI_API_KEY,
            temperature=0.0,
            timeout=30,
        )
        _judge = llm.with_structured_output(JudgeScores, method="json_mode")
    return _judge


def _build_context(docs) -> str:
    """Inference'taki ile aynı [n]-numaralı, tarih etiketli context formatı (chat route ile eşleşir)."""
    return "\n\n---\n\n".join(
        f"[{i}] ({d.metadata.get('date') or 'tarih yok'}) {d.page_content}"
        for i, d in enumerate(docs, 1)
    )


def _judge_case(case: dict, docs: list):
    """Yanıtı üret + hakem puanla. (scores | None, hata | None) döndür."""
    if not docs:
        return None, "belge yok"
    try:
        context = _build_context(docs)
        answer = build_chain().invoke({
            "question": case["query"], "context": context, "chat_history": [],
        })
        scores = _get_judge().invoke(
            _JUDGE_PROMPT.format(question=case["query"], context=context, answer=answer)
        )
        return scores, None
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description="RAG eval harness")
    parser.add_argument("--no-retrieval", action="store_true",
                        help="Yalnız filtre çıkarmayı değerlendir (vector store gerekmez)")
    parser.add_argument("--judge", action="store_true",
                        help="LLM-judge ile yanıt kalitesini puanla (groundedness+relevance, Gemini)")
    parser.add_argument("--judge-threshold", type=float, default=3.5,
                        help="--judge ile ortalama puan eşiği; altı çıkış kodunu 1 yapar (varsayılan 3.5)")
    args = parser.parse_args()

    print(f"\nRAG Eval — {len(EVAL_CASES)} vaka\n" + "=" * 70)
    filter_pass = 0
    ground_scores, rel_scores = [], []
    for case in EVAL_CASES:
        filters = extract_filters(case["query"])
        errors = _check_filters(case, filters)
        status = "PASS" if not errors else "FAIL"
        if not errors:
            filter_pass += 1
        print(f"\n[{status}] {case['query']}")
        print(f"    filtreler: {filters}")
        for err in errors:
            print(f"    ✗ {err}")
        docs = []
        if not args.no_retrieval:
            note, docs = _run_retrieval(case, filters)
            print(f"    retrieval: {note}")
        if args.judge and not case.get("vague"):
            scores, jerr = _judge_case(case, docs)
            if scores is not None:
                ground_scores.append(scores.groundedness)
                rel_scores.append(scores.relevance)
                print(f"    judge: groundedness={scores.groundedness}/5, "
                      f"relevance={scores.relevance}/5 — {scores.reason}")
            else:
                print(f"    judge: atlandı ({jerr})")

    total = len(EVAL_CASES)
    print("\n" + "=" * 70)
    print(f"Filtre doğruluğu: {filter_pass}/{total} ({100 * filter_pass // total}%)")

    judge_ok = True
    if args.judge and ground_scores:
        avg_g = sum(ground_scores) / len(ground_scores)
        avg_r = sum(rel_scores) / len(rel_scores)
        print(f"Judge ortalaması ({len(ground_scores)} vaka): "
              f"groundedness={avg_g:.2f}/5, relevance={avg_r:.2f}/5 "
              f"(eşik {args.judge_threshold})")
        judge_ok = avg_g >= args.judge_threshold and avg_r >= args.judge_threshold

    sys.exit(0 if (filter_pass == total and judge_ok) else 1)


if __name__ == "__main__":
    main()
