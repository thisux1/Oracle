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

function TextField({ label, field, value, onChange, isPassword = false, placeholder = "", type = "text", isRequired = false }) {
  const [visible, setVisible] = useState(false);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="block text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
          {label} {isRequired && <span style={{ color: "var(--accent-danger)" }}>*</span>}
        </label>
        {RESTART_FIELDS.has(field) ? (
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--accent-warning-dim)", color: "var(--accent-warning)" }}
          >
            reiniciar
          </span>
        ) : (
          <span
            className="rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide"
            style={{ background: "var(--accent-success-dim)", color: "var(--accent-success)" }}
          >
            tempo real
          </span>
        )}
      </div>
      <div className="relative">
        <input
          type={isPassword && !visible ? "password" : type}
          value={value === "none" && type === "time" ? "" : (value || "")}
          onChange={(e) => {
            let val = e.target.value;
            if (type === "time" && !val) val = "none";
            onChange(field, val);
          }}
          placeholder={placeholder}
          className="input pr-10"
          style={{ 
            fontFamily: isPassword || type === "time" ? "var(--font-mono)" : undefined,
            border: isRequired && (!value || value === "none") ? "1px solid var(--accent-danger)" : undefined
          }}
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
      setErrorMsg(err?.message || "Falha ao salvar");
    }
  };

  const doToggle = (field) => (checked) => handleChange(field, checked ? "true" : "false");
  const isTrue = (field) => config[field] === "true" || config[field] === true;

  return (
    <div className="space-y-4">
      {/* Credentials */}
      <ConfigSection title="Credenciais" icon="&#128273;" requiresRestart defaultOpen>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Token do Usuário" field="user_token" value={config.user_token} onChange={handleChange} isPassword placeholder="Token do Discord" isRequired />
          <TextField label="ID do Canal" field="channel_id" value={config.channel_id} onChange={handleChange} placeholder="123456789" isRequired />
          <TextField label="ID do Servidor (Guild)" field="guild_id" value={config.guild_id} onChange={handleChange} placeholder="987654321" isRequired />
        </div>
      </ConfigSection>

      {/* General */}
      <ConfigSection title="Geral" icon="&#9881;&#65039;">
        <div className="grid gap-4 sm:grid-cols-2">
          <ToggleSwitch label="Intervalo Aleatório (atraso humanizador)" checked={isTrue("random_interval")} onChange={doToggle("random_interval")} />
          <NumberField label="Chance de Erro de Digitação (ex: 0.05 = 5%)" field="typo_chance" value={config.typo_chance} onChange={handleChange} min={0} max={1} step={0.01} />
        </div>
      </ConfigSection>

      {/* Adventure */}
      <ConfigSection title="Adventure" icon="&#9876;&#65039;">
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Aumento de Vida antes de Adventure"
            field="life_boost_before_adv"
            value={config.life_boost_before_adv}
            onChange={handleChange}
            options={[
              { value: "none", label: "Nenhum (None)" },
              { value: "a", label: "A" },
              { value: "b", label: "B" },
              { value: "c", label: "C" },
            ]}
          />
          <TextField label="Área de Adventure" field="adventure_area" value={config.adventure_area} onChange={handleChange} />
          <TextField label="Área Atual" field="current_area" value={config.current_area} onChange={handleChange} />
          <TextField label="Resposta ao Evento Zombie Horde" field="zombie_horde_event_response" value={config.zombie_horde_event_response} onChange={handleChange} />
          <TextField label="Comando de Aventura do Pet" field="pet_adventure_command" value={config.pet_adventure_command} onChange={handleChange} placeholder="rpg pet adv learn a (ex: find epic)" />
        </div>
      </ConfigSection>

      {/* Economy */}
      <ConfigSection title="Economia" icon="&#127805;">
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Tipo de Lootbox"
            field="lootbox_type"
            value={config.lootbox_type}
            onChange={handleChange}
            options={[
              { value: "common lb", label: "Common Lootbox" },
              { value: "uncommon lb", label: "Uncommon Lootbox" },
              { value: "rare lb", label: "Rare Lootbox" },
              { value: "ep lb", label: "Epic Lootbox" },
              { value: "ed lb", label: "Edgy Lootbox" },
            ]}
          />
          <TextField label="Seed" field="seed" value={config.seed} onChange={handleChange} />
          <TextField label="Comando de Trabalho (Work)" field="work_command" value={config.work_command} onChange={handleChange} />
          <NumberField label="Banca Máxima (Bankroll)" field="bankroll" value={config.bankroll} onChange={handleChange} min={0} />
          <NumberField label="Perdas Máximas (Max Losses)" field="max_losses" value={config.max_losses} onChange={handleChange} min={0} />
          <NumberField label="Passo Inicial (Initial Step)" field="initial_step" value={config.initial_step} onChange={handleChange} min={0} />
        </div>
      </ConfigSection>

      {/* Telegram */}
      <ConfigSection title="Telegram" icon="&#128241;" requiresRestart>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Token do Bot" field="telegram_bot_token" value={config.telegram_bot_token} onChange={handleChange} isPassword placeholder="123:ABC" />
          <TextField label="ID do Chat" field="telegram_chat_id" value={config.telegram_chat_id} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Features */}
      <ConfigSection title="Recursos (Features)" icon="&#9989;">
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
            { field: "do_duel", label: "Duel" },
            { field: "win_duel", label: "Win Duel" },
            { field: "do_pet", label: "Pets" },
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
      <ConfigSection title="Avançado" icon="&#129514;">
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField
            label="Ação do Card Hand"
            field="card_hand_action"
            value={config.card_hand_action}
            onChange={handleChange}
            options={[
              { value: "auto", label: "Auto (Híbrido — Neon + Override via Telegram)" },
              { value: "legacy_auto", label: "Legacy Auto (Automático direto via Neon)" },
            ]}
          />
          <NumberField label="Quantidade de TC" field="tc_quantity" value={config.tc_quantity} onChange={handleChange} min={1} />
          <ToggleSwitch label="Dungeon Eternal (Is Eternal)" checked={isTrue("is_eternal")} onChange={doToggle("is_eternal")} />
          <SelectField
            label="Tier de Eternal"
            field="eternal_tier"
            value={config.eternal_tier}
            onChange={handleChange}
            options={[
              { value: "t1", label: "T1" },
              { value: "t2", label: "T2" },
              { value: "t3", label: "T3" },
              { value: "t4", label: "T4" },
              { value: "t5", label: "T5" },
              { value: "t6", label: "T6" },
              { value: "t7", label: "T7" },
              { value: "t8", label: "T8" },
              { value: "t9", label: "T9" },
              { value: "t10", label: "T10" },
            ]}
          />
          <ToggleSwitch label="Casado (Is Married)" checked={isTrue("is_married")} onChange={doToggle("is_married")} />
          <TextField label="Nome do Parceiro(a)" field="partner_name" value={config.partner_name} onChange={handleChange} />
          <TextField label="ID do Parceiro de Duelo" field="duel_partner_id" value={config.duel_partner_id} onChange={handleChange} placeholder="ID do Discord" />
          <ToggleSwitch label="Ascendido (Is Ascended)" checked={isTrue("is_ascended")} onChange={doToggle("is_ascended")} />
          <TextField label="IDs dos Administradores" field="admin_ids" value={config.admin_ids} onChange={handleChange} placeholder="id1,id2" />
          <TextField label="Parar TC Em (TC Stop On)" field="tc_stop_on" value={config.tc_stop_on} onChange={handleChange} />
        </div>
      </ConfigSection>

      {/* Schedule */}
      <ConfigSection title="Agendamento" icon="&#128336;">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="Dormir às (Sleep At) (24h)" field="sleep_at" type="time" value={config.sleep_at} onChange={handleChange} />
          <TextField label="Acordar às (Wake Up At) (24h)" field="wake_up_at" type="time" value={config.wake_up_at} onChange={handleChange} />
          <SelectField
            label="Tema"
            field="theme"
            value={config.theme}
            onChange={handleChange}
            options={[
              { value: "cathedral", label: "Cathedral" },
              { value: "dracula", label: "Dracula" },
              { value: "nord", label: "Nord" },
              { value: "monokai", label: "Monokai Pro" },
              { value: "gruvbox", label: "Gruvbox" },
              { value: "catppuccin", label: "Catppuccin" },
              { value: "tokyonight", label: "Tokyo Night" },
              { value: "rosepine", label: "Rosé Pine" },
              { value: "solarized", label: "Solarized" },
              { value: "cyberpunk", label: "Cyberpunk" },
            ]}
          />
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
              <span style={{ color: "var(--accent-success)" }}>Salvo</span>
            </>
          ) : saveState === "error" ? (
            <>
              <AlertCircle size={16} style={{ color: "var(--accent-danger)" }} />
              <span style={{ color: "var(--accent-danger)" }}>{errorMsg}</span>
            </>
          ) : configDirty ? (
            <span style={{ color: "var(--text-dim)" }}>Alterações não salvas</span>
          ) : (
            <span style={{ color: "var(--text-dim)" }}>Sem alterações</span>
          )}
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={savingConfig || !configDirty}
          className="btn btn-primary"
        >
          <Save size={14} />
          {savingConfig ? "Salvando..." : "Salvar"}
        </button>
      </div>
    </div>
  );
}
