import type { Label, QuestionItem } from "../api/types";
import styles from "./QuestionCard.module.css";

interface Props {
  item: QuestionItem;
  label: Label | null;
  onSelect: (label: Label) => void;
}

/**
 * 作品カード。3ボタンは排他選択、再タップで解除。
 * 回答してもカードは消さない（押し間違いの修正を可能にするため / UI仕様書3.2）。
 * MALの画像は使わない。
 */
export default function QuestionCard({ item, label, onSelect }: Props) {
  const genreText = item.genres.slice(0, 2).join("・");
  const episodesText = item.episodes ? `全${item.episodes}話` : "話数不明";
  const yearText = item.year ?? "年代不明";

  return (
    <div className={`${styles.card} ${label ? styles.selected : ""}`}>
      <p className={styles.title}>{item.title}</p>
      <p className={styles.meta}>
        {yearText} / {episodesText}
        {genreText ? ` / ${genreText}` : ""}
      </p>
      <div className={styles.buttons}>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnLoved} ${label === "loved" ? styles.active : ""}`}
          onClick={() => onSelect("loved")}
        >
          ♥ 好き
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnCompleted} ${label === "completed" ? styles.active : ""}`}
          onClick={() => onSelect("completed")}
        >
          ✓ 完走
        </button>
        <button
          type="button"
          className={`${styles.btn} ${styles.btnDropped} ${label === "dropped" ? styles.active : ""}`}
          onClick={() => onSelect("dropped")}
        >
          ⏸ 途中で止まった
        </button>
      </div>
    </div>
  );
}
