import { useOracleStore } from "../stores/useOracleStore";
import { translations } from "../lib/locales";

export function useTranslation() {
  const language = useOracleStore((s) => s.config?.language || "pt");

  const t = (key) => {
    const langData = translations[language] || translations.pt;
    return langData[key] ?? translations.pt[key] ?? key;
  };

  return { t, language };
}
