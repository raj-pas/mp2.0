import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";

import { EmptyStage } from "../chrome/EmptyStage";

export function AccountRoute() {
  const { t } = useTranslation();
  const { accountId } = useParams<{ accountId: string }>();
  return (
    <EmptyStage
      phaseLabel={t("scaffold.phase_label_r2")}
      title={t("routes.account.placeholder_title")}
      description={t("routes.account.placeholder_description", {
        accountId: accountId ?? "—",
      })}
    />
  );
}
