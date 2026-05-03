/**
 * TODO(canon §13.0.1): pilot-mode disclaimer surface deferred — iterative
 * scope per locked decision #17. Add ribbon under topbar or per-recommendation
 * footer when finalized with Lori.
 */
import { Home, Sigma, Zap } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";

import { BrandMark } from "./BrandMark";
import { ClientPicker } from "./ClientPicker";
import { ModeToggle, type GroupByMode } from "./ModeToggle";
import { FeedbackButton } from "./FeedbackButton";
import { UserChip } from "./UserChip";

interface TopBarProps {
  selectedClientId: string | null;
  onSelectClient: (id: string) => void;
  groupBy: GroupByMode;
  onChangeGroupBy: (value: GroupByMode) => void;
  user: { name: string; role: string };
  showClientControls: boolean;
}

export function TopBar({
  selectedClientId,
  onSelectClient,
  groupBy,
  onChangeGroupBy,
  user,
  showClientControls,
}: TopBarProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <header
      className="flex h-12 flex-shrink-0 items-center gap-3.5 border-b border-hairline-2 bg-paper px-[18px] shadow-sm"
      role="banner"
    >
      <BrandMark />

      {showClientControls && (
        <>
          <Divider />
          <ClientPicker
            selectedId={selectedClientId}
            onSelect={onSelectClient}
            enabled={showClientControls}
          />
          <Divider />
          <Button
            variant="outline"
            size="sm"
            onClick={() => navigate("/")}
            aria-label={t("topbar.home_label")}
          >
            <Home aria-hidden className="h-3.5 w-3.5" />
            <span>{t("topbar.home")}</span>
          </Button>
          <ModeToggle
            label={t("topbar.group_by_label")}
            options={[
              { value: "by-account", label: t("topbar.group_by_account") },
              { value: "by-goal", label: t("topbar.group_by_goal") },
            ]}
            value={groupBy}
            onChange={onChangeGroupBy}
          />
        </>
      )}

      <div className="flex-1" />

      <Button
        variant="default"
        size="sm"
        onClick={() => {
          /* Report flow ships in R10 polish (locked decision #17 / parking-lot #8). */
        }}
        aria-label={t("topbar.report")}
        title={t("topbar.report_title")}
      >
        <Zap aria-hidden className="h-3.5 w-3.5 text-accent" />
        <span>{t("topbar.report")}</span>
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate("/methodology")}
        aria-label={t("topbar.methodology_label")}
        title={t("topbar.methodology_title")}
      >
        <Sigma aria-hidden className="h-3.5 w-3.5" />
        <span>{t("topbar.methodology")}</span>
      </Button>

      <Divider />
      <FeedbackButton />
      <UserChip name={user.name} role={user.role} />
    </header>
  );
}

function Divider() {
  return <div aria-hidden className="h-[22px] w-px bg-hairline-2" />;
}
