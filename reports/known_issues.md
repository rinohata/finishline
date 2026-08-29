# 既知の問題

対応方針の判断待ち、または優先度が低いため未対応の問題を記録する。

## will_complete の理由生成が、表示ジャンルと異なるジャンルを根拠にすることがある【修正済み】

### 症状

「完走できる作品」ブロックで、表示されているジャンルには含まれないジャンルを
理由として提示することがある。

例: 「怪～ayakashi～」（表示ジャンル: Mystery・Historical）に対して
「ファンタジーの完走実績があります」という理由が表示される。

### 原因（調査済み）

`anime.csv`の実際のGenres列は `Mystery, Historical, Horror, Fantasy` の4件だが、
UI表示側（`frontend/src/components/WillCompleteBlock.tsx`・`AtRiskBlock.tsx`・
`QuestionCard.tsx`）は`genres.slice(0, 2)`で先頭2件のみを表示している。

一方、理由生成側（`api/services/explain.py`の`build_will_complete_reason`）は
`store.genres(anime_id)`で取得した**全ジャンル**からユーザーの完走率が最も高い
ジャンルを選んで理由文を作る（`max(genre_hits, key=lambda x: x[1])`）。

このため、ユーザーの完走率が最も高いジャンルがちょうど3番目以降（表示されない
ジャンル）だった場合、表示ジャンルと理由のジャンルが食い違う。`at_risk`側の
理由生成（`build_reasons`）も同じ`store.genres()`全件を参照する作りのため、
同様の食い違いが起こりうる。

### 修正内容

`api/services/explain.py`に`_displayed_genre_hits()`を追加し、`build_reasons`
（at_risk）・`build_will_complete_reason`（will_complete）の両方で、理由に使う
ジャンルの選択範囲を表示側と同じ`DISPLAYED_GENRE_COUNT = 2`（先頭2件）に限定した。
先頭2ジャンルのいずれも回答本数が薄い（`GENRE_REASON_MIN_COUNT`未満）場合は
ジャンル理由を出さず、他の理由（話数バケット・埋め込み類似度・母集団完走率との差）
にフォールバックする。

`at_risk`側にも同じ問題（`store.genres(anime_id)`で全ジャンルを参照していた）が
あったため同様に修正した。

テストユーザー20人で再測定し、`at_risk`40件・`will_complete`199件すべてで
表示ジャンルと理由のジャンルが一致することを確認済み（不一致0件）。
