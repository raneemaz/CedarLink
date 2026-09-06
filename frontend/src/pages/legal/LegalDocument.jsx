import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import BackLink from "../../components/common/BackLink";
import { formatDate } from "../../utils/helpers";
import { LEGAL_LAST_UPDATED_ISO } from "./legalMeta";

/**
 * Shared shell for the Privacy Policy and Terms of Service pages.
 *
 * Both are static, translated documents with the same structure: a back
 * link, an "academic document" notice, a title, a single "last updated"
 * date driven by `legalMeta`, an intro, and a list of titled sections.
 * Only the namespace and the section order differ, so the layout lives
 * here once.
 *
 * Section bodies are plain translated strings. Paragraphs are separated by
 * a blank line; a block whose every line begins with "- " renders as a
 * bulleted list. Nothing here interprets markup beyond that.
 */
function Prose({ text }) {
  const blocks = text.split("\n\n");

  return blocks.map((block, index) => {
    const lines = block.split("\n");

    if (lines.every((line) => line.startsWith("- "))) {
      return (
        <ul
          key={index}
          className="mt-3 list-disc space-y-1.5 ps-5 text-body text-ink-body"
        >
          {lines.map((line, lineIndex) => (
            <li key={lineIndex}>{line.slice(2)}</li>
          ))}
        </ul>
      );
    }

    return (
      <p key={index} className="mt-3 text-body leading-relaxed text-ink-body">
        {block}
      </p>
    );
  });
}

export default function LegalDocument({ ns, sectionKeys, controls }) {
  const { t, i18n } = useTranslation();

  return (
    <div className="mx-auto max-w-3xl py-4">
      <BackLink to="/" className="mb-6">
        {t("common.backToCedarLink")}
      </BackLink>

      <div className="rounded-card border border-line-strong bg-paper-sunken p-4">
        <p className="text-small font-semibold text-ink">
          {t(`${ns}.academicNoticeTitle`)}
        </p>
        <p className="mt-1 text-small leading-relaxed text-ink-body">
          {t(`${ns}.academicNotice`)}
        </p>
      </div>

      <h1 className="mt-8 text-title font-bold text-ink">{t(`${ns}.title`)}</h1>
      <p className="mt-2 text-small text-ink-muted">
        {t(`${ns}.lastUpdated`, {
          date: formatDate(LEGAL_LAST_UPDATED_ISO, i18n.language),
        })}
      </p>

      <p className="mt-6 text-body leading-relaxed text-ink-body">
        {t(`${ns}.intro`)}
      </p>

      <div className="mt-8 space-y-8">
        {sectionKeys.map((key) => (
          <section key={key}>
            <h2 className="text-body font-semibold text-ink">
              {t(`${ns}.sections.${key}.title`)}
            </h2>
            <Prose text={t(`${ns}.sections.${key}.body`)} />

            {key === "contact" && controls && (
              <>
                <p className="mt-3 text-body leading-relaxed text-ink-body">
                  {t(`${ns}.controlsIntro`)}
                </p>
                <ul className="mt-3 space-y-2">
                  {controls.map(({ to, key: controlKey }) => (
                    <li key={controlKey}>
                      <Link
                        to={to}
                        className="text-body font-medium text-cedar hover:underline"
                      >
                        {t(`${ns}.controls.${controlKey}`)}
                      </Link>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
