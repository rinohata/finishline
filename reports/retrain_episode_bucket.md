# 再学習レポート: episode_gap → episode_bucket_completion_rate / episode_bucket_gap

`reports/fix_endurance_bucket.md`（修正2）で判明した「耐久話数はテストユーザーの
54.31%で100話超」という問題を受け、`episode_gap` 特徴量を話数レンジバケットベースの
特徴量に置き換え、本番モデルを再学習した。

## 修正1: 現状の確認（再学習前）

再学習前の本番モデル（`models/archive/dropout_predictor_pre_episode_bucket.lgb`
として保存済み）の特徴量重要度（gain）を確認した。

| 順位 | 特徴量 | gain | gain比率 |
|---|---|---|---|
| 1 | anime_avg_completion_rate_A | 802,372.9 | 54.21% |
| 2 | user_completion_rate | 412,107.1 | 27.84% |
| 3 | episodes_num | 105,458.6 | 7.12% |
| 4 | score_num | 37,690.2 | 2.55% |
| 5 | cos_dropped | 26,936.0 | 1.82% |
| **6** | **episode_gap** | **24,670.3** | **1.67%** |
| 7 | n_input | 22,163.0 | 1.50% |
| 8 | genre_match_completion_rate | 14,584.7 | 0.99% |
| ... | ... | ... | ... |
| 13 | endurance_episodes | 1,509.6 | 0.10% |

**仮説の検証結果**: 「episode_gapが機能していなかった」という仮説は**部分的に正しい**。
完全にゼロではなく57特徴量中6位（1.67%）と一定の寄与はあったが、`anime_avg_completion_rate_A`
（54.21%）・`user_completion_rate`（27.84%）の2特徴量が支配的で、episode_gapの寄与は
相対的に小さい。また、episode_gapの元になる `endurance_episodes` 自体は単独では
0.10%（13位）とほぼ寄与していない。外れ値に弱い指標であるにもかかわらず一定の
gainを得ていたのは、LightGBMが（NaNではなく）大きく負の値に張り付いた分布からでも
何らかの分割点を見つけて学習していたためと考えられる。

## 修正2: 特徴量の置き換え

`api/services/profile.py` に追加済みの `compute_episode_buckets` / `best_episode_bucket` /
`bucket_index_for_episodes`（前回の修正で実装済み）を再利用し、以下2特徴量を新設した。

- **`episode_bucket_completion_rate`**: 候補作品の話数バケット（〜13/14〜26/27〜50/51話〜）に
  おけるユーザーの完走率。該当バケットの本数が3本未満ならNaN
- **`episode_bucket_gap`**: 候補作品のバケットindex（0〜3） − ユーザーの「合う話数」バケット
  のindex。ユーザーに十分なデータがなければNaN

`api/ml/inference.py` の `build_candidate_features` を修正し、学習時と完全に同じ定義で
推論時にもこの2特徴量を計算するようにした（`UserProfileVectors` に `episode_buckets`
（4バケット全件）を追加）。`genre_match_completion_rate` と同じ「ユーザー×候補作品」の
交互作用特徴量という位置づけで、要件定義書5.4「交互作用」節にも反映した。

## 修正3: 再学習と評価

本番モデルと同一のレシピ（`notebooks/02_model.ipynb` と同じ2パスサンプリング・
SEED=42・user_id単位70/15/15分割・N=[3,5,10,20,30]をプールし`n_input`を特徴量に含める・
放送継続中577作品中288作品分の`anime_avg_completion_rate_A`を訓練データ側でもNaN化）を
再現し、`episode_gap`版（control）と`episode_bucket_*`版を同一train/val/test分割で
学習・比較した。評価は本番と同じくtest集合のN=20行のみで実施（`test_baseline_pos_rate`
=0.0556、本番の記録値と一致）。

