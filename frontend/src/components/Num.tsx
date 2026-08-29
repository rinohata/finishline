import type { ReactNode } from "react";

type NumSize = "xl" | "lg" | "md" | "sm";

const SIZE_VAR: Record<NumSize, string> = {
  xl: "var(--fl-numeric-xl)",
  lg: "var(--fl-numeric-lg)",
  md: "var(--fl-numeric-md)",
  sm: "var(--fl-numeric-sm)",
};

/** 数字専用の表示コンポーネント。Inter + tabular-numsで統一し、装飾（グラデーション
 * 背景・斜体・絵文字併記）は一切加えない
 * （docs/design_guidelines.md「パッケージはカラフルに、数字は硬派に」）。
 * 数値を表示する箇所は必ずこれを通すこと。 */
export default function Num({
  children,
  size = "md",
  color,
}: {
  children: ReactNode;
  size?: NumSize;
  color?: string;
}) {
  return (
    <span className="fl-numeric" style={{ fontSize: SIZE_VAR[size], color }}>
      {children}
    </span>
  );
}
