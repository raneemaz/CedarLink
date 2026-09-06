import { useTranslation } from "react-i18next";

import { SOCIAL_PLATFORMS } from "./socialPlatforms";

/**
 * A store's social and contact links, as icons.
 *
 * The icon carries no text, so each link needs an accessible name of its
 * own — `aria-label` plus a `title`, both naming the platform and the
 * store, since "Instagram" on its own tells a screen-reader user nothing
 * about where it goes.
 *
 * Every link is outbound and opens in a new tab, so every link carries
 * `rel="noopener noreferrer"`: without `noopener` the opened page gets a
 * handle on this one through `window.opener`, and these hrefs were typed
 * by a vendor.
 *
 * Renders nothing when a store has listed none, so callers can drop it in
 * without a surrounding conditional.
 */
function StoreSocialLinks({ links, storeName, className = "" }) {
  const { t } = useTranslation();

  if (!links || links.length === 0) return null;

  const byPlatform = new Map(links.map((link) => [link.platform, link]));

  const shown = SOCIAL_PLATFORMS.filter(({ id }) => byPlatform.has(id));

  if (shown.length === 0) return null;

  return (
    <div className={className}>
      <h2 className="text-sm font-semibold text-ink">
        {t("social.heading")}
      </h2>

      <ul className="mt-3 flex flex-wrap gap-2">
        {shown.map(({ id, Icon }) => {
          // A per-platform template, not one "{{store}} on {{platform}}":
          // that reads correctly for Instagram and absurdly for Phone.
          const label = t(`social.linkLabel.${id}`, { store: storeName });

          return (
            <li key={id}>
              <a
                href={byPlatform.get(id).value}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={label}
                title={label}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-line text-ink-secondary transition hover:border-cedar-ring hover:text-cedar"
              >
                <Icon size={18} aria-hidden="true" />
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default StoreSocialLinks;
