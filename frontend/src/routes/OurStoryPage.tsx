import { useLanguage } from "../i18n";

export function OurStoryPage() {
  const { t } = useLanguage();
  return (
    <div className="page">
      <h1>{t("ourStory.title")}</h1>
      <p className="muted">{t("ourStory.intro")}</p>

      <section className="card">
        <h2>{t("ourStory.heading1")}</h2>
        <p>{t("ourStory.paragraph1a")}</p>
        <p>
          {t("ourStory.paragraph1bPre")}
          <strong>{t("ourStory.paragraph1bBold")}</strong>
          {t("ourStory.paragraph1bPost")}
        </p>
      </section>

      <section className="card">
        <h2>{t("ourStory.heading2")}</h2>
        <p>{t("ourStory.paragraph2a")}</p>
        <p>{t("ourStory.paragraph2b")}</p>
      </section>

      <section className="card">
        <h2>{t("ourStory.heading3")}</h2>
        <p>{t("ourStory.paragraph3a")}</p>
        <p>{t("ourStory.paragraph3b")}</p>
      </section>

      <p className="muted">{t("ourStory.disclaimer")}</p>
    </div>
  );
}
