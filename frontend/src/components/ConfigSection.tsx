import { useEffect, useState } from 'react';
import { authFetchJson } from '../api';

interface ModelConfig {
  purpose: string;
  provider: string;
  base_url?: string;
  api_key?: string;
  model: string;
  temperature: number;
  max_tokens?: number;
  enabled: boolean;
  extra_json?: Record<string, unknown>;
}

interface RuntimeConfig {
  key: string;
  value_json: Record<string, unknown>;
}

function ConfigSection() {
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [runtime, setRuntime] = useState<RuntimeConfig[]>([]);
  const [saving, setSaving] = useState<string | null>(null);

  const load = async () => {
    const [modelRes, runtimeRes] = await Promise.all([
      authFetchJson('/model-configs'),
      authFetchJson('/runtime-configs'),
    ]);
    setModels(modelRes);
    setRuntime(runtimeRes);
  };

  useEffect(() => {
    load().catch(console.error);
  }, []);

  const updateModel = (purpose: string, patch: Partial<ModelConfig>) => {
    setModels((prev) => prev.map((item) => item.purpose === purpose ? { ...item, ...patch } : item));
  };

  const saveModel = async (model: ModelConfig) => {
    setSaving(model.purpose);
    try {
      await authFetchJson(`/model-configs/${model.purpose}`, {
        method: 'PUT',
        body: JSON.stringify(model),
      });
    } finally {
      setSaving(null);
    }
  };

  const chatConfig = runtime.find((item) => item.key === 'chat');
  const chatValue = chatConfig?.value_json || {};

  const saveChatRuntime = async (value: Record<string, unknown>) => {
    setSaving('chat');
    try {
      const saved = await authFetchJson('/runtime-configs/chat', {
        method: 'PUT',
        body: JSON.stringify({ value_json: value }),
      });
      setRuntime((prev) => prev.map((item) => item.key === 'chat' ? saved : item));
    } finally {
      setSaving(null);
    }
  };

  return (
    <section className="section">
      <div className="section-header">Model & Runtime Config</div>
      <div className="config-grid">
        {models
          .filter((model) => ['intent_recognition', 'tool_enrichment', 'response_generation'].includes(model.purpose))
          .map((model) => (
            <div className="config-card" key={model.purpose}>
              <div className="config-title">{model.purpose}</div>
              <input
                className="config-input"
                value={model.model}
                onChange={(event) => updateModel(model.purpose, { model: event.target.value })}
                placeholder="model"
              />
              <input
                className="config-input"
                value={model.base_url || ''}
                onChange={(event) => updateModel(model.purpose, { base_url: event.target.value })}
                placeholder="base url"
              />
              <input
                className="config-input"
                type="password"
                value={model.api_key || ''}
                onChange={(event) => updateModel(model.purpose, { api_key: event.target.value })}
                placeholder="api key"
              />
              <label className="config-label">
                Temperature
                <input
                  className="config-input"
                  type="number"
                  min="0"
                  max="2"
                  step="0.1"
                  value={model.temperature}
                  onChange={(event) => updateModel(model.purpose, { temperature: Number(event.target.value) })}
                />
              </label>
              <button className="submit-btn compact" onClick={() => saveModel(model)} disabled={saving === model.purpose}>
                {saving === model.purpose ? 'Saving...' : 'Save'}
              </button>
            </div>
          ))}
        <div className="config-card">
          <div className="config-title">chat runtime</div>
          <label className="config-label">
            Layer 1 max iterations
            <input
              className="config-input"
              type="number"
              min="1"
              max="8"
              value={Number(chatValue.layer1_max_iterations || 3)}
              onChange={(event) => {
                const value = { ...chatValue, layer1_max_iterations: Number(event.target.value) };
                setRuntime((prev) => prev.map((item) => item.key === 'chat' ? { ...item, value_json: value } : item));
              }}
            />
          </label>
          <label className="config-label">
            History max chars
            <input
              className="config-input"
              type="number"
              min="1000"
              step="1000"
              value={Number(chatValue.history_max_chars || 12000)}
              onChange={(event) => {
                const value = { ...chatValue, history_max_chars: Number(event.target.value) };
                setRuntime((prev) => prev.map((item) => item.key === 'chat' ? { ...item, value_json: value } : item));
              }}
            />
          </label>
          <button className="submit-btn compact" onClick={() => saveChatRuntime(chatValue)} disabled={saving === 'chat'}>
            {saving === 'chat' ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </section>
  );
}

export default ConfigSection;
