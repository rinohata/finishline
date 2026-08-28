# data/raw・data/processed 消失からの復旧記録

## 何が失われたか

プロジェクトを `~/Documents` 相当の場所から `~/dev/finishline`（iCloud同期対象外）へ移動する作業の際に、
`data/raw/`（Kaggle生データ）と `data/processed/`（学習・推論用の事前計算済みルックアップ）が削除された。
どちらも `.gitignore` 対象で、生成コード自体もリポジトリにコミットされていなかったため、git履歴からの
復元もできない状態だった。

生き残っていたもの: `models/dropout_predictor.lgb`・`feature_columns.json`・`model_card.json`（これらは
`.gitignore` 対象ではなく元々git管理下にあった）、`data/dropout_curves.json`・`data/question_pool.json`、
コード全体、`reports/` 全体。

調査の結果、`data/processed/` を生成する「Phase 2」の一部ロジック（`anime_population_completion_rate_B` ・
`anime_avg_completion_rate_A_train` 系・`anime_is_ongoing`・`anime_peak_at_risk`・`population_stats`）は、
`notebooks/` 配下のどのノートブックにも存在しないことが判明した。過去のセッションでアドホックに実行され、
保存されずに失われたコードの成果物だったとみられる。

## 何が既存コードから復元でき、何ができなかったか

| 項目 | ノートブックに計算コードがあったか | 保存コードがあったか |
|---|---|---|
| train/val/test分割 (`02_model.ipynb`セル3) | あり（SEED=42固定） | — |
| `anime_avg_completion_rate_A_train` | あり（セル7、メモリ上のみ） | 無し |
| `anime_population_completion_rate_B` | あり（`01_aggregation.ipynb`セル7、全作品分） | 一部のみ（`dropout_curves.json`経由、eligible作品のみ） |
| `anime_peak_at_risk` | 無し（`dropout_curves.json`には丸め済みハザード率のみで生の到達者数は無い） | 無し |
| `anime_is_ongoing` | 無し | 無し |
| `population_stats` | 無し（`api/`のどこからも未参照と判明） | 無し |
| `anime_embeddings` | あり（`02_model.ipynb`セル9） | あり |

計算コードが無かった4項目は、`api/services/data_store.py`の使用箇所と`reports/api_verification.md`の
記述から仕様を逆算して実装した。特に`anime_is_ongoing`は`reports/api_verification.md`追記3に
「Aired基準（"...to ?"パターン、525本）OR watching_ratio>0.5・denom≥50基準（230本）の和集合＝577本」
という具体的な検証済みの仕様が残っていたため、これをそのまま再現した。

## 実施した復旧作業

1. **`scripts/build_lookups.py`を新規作成**: `data/raw/{anime.csv, animelist.csv, anime_with_synopsis.csv}`
   から`data/processed/`の全9ファイル（ルックアップ8種 + あらすじ埋め込み）を再生成する。
   `data/dropout_curves.json`・`data/question_pool.json`は対象外（既存のまま維持）。
2. **`scripts/train_model.py`を新規作成**: 再生成した`data/processed/`と`data/raw/`から
   `dropout_predictor.lgb`を再学習する。特徴量エンジニアリングは`api/services/profile.py`の純粋関数と
   `api/ml/inference.py`の`build_candidate_features`をそのままimportして使うことで、学習時と提供時の
   特徴量定義が食い違わないようにした。
3. Kaggleデータセット（`hernan4444/anime-recommendation-database-2020`）を`data/raw/`に配置。
4. `scripts/build_lookups.py`を実行（約2.5分、`animelist.csv`への2回のフルスキャン + 埋め込み計算）。
5. `scripts/train_model.py`を実行して再学習（約1分）。

### トラブルシューティング: メモリ枯渇

`train_model.py`の初回実行時、1行あたり約60キー（動的特徴量 + 静的特徴量 + genre one-hot 44列）の
Pythonの辞書を、target行ごとに`anime_feat.loc[aid]`で都度組み立てる実装になっており、このマシン
（物理RAM 8GB）でswapが枯渇しかけた（RSS約12GB、swap使用率95%）。実行中のプロセスを安全に終了し、
`02_model.ipynb`の`attach_static_features`と同じ設計（動的特徴量だけの小さい辞書でDataFrameを作り、
静的特徴量・genre列は最後に1回のvectorized mergeでまとめて付与する）に書き直したところ、
所要時間が数分規模から数十秒規模に短縮され、メモリも問題ないレベルに収まった。

## 検証結果

### 1. `anime_is_ongoing`件数

| 基準 | 期待値（`reports/api_verification.md`より） | 再計算値 |
|---|---|---|
| Aired基準（"...to ?"パターン） | 525 | **525** |
| watching_ratio 対象作品数（denom≥50） | 14,056 | **14,056** |
| watching_ratio > 0.5 | 230 | **230** |
| 和集合 | 577 | **577** |

4項目すべて完全一致。

### 2. 消失前に稼働していた旧プロセス（PID 37186、`data/raw`・`data/processed`削除前からメモリ上に
   ロード済みだったデータを保持）との値照合

`POST /predict/single`のレスポンス（`population_completion_rate`・`is_ongoing`・`peak_dropout_episode`）を
使い、旧プロセスと再構築後に別ポートで起動した新プロセスとで7作品を照合した。

| anime_id | 旧プロセス | 新プロセス | 一致 |
|---|---|---|---|
| 1（カウボーイビバップ） | 0.8707 / False / 2 | 0.8707 / False / 2 | ✓ |
| 21（One Piece、放送中） | 0.0 / True / None | 0.0 / True / None | ✓ |
| 30749 | 0.8736 / False / 2 | 0.8736 / False / 2 | ✓ |
| 7261 | 0.8754 / False / 20 | 0.8754 / False / 20 | ✓ |
| 35385 | 0.5357 / False / None | 0.5357 / False / None | ✓ |
| 1746 | 0.8329 / False / 2 | 0.8329 / False / 2 | ✓ |
| 2592 | 0.9521 / False / None | 0.9521 / False / None | ✓ |

7作品すべて完全一致。

### 3. `dropout_curves.json`との`peak_dropout_episode`突合

`scripts/build_lookups.py`内で自動検証。ハザード曲線が存在する7,603作品全件で、既存の
`data/dropout_curves.json`の`peak_dropout_episode`と再計算値が完全一致（不一致0件）。

### 4. 再学習後の性能

| 指標 | 消失前の本番モデル | 今回の再学習 |
|---|---|---|
| test_auc | 0.8374 | **0.8378** |
| test_pr_auc | 0.3232 | **0.3291** |
| test_baseline_pos_rate | 0.0556 | 0.0556 |
| trained_on_users | 10,004 | **10,004** |

`trained_on_users`が偶然ではなく完全一致した。これは`scripts/build_lookups.py`のtrain/val/test分割
（SEED=42・N_USERS_TARGET=15,000、`02_model.ipynb`セル3と同一パラメータ）が消失前の本番モデルの
学習時と同じ分割を再現できていることを意味する。当初は「既存モデルとの数値的な再現は狙わない」
方針だったが、結果的にAUC/PR-AUCも同水準に戻り、実質的に再現された。

## 再発防止（`CLAUDE.md`に追記済み）

- `.gitignore`で除外する生成物は、生成スクリプトを必ずコミットする
- ノートブックでアドホックに作った成果物を本番に使わない
- `data/processed/`は`scripts/build_lookups.py`で完全に再生成できること
- モデルは`scripts/train_model.py`で再学習できること
