import { useTranslation } from "react-i18next";

import { EmptyStage } from "../chrome/EmptyStage";

export function ReviewRoute() {
  const { t } = useTranslation();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.review.placeholder_title")}
      description={t("routes.review.placeholder_description")}
    />
  );
}
