import { useTranslation } from "react-i18next";

import { EmptyStage } from "../chrome/EmptyStage";

export function CmaRoute() {
  const { t } = useTranslation();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.cma.placeholder_title")}
      description={t("routes.cma.placeholder_description")}
    />
  );
}
