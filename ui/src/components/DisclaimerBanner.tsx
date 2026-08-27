import { DISCLAIMER } from "../lib/constants";
import { Icon } from "./Icon";

export function DisclaimerBanner() {
  return (
    <div
      role="note"
      aria-label="Disclaimer"
      className="bg-disclaimer-bg border-l-4 border-tertiary-container rounded-r-lg px-md py-sm flex items-start gap-sm w-full shrink-0 shadow-sm"
    >
      <Icon name="info" className="text-disclaimer-text shrink-0 mt-0.5" filled />
      <p className="text-disclaimer-text font-body-sm text-body-sm font-semibold m-0">
        {DISCLAIMER}
      </p>
    </div>
  );
}
