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

from rag.query_processor import extract_filters, analyze_query
from rag.retriever import (
    build_retriever,
    apply_date_filter,
    rerank_by_recency,
    _COUNTRY_RELIEFWEB_ALIASES,
)


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


def _run_retrieval(case: dict, filters: dict) -> str:
    """Canlı retrieval çalıştır; tek satırlık bir özet döndür."""
    try:
        retriever = build_retriever(filters)
        docs = retriever.invoke(case["query"])
        docs = apply_date_filter(docs, filters.get("date"))
        docs = rerank_by_recency(docs)
    except Exception as e:
        return f"retrieval HATASI: {e}"

    n = len(docs)
    note = f"{n} belge"
    if "country" in case and n:
        matched = sum(1 for d in docs if _country_matches(case["country"], d.metadata.get("country", "")))
        note += f", {matched}/{n} {case['country']} eşleşti"
    min_results = case.get("min_results")
    if min_results is not None and n < min_results:
        note += f"  ⚠ min {min_results} beklendi"
    return note


def main():
    parser = argparse.ArgumentParser(description="RAG eval harness")
    parser.add_argument("--no-retrieval", action="store_true",
                        help="Yalnız filtre çıkarmayı değerlendir (vector store gerekmez)")
    args = parser.parse_args()

    print(f"\nRAG Eval — {len(EVAL_CASES)} vaka\n" + "=" * 70)
    filter_pass = 0
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
        if not args.no_retrieval:
            print(f"    retrieval: {_run_retrieval(case, filters)}")

    total = len(EVAL_CASES)
    print("\n" + "=" * 70)
    print(f"Filtre doğruluğu: {filter_pass}/{total} ({100 * filter_pass // total}%)")
    sys.exit(0 if filter_pass == total else 1)


if __name__ == "__main__":
    main()
