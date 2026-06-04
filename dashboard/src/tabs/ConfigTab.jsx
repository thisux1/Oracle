import { useMemo, useState } from "react";
import { useOracleStore } from "../stores/useOracleStore";
import ConfigSection from "../components/ConfigSection";
import ToggleSwitch from "../components/ToggleSwitch";
import { Eye, EyeOff, Save, CheckCircle, AlertCircle } from "lucide-react";

const RESTART_FIELDS = new Set([
  "user_token",
  "user_mention_text",
  "user_id",
  "channel_id",
  "guild_id",
  "telegram_bot_token",
  "telegram_chat_id",
  "bankroll",
  "max_losses",
  "initial_step",
  "seed",
  "work_command",
  "lootbox_type",
  "is_married",
  "partner_name",
  "is_ascended",
]);

function TextField({ label, field, value, onChange, isPassword = false, placeholder = "" }) {
  const [visible, setVisible] = useState(false);
  const isSecret = isPassword && !visible;

  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <label className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
          {label}
        </label>
        {RESTART_FIELDS.has(field) ? (
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--accent-warning-dim)", color: "var(--accent-warning)" }}
          >
            restart
          </span>
        ) : (
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--accent-success-dim)", color: "var(--accent-success)" }}
          >
            runtime
          </span>
        )}
      </div>
      <div className="relative">
        <input
          type={isPassword && !visible ? "password" : "text"}
          value={value || ""}
          onChange={(e) => onChange(field, e.target.value)}
          placeholder={placeholder}
          className="input pr-10"
          style={{ fontFamily: isPassword ? "var(--font-mono)" : undefined }}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1"
            style={{ color: "var(--text-dim)" }}
          >
            {visible ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SelectField({ label, field, value, onChange, options = [] }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
        {label}
      </label>
      <select
        value={value || ""}
        onChange={(e) => onChange(field, e.target.value)}
        className="input appearance-none"
        style={{ cursor: "pointer" }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumberField({ label, field, value, onChange, min, max, step }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
        {label}
      </label>
      <input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(field, e.target.value)}
        min={min}
        max={max}
        step={step}
        className="input"
        style={{ fontFamily: "var(--font-mono)" }}
      />
    </div>
  );
}

export default function ConfigTab() {
  const config = useOracleStore((s) => s.config);
  const setConfigField = useOracleStore((s) => s.setConfigField);
  const saveConfig = useOracleStore((s) => s.saveConfig);
  const savingConfig = useOracleStore((s) => s.savingConfig);
  const configDirty = useOracleStore((s) => s.configDirty);
  const activeProfile = useOracleStore((s) => s.activeProfile);

  const [saveState, setSaveState] = useState(null); // null | "success" | "error"
  const [errorMsg, setErrorMsg] = useState("");

  const handleChange = (field, value) => {
    setConfigField(field, value);
    setSaveState(null);
  };

  const handleSave = async () => {
    try {
      await saveConfig(config, activeProfile);
      setSaveState("success");
      setErrorMsg("");
      setTimeout(() => setSaveState(null), 3000);
    } catch (err) {
      setSaveState("error");
      setErrorMsg(err?.message || "Failed to save");
    }
  };

  const doToggle = (field) => (checked) => handleChange(field, checked ? "true" : "false");
  const isTrue = (field) => config[field] === "true" || config[field] === true;

  return (
    <div className="space-y-4">
      {/* Credentials */}
      <ConfigSection title="Credentials" icon="&#128273;" requiresRestart defaultOpen>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="User Token" field="user_token" value={config.user_token} onChange={handleChange} isPassword placeholder="Discord token" />
          <TextField label="User Mention Text" field="user_mention_text" value={config.user_mention_text} onChange={handleChange} placeholder="@user" />
          <TextField label="Channel ID" field="channel_id" value={config.channel_id} onChange={handleChange} placeholder="123456789" />
          <TextField label="Guild ID" field="guild_id" value={config.guild_id} onChange={handleChange} placeholder="987654321" />
        </div>
      </ConfigSection>

      {/* General */}
      <ConfigSection title="General" icon="&#9881;&#65039;">
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField label="Random Interval (s)" field="random_interval" value={config.random_interval} onChange={handleChange} min={1} max={300} step={1} />
          <NumberField label="Typo Chance (%)" field="typo_chance" value={config.typo_chance} onChange={handleChange} min={0} max={100} step={1} />
        </div>
      </ConfigSection>

      {/* Adventure */}
      <ConfigSection title="Adventure" icon="&#9876;&#65039;">
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField label="Life Boost Before Adv" field="life_boost_before_adv" value={config.life_boost_before_adv} onChange={handleChange} min={0} max={100} />
          <TextField label="Adventure Area" field="adventure_area" value={config.adventure_area} onChange={handleChange} />
          <TextField label="Current Area" field="current_area" value={config.current_area} onChange={handleChange} />
          <TextField label="Zombie Horde Response" field="zombie_horde_event_response" value={config.zombie_horde_event_response} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Economy */}
      <ConfigSection title="Economy" icon="&#127805;">
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Lootbox Type"
            field="lootbox_type"
            value={config.lootbox_type}
            onChange={handleChange}
            options={[
              { value: "normal", label: "Normal" },
              { value: "premium", label: "Premium" },
            ]}
          />
          <TextField label="Seed" field="seed" value={config.seed} onChange={handleChange} />
          <TextField label="Work Command" field="work_command" value={config.work_command} onChange={handleChange} />
          <NumberField label="Bankroll" field="bankroll" value={config.bankroll} onChange={handleChange} min={0} />
          <NumberField label="Max Losses" field="max_losses" value={config.max_losses} onChange={handleChange} min={0} />
          <NumberField label="Initial Step" field="initial_step" value={config.initial_step} onChange={handleChange} min={0} />
        </div>
      </ConfigSection>

      {/* Telegram */}
      <ConfigSection title="Telegram" icon="&#128241;" requiresRestart>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Bot Token" field="telegram_bot_token" value={config.telegram_bot_token} onChange={handleChange} isPassword placeholder="123:ABC" />
          <TextField label="Chat ID" field="telegram_chat_id" value={config.telegram_chat_id} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Features */}
      <ConfigSection title="Features" icon="&#9989;">
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { field: "do_hunt", label: "Hunt" },
            { field: "do_adv", label: "Adventure" },
            { field: "do_farm", label: "Farm" },
            { field: "do_work", label: "Work" },
            { field: "do_training", label: "Training" },
            { field: "do_daily", label: "Daily" },
            { field: "do_weekly", label: "Weekly" },
            { field: "do_quest", label: "Quest" },
            { field: "do_lootbox", label: "Lootbox" },
            { field: "do_dungeon", label: "Dungeon" },
            { field: "do_card_hand", label: "Card Hand" },
            { field: "do_ultr", label: "Ultra" },
          ].map(({ field, label }) => (
            <ToggleSwitch
              key={field}
              label={label}
              checked={isTrue(field)}
              onChange={doToggle(field)}
            />
          ))}
        </div>
      </ConfigSection>

      {/* Advanced */}
      <ConfigSection title="Advanced" icon="&#129514;">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Card Hand Action" field="card_hand_action" value={config.card_hand_action} onChange={handleChange} />
          <NumberField label="TC Quantity" field="tc_quantity" value={config.tc_quantity} onChange={handleChange} min={1} />
          <ToggleSwitch label="Is Eternal" checked={isTrue("is_eternal")} onChange={doToggle("is_eternal")} />
          <ToggleSwitch label="Is Married" checked={isTrue("is_married")} onChange={doToggle("is_married")} />
          <TextField label="Partner Name" field="partner_name" value={config.partner_name} onChange={handleChange} />
          <ToggleSwitch label="Is Ascended" checked={isTrue("is_ascended")} onChange={doToggle("is_ascended")} />
          <TextField label="Admin IDs" field="admin_ids" value={config.admin_ids} onChange={handleChange} placeholder="id1,id2" />
          <TextField label="TC Stop On" field="tc_stop_on" value={config.tc_stop_on} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Schedule */}
      <ConfigSection title="Schedule" icon="&#128336;">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Sleep At" field="sleep_at" value={config.sleep_at} onChange={handleChange} placeholder="23:30" />
          <TextField label="Wake Up At" field="wake_up_at" value={config.wake_up_at} onChange={handleChange} placeholder="07:00" />
          <TextField label="Theme" field="theme" value={config.theme} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Save bar */}
      <div
        className="glass sticky bottom-0 z-10 flex items-center justify-between rounded-2xl px-4 py-3"
        style={{ border: "1px solid var(--border-subtle)" }}
      >
        <div className="flex items-center gap-2 text-sm">
          {saveState === "success" ? (
            <>
              <CheckCircle size={16} style={{ color: "var(--accent-success)" }} />
              <span style={{ color: "var(--accent-success)" }}>Saved</span>
            </>
          ) : saveState === "error" ? (
            <>
              <AlertCircle size={16} style={{ color: "var(--accent-danger)" }} />
              <span style={{ color: "var(--accent-danger)" }}>{errorMsg}</span>
            </>
          ) : configDirty ? (
            <span style={{ color: "var(--text-dim)" }}>Unsaved changes</span>
          ) : (
            <span style={{ color: "var(--text-dim)" }}>No changes</span>
          )}
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={savingConfig || !configDirty}
          className="btn btn-primary"
        >
          <Save size={14} />
          {savingConfig ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
