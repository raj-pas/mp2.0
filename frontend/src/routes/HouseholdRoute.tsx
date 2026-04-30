import { useTranslation } from "react-i18next";

import { EmptyStage } from "../chrome/EmptyStage";

export function HouseholdRoute() {
  const { t } = useTranslation();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.household.placeholder_title")}
      description={t("routes.household.placeholder_description")}
    />
  );
}
