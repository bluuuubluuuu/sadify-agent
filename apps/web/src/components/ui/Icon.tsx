import type { CSSProperties, ReactNode } from "react";

/**
 * Inline, dependency-free icon set in a Phosphor-style (rounded, soft strokes).
 * Back navigation uses `caretLeft` (a soft chevron), never an arrow-with-tail.
 * Icon-only buttons MUST wrap <Icon> in a <button aria-label="…"> at the call site.
 */
export type IconName =
  | "sparkle"
  | "folder"
  | "cloudCheck"
  | "clock"
  | "paperclip"
  | "fileText"
  | "book"
  | "uploadCloud"
  | "user"
  | "google"
  | "caretLeft"
  | "caretRight"
  | "caretDown"
  | "plus"
  | "check"
  | "checkCircle"
  | "circle"
  | "halfCircle"
  | "info"
  | "question"
  | "eye"
  | "edit"
  | "arrowRight"
  | "openExternal"
  | "signOut"
  | "x"
  | "swap"
  | "menu";

const GLYPHS: Record<IconName, ReactNode> = {
  sparkle: <path d="M12 3.2l1.9 5 5 1.9-5 1.9-1.9 5-1.9-5-5-1.9 5-1.9z" />,
  folder: (
    <path d="M3 7a2 2 0 0 1 2-2h3.6a2 2 0 0 1 1.4.6L11.5 7H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
  ),
  cloudCheck: (
    <>
      <path d="M7 18a4 4 0 0 1-.5-7.97 6 6 0 0 1 11.4 1.2A3.5 3.5 0 0 1 17.5 18z" />
      <path d="M9.5 13.5l1.8 1.8 3.2-3.6" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </>
  ),
  paperclip: (
    <path d="M20.5 11.5l-8.4 8.4a5 5 0 0 1-7.1-7.1l8.5-8.5a3.4 3.4 0 0 1 4.8 4.8l-8.5 8.5a1.8 1.8 0 0 1-2.6-2.6l7.8-7.8" />
  ),
  fileText: (
    <>
      <path d="M7 3.5h6.5L19 9v11a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 6 20V5A1.5 1.5 0 0 1 7 3.5z" />
      <path d="M13.5 3.5V9H19" />
      <path d="M9 13h6M9 16.5h4" />
    </>
  ),
  book: (
    <>
      <path d="M6 4.5h11A1.5 1.5 0 0 1 18.5 6v13.5H7A1.5 1.5 0 0 1 5.5 18V6A1.5 1.5 0 0 1 7 4.5z" />
      <path d="M5.5 18A1.5 1.5 0 0 1 7 16.5h11.5" />
    </>
  ),
  uploadCloud: (
    <>
      <path d="M7 17.5a4 4 0 0 1-.5-7.97 6 6 0 0 1 11.4 1.2A3.5 3.5 0 0 1 17.5 17.5" />
      <path d="M12 12v7M9.2 14.2L12 11.4l2.8 2.8" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M5.5 19.5a6.5 6.5 0 0 1 13 0" />
    </>
  ),
  google: <path d="M16.5 9.2A5 5 0 1 0 17.6 13H12.4" />,
  caretLeft: <path d="M15 6l-6 6 6 6" />,
  caretRight: <path d="M9 6l6 6-6 6" />,
  caretDown: <path d="M6 9l6 6 6-6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  check: <path d="M5 12.5l4.2 4.2L19 7" />,
  checkCircle: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.2l2.6 2.6L16 9" />
    </>
  ),
  circle: <circle cx="12" cy="12" r="8.5" />,
  halfCircle: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v5M12 8h.01" />
    </>
  ),
  question: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.6 9.2a2.4 2.4 0 1 1 3 2.4v1.2M12 16h.01" />
    </>
  ),
  eye: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  edit: (
    <>
      <path d="M12 20h8.5" />
      <path d="M16.5 3.6a2 2 0 0 1 2.9 2.9L7.5 18.4l-3.8 1 1-3.8z" />
    </>
  ),
  arrowRight: <path d="M5 12h13M12.5 6l6 6-6 6" />,
  openExternal: (
    <>
      <path d="M14 4.5h5.5V10" />
      <path d="M19.5 4.5l-8 8" />
      <path d="M18 13.5V18a1.5 1.5 0 0 1-1.5 1.5h-10A1.5 1.5 0 0 1 5 18V8a1.5 1.5 0 0 1 1.5-1.5H11" />
    </>
  ),
  signOut: (
    <>
      <path d="M9.5 5.5H6A1.5 1.5 0 0 0 4.5 7v10A1.5 1.5 0 0 0 6 18.5h3.5" />
      <path d="M16 16.5l4.5-4.5L16 7.5M20.5 12h-11" />
    </>
  ),
  x: <path d="M6.5 6.5l11 11M17.5 6.5l-11 11" />,
  swap: <path d="M6.5 8.5h12l-3.2-3.2M17.5 15.5h-12l3.2 3.2" />,
  menu: <path d="M4.5 7h15M4.5 12h15M4.5 17h15" />,
};

export function Icon({
  name,
  size = 24,
  color = "currentColor",
  stroke = 1.9,
  style,
  className,
}: {
  name: IconName;
  size?: number;
  color?: string;
  stroke?: number;
  style?: CSSProperties;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      style={style}
      className={className}
    >
      {GLYPHS[name]}
    </svg>
  );
}
