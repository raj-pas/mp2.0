import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

export function BrandMark() {
  const { t } = useTranslation();
  return (
    <Link
      to="/"
      title={t("topbar.brand_home_title")}
      className="flex items-center gap-2 text-ink no-underline transition-opacity hover:opacity-70"
    >
      <span className="grid h-6 w-6 place-items-center bg-ink font-serif text-sm italic font-semibold text-paper">
        M
      </span>
      <span className="font-serif text-sm font-medium tracking-tight text-ink">
        {t("topbar.brand")}
      </span>
    </Link>
  );
}
