"""anime.csv の Genres 列（英語表記）に対する日本語対応表。

`api/services/explain.py`（reasons/evidence の文言生成）と `GET /genres`
（入力画面のジャンル表示・絞り込み選択肢の日本語化）の両方から参照される、
唯一の翻訳表（このファイルが正）。全43種を網羅する
（store.all_genres は anime.csv の全ジャンルから構築されるため、対象は
この43種に限られる）。ジャンルが増えたときはここに追記すること。
"""

GENRE_JP: dict[str, str] = {
    "Action": "アクション", "Adventure": "アドベンチャー", "Cars": "カーレース",
    "Comedy": "コメディ", "Dementia": "異色", "Demons": "悪魔", "Drama": "ドラマ",
    "Ecchi": "エッチ", "Fantasy": "ファンタジー", "Game": "ゲーム", "Harem": "ハーレム",
    "Hentai": "成人向け", "Historical": "歴史", "Horror": "ホラー", "Josei": "女性向け",
    "Kids": "子供向け", "Magic": "魔法", "Martial Arts": "格闘", "Mecha": "メカ",
    "Military": "ミリタリー", "Music": "音楽", "Mystery": "ミステリー", "Parody": "パロディ",
    "Police": "刑事", "Psychological": "心理", "Romance": "恋愛", "Samurai": "時代劇",
    "School": "学園", "Sci-Fi": "SF", "Seinen": "青年向け", "Shoujo": "少女向け",
    "Shoujo Ai": "百合(ソフト)", "Shounen": "少年向け", "Shounen Ai": "BL(ソフト)",
    "Slice of Life": "日常系", "Space": "宇宙", "Sports": "スポーツ", "Super Power": "超能力",
    "Supernatural": "超自然", "Thriller": "スリラー", "Vampire": "ヴァンパイア", "Yaoi": "BL",
    "Yuri": "百合",
}


def jp(genre: str) -> str:
    return GENRE_JP.get(genre, genre)
