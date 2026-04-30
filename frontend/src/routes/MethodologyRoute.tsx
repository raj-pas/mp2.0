import { useTranslation } from "react-i18next";

import { EmptyStage } from "../chrome/EmptyStage";

export function MethodologyRoute() {
  const { t } = useTranslation();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.methodology.placeholder_title")}
      description={t("routes.methodology.placeholder_description")}
    />
  );
}
