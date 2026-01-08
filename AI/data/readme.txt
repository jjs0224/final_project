root인 곳에서 실행(ex. final_project)

# 1) 카테고리 포함 catalog 생성
python -m AI.data.build_menu_catalog ^
  --src AI/data/menu_final_with_allergen.json ^
  --out AI/data/menu_catalog.jsonl

# 2) lexical index 생성
python -m AI.data.build_lexical_index --catalog AI/data/menu_catalog.jsonl --out AI/index/lexical/lexical_meta.json

Chromadb 바로구축
기존데이터있을시 삭제후 진행
pip install chromadb sentence-transformers rapidfuzz
python -m AI.data.build_vector_index ^
  --catalog AI/data/menu_catalog.jsonl ^
  --mode chroma ^
  --out_dir AI/index/vector ^
  --collection menu_catalog