# FinishLine

アニメの完走予測サービス（ポートフォリオ用途・非商用）。

仕様は [docs/requirements.md](docs/requirements.md) と [docs/ui_spec.md](docs/ui_spec.md) を参照。

## 重要: プロジェクトの置き場所

このプロジェクトは **`~/dev` 配下**に置くこと。`~/Documents` など iCloud Drive
の同期対象ディレクトリに置くと、`data/raw/animelist.csv`（1.9GB）のような大きい
ファイルがオンデマンドダウンロードのプレースホルダ化し、読み込み中に処理が止まる
（ファイル本体が手元に無い状態になる）。

## セットアップ

### バックエンド

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### フロントエンド

```bash
cd frontend
npm install
```

## 起動

### バックエンド（ポート 8000 固定。フロントエンドの vite proxy がこのポートに向く）

```bash
source .venv/bin/activate
python3 -m uvicorn api.main:app --port 8000
```

起動時に以下を読み込む（`animelist.csv` は読まない）。1つでも欠けると起動に失敗する。

- `data/raw/anime.csv`
- `data/question_pool.json` / `data/dropout_curves.json`
- `data/processed/` 配下の事前計算済みルックアップ一式・埋め込み
- `models/dropout_predictor.lgb` / `models/feature_columns.json`

### フロントエンド

```bash
cd frontend
npm run dev
```

## data/raw の取得

`data/raw/` は `.gitignore` 対象。以下を Kaggle から取得して配置する。

- 取得元: [hernan4444/anime-recommendation-database-2020](https://www.kaggle.com/datasets/hernan4444/anime-recommendation-database-2020)（Kaggle アカウントが必要）

| ファイル | サイズ目安 | 必要な作業 |
|---|---|---|
| `anime.csv` | 数MB | API 起動・全ノートブック（作品メタデータの起点。これが無いと起動不可） |
| `anime_with_synopsis.csv` | 6.9MB | あらすじ埋め込み生成（`data/processed/anime_embeddings.npy` のキャッシュが無い場合のみ） |
| `animelist.csv` | 1.9GB（約1億900万行） | ユーザー行動データ集計全般。`data/processed/` 配下のほとんどのルックアップ（訓練ユーザーのみで算出する作品平均完走率など、`CLAUDE.md` のデータリーク防止規定に対応）の再生成に必須 |
| `anilist/anilist_anime_data_complete.pkl` | 257MB | 続編/前作（franchise）判定用。取得元は別データセット: [calebmwelsh/anilist-anime-dataset](https://www.kaggle.com/datasets/calebmwelsh/anilist-anime-dataset)（AniList GraphQL API由来）。`scripts/build_relations.py`が`~/.kaggle/kaggle.json`の認証情報を使って自動ダウンロードするため、事前に`kaggle datasets download`で手動配置する必要は無い（`kaggle`パッケージと認証情報のみ用意すればよい） |

`data/processed/` も `.gitignore` 対象で、以下のスクリプトの実行により生成される（`notebooks/`はPhase検証時の実験用で、本番の再生成には使わない。詳細は `CLAUDE.md`「再現性」節・`reports/data_recovery.md`・`reports/franchise_prerequisite.md` を参照）。

```bash
python3 -m scripts.build_lookups     # data/processed/ のルックアップ・埋め込み一式
python3 -m scripts.train_model       # models/dropout_predictor.lgb の再学習
python3 -m scripts.build_relations   # data/processed/anime_relations.json（続編/前作関係）
```

## データ出典・ライセンス

- データ出典: Hernan4444 / anime-recommendation-database-2020 (Kaggle)
- 続編/前作関係のデータ出典: calebmwelsh / anilist-anime-dataset (Kaggle, AniList GraphQL API由来)
- 元データ提供: MyAnimeList, AniList, Jikan API
- Kaggle のデータセットページに記載のライセンス条件に従うこと
- 本プロジェクトは非商用・ポートフォリオ用途である
