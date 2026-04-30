import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { EmptyStage } from "../chrome/EmptyStage";

export function GoalRoute() {
  const { t } = useTranslation();
  const { goalId } = useParams<{ goalId: string }>();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.goal.placeholder_title")}
      description={t("routes.goal.placeholder_description", { goalId: goalId ?? "—" })}
    />
  );
}