再現に使ったのはこの検証専用の新規学習であり、現在保存されている旧`model_card.json`の
記録値（test_auc=0.8226, test_pr_auc=0.3023）とは実行が別のため厳密には一致しない
（LightGBMは`feature_fraction`/`bagging_fraction`を使うため実行間でわずかな差が出る）。
このため、比較の基準は「同一スクリプト・同一データでepisode_gapの有無だけを変えた
2モデル」（below の control）とした。

### 評価表

| | AUC | PR-AUC |
|---|---|---|
| 旧（episode_gap, control再現） | 0.8377 | 0.3212 |
| 新（episode_bucket_completion_rate + episode_bucket_gap） | 0.8374 | 0.3232 |
| 差 | **-0.0003** | **+0.0020** |

### 新特徴量の重要度（gain）

| 特徴量 | 順位 | gain | gain比率 |
|---|---|---|---|
| episode_bucket_completion_rate | 8/58 | 19,539.6 | 1.27% |
| episode_bucket_gap | 14/58 | 3,592.3 | 0.23% |
| （参考）旧episode_gap（control） | 4/57 | 45,039.6 | 2.96% |

新旧で特徴量重要度の順位・gainの絶対値は下がった（旧episode_gapは4位2.96% →
新2特徴量の合計でも1.50%）が、精度（AUC/PR-AUC）は悪化していない。これは
`episode_gap`が持っていたgainの一部が「外れ値によるノイズの多い分割点」を
モデルが学習していたことによるもので、実質的な予測力への寄与は小さかった
可能性を示唆する。

### 判断: 変更を採用（ロールバックなし）

CLAUDE.mdの評価方針どおりPR-AUCを主要指標として判断した。PR-AUCは+0.0020で改善、
AUCは-0.0003で誤差範囲内（LightGBMの`feature_fraction`/`bagging_fraction`由来の
実行間ノイズと同程度）のため、**精度は下がっていないと判断し、変更を採用した**。
旧本番モデルは `models/archive/dropout_predictor_pre_episode_bucket.lgb`（および
`feature_columns_pre_episode_bucket.json`, `model_card_pre_episode_bucket.json`）
として保存済みで、必要ならいつでもロールバックできる。

## 修正4: model_card.json の更新

`models/model_card.json` を更新した。

- `performance` / `test_auc` / `test_pr_auc`: 0.8226/0.3023 → **0.8374/0.3232**
- `feature_columns`: `episode_gap` を削除し、`episode_bucket_completion_rate` /
  `episode_bucket_gap` を追加（57 → 58特徴量）
- 新設 `episode_gap_deprecation` セクション: 廃止理由（耐久話数の外れ値問題、
  テストユーザーの100話超が54.31%だった事実）、日付、本レポートへの参照、
  変更前後のAUC/PR-AUC・gain比較、ロールバックしなかった判断根拠を記録

## 動作確認

1. `models/dropout_predictor.lgb` / `models/feature_columns.json`（58特徴量、
   `episode_bucket_completion_rate`・`episode_bucket_gap`を含み`episode_gap`は
   含まないことを確認）をデプロイし、バックエンドを再起動
2. `build_predict_response` / `build_predict_single_response` を実データで実行し、
   クラッシュなく `at_risk` / `will_complete` / 単体判定が返ることを確認
3. Playwright不使用の直接HTTP経由（`vite preview`の`/api`プロキシ経由含む）で
   `/predict` を実データ6件で呼び出し、正常なJSONレスポンスを確認
4. 全シナリオでエラーなし

## 変更ファイル

- `models/dropout_predictor.lgb`（差し替え）
- `models/feature_columns.json`（差し替え）
- `models/model_card.json`（更新）
- `models/archive/`（旧モデル一式のバックアップ、新規）
- `api/ml/inference.py`（`episode_bucket_completion_rate` / `episode_bucket_gap` を
  学習時と同じ定義で計算するよう修正）
- `api/services/profile.py`（`compute_endurance_episodes` のdocstring更新）
- `docs/requirements.md`（5.4節の特徴量リストを更新）
