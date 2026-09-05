/**
 * Three marks lucide no longer ships.
 *
 * lucide-react dropped its brand icons, so Instagram, Facebook and TikTok
 * have to be drawn here. They are deliberately plain outlines in lucide's
 * own house style — 24x24 viewBox, 2px stroke, round caps and joins, colour
 * inherited from `currentColor` — so they sit in a row with Globe, Mail and
 * Phone without looking pasted in from somewhere else.
 *
 * Same prop shape as a lucide icon (`size`, `className`, and anything else
 * passed through), so callers cannot tell the difference.
 */

function Svg({ size = 24, children, ...rest }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  );
}

export function InstagramIcon(props) {
  return (
    <Svg {...props}>
      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
    </Svg>
  );
}

export function FacebookIcon(props) {
  return (
    <Svg {...props}>
      <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
    </Svg>
  );
}

export function TiktokIcon(props) {
  return (
    <Svg {...props}>
      <path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5" />
    </Svg>
  );
}
