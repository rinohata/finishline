/**
 * docs/design_guidelines.md「絵文字の扱い」: ⚠ 📉 ▼ を線画SVGアイコンに置き換える。
 * すべて currentColor で塗るため、呼び出し側の color / style.color で着色する。
 * 数値の隣には置かない（意味を示すラベル・見出しの位置でのみ使用する）。
 */

interface IconProps {
  size?: number;
  className?: string;
}

/** 注意色（at_risk等）のトライアングル警告アイコン。⚠の置き換え。 */
export function WarningIcon({ size = 14, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      style={{ display: "inline-block", verticalAlign: "-2px" }}
    >
      <path
        d="M10 2.5 18 17H2L10 2.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
        fill="none"
      />
      <line x1="10" y1="8" x2="10" y2="11.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="10" cy="14" r="1" fill="currentColor" />
    </svg>
  );
}

/** 右肩下がりの折れ線アイコン。📉の置き換え。 */
export function TrendDownIcon({ size = 14, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      style={{ display: "inline-block", verticalAlign: "-2px" }}
    >
      <path d="M3 5 8 11 11.5 8 17 15" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 15h5v-5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 開閉トグル用の下向きシェブロン。▼の置き換え。 */
export function ChevronIcon({ size = 12, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      style={{ display: "inline-block", verticalAlign: "-1px" }}
    >
      <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/** 情報ノート用のインフォアイコン。ⓘの置き換え（EstimatedNote等）。 */
export function InfoIcon({ size = 14, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      className={className}
      aria-hidden
      style={{ display: "inline-block", verticalAlign: "-2px" }}
    >
      <circle cx="10" cy="10" r="8.2" stroke="currentColor" strokeWidth="1.6" />
      <line x1="10" y1="9" x2="10" y2="14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="10" cy="6.3" r="1" fill="currentColor" />
    </svg>
  );
}
