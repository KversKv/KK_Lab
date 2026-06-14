import React, { useState } from 'react';
import { LogPanel, AutoBaudSettings, SerialConfig } from '../types';
import { SUPPORTED_BAUDRATES, MOCK_DEVICES, isWebSerialSupported } from '../utils/serialHelper';
import { Sliders, RefreshCw, Cpu, Activity, Eye, FileText, Send, EyeOff } from 'lucide-react';

interface SidebarProps {
  panel: LogPanel;
  updatePanelSettings: (settings: Partial<LogPanel>) => void;
  autoBaud: AutoBaudSettings;
  updateAutoBaud: (settings: Partial<AutoBaudSettings>) => void;
  onRefreshPorts: () => void;
  availablePorts: string[];
}

export function Sidebar({
  panel,
  updatePanelSettings,
  autoBaud,
  updateAutoBaud,
  onRefreshPorts,
  availablePorts
}: SidebarProps) {
  const [customBaud, setCustomBaud] = useState(false);

  // MiniSlideToggle component rewritten in React
  const renderSlideToggle = (
    label: string,
    value: 'ASCII' | 'HEX',
    onChange: (val: 'ASCII' | 'HEX') => void
  ) => {
    return (
      <div className="flex items-center justify-between py-1.5" id={`toggle-${label.toLowerCase()}`}>
        <span className="text-xs font-medium text-gray-500">{label}</span>
        <div 
          onClick={() => onChange(value === 'ASCII' ? 'HEX' : 'ASCII')}
          className="relative inline-flex h-6 w-24 flex-shrink-0 cursor-pointer rounded-md border border-gray-200 bg-gray-100 p-0.5 transition-colors duration-200 ease-in-out hover:border-gray-300"
          id={`slider-${label.toLowerCase()}`}
        >
          {/* Active Knob slide animation */}
          <div
            className={`absolute top-0.5 bottom-0.5 w-[46px] rounded-sm bg-[#007AFF] transition-all duration-200 ease-out ${
              value === 'HEX' ? 'translate-x-[45px]' : 'translate-x-[1px]'
            }`}
          />
          <div className="flex w-full items-center justify-between text-[10px] font-bold z-10 select-none">
            <span className={`w-1/2 text-center transition-colors duration-150 ${value === 'ASCII' ? 'text-white' : 'text-gray-400'}`}>ASCII</span>
            <span className={`w-1/2 text-center transition-colors duration-150 ${value === 'HEX' ? 'text-white' : 'text-gray-400'}`}>HEX</span>
          </div>
        </div>
      </div>
    );
  };

  const handlePortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    updatePanelSettings({ port: e.target.value });
  };

  const handleBaudrateChange = (e: React.ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    const val = Number(e.target.value);
    if (!isNaN(val)) {
      updatePanelSettings({ baudrate: val });
    }
  };

  return (
    <aside className="w-[300px] bg-slate-50/50 dark:bg-[#020617]/50 backdrop-blur-md border-r border-slate-200 dark:border-slate-800/80 flex flex-col h-full overflow-y-auto select-none" id="serial-config-sidebar">
      {/* Scrollable Container wrapper to keep scrollbars thin */}
      <div className="p-5 space-y-5 flex-1 pr-3 scrollbar-thin">
        
        {/* SECTION 1: Serial Config Card */}
        <div className="bg-white/60 dark:bg-slate-900/40 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 space-y-4 backdrop-blur-sm" id="card-config-serial">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800/60" id="header-config">
            <Sliders size={14} className="text-blue-500" />
            <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 tracking-wider uppercase">Serial Config</h3>
          </div>

          <div className="space-y-3" id="inputs-grid-serial">
            {/* Port dropdown selector */}
            <div className="space-y-1" id="field-port">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Port</label>
                <button 
                  onClick={onRefreshPorts}
                  title="Scan hardware serial ports"
                  className="p-1 rounded-md text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  id="btn-scan"
                >
                  <RefreshCw size={11} className={panel.isConnected ? "animate-spin" : ""} />
                </button>
              </div>
              <select
                value={panel.port}
                onChange={handlePortChange}
                disabled={panel.isConnected}
                className="w-full text-xs font-medium bg-slate-50 dark:bg-[#020617] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 rounded-lg py-2.5 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50"
                id="select-port"
              >
                <option value="">-- Select Port --</option>
                {/* Physical ports */}
                {availablePorts.map((p, idx) => (
                  <option key={`p-${idx}`} value={p}>{p}</option>
                ))}
                {/* Mock items */}
                {MOCK_DEVICES.map((dev, idx) => (
                  <option key={`m-${idx}`} value={dev.port}>{dev.port} - {dev.name}</option>
                ))}
              </select>
            </div>

            {/* Baud Rate selector */}
            <div className="space-y-1" id="field-baud">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Baud Rate (bps)</label>
                <button
                  onClick={() => setCustomBaud(!customBaud)}
                  className="text-[10px] font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline"
                  id="btn-baud-mode"
                >
                  {customBaud ? "Select Preset" : "Custom"}
                </button>
              </div>

              {customBaud ? (
                <input
                  type="number"
                  value={panel.baudrate}
                  onChange={handleBaudrateChange}
                  disabled={panel.isConnected && !panel.isMock}
                  className="w-full text-xs font-medium bg-slate-50 dark:bg-[#020617] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50 font-mono"
                  id="input-custom-baud"
                  placeholder="e.g. 115200"
                />
              ) : (
                <select
                  value={panel.baudrate}
                  onChange={handleBaudrateChange}
                  disabled={panel.isConnected && !panel.isMock}
                  className="w-full text-xs font-medium bg-slate-50 dark:bg-[#020617] text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-slate-800 rounded-lg py-2.5 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all disabled:opacity-50"
                  id="select-baud"
                >
                  {SUPPORTED_BAUDRATES.map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Auto Baudrate Detection */}
            <div className="flex items-center justify-between pt-3 mt-1 border-t border-slate-100 dark:border-slate-800/60" id="field-autodetect">
              <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Auto-Detect</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoBaud.enabled}
                  onChange={(e) => updateAutoBaud({ enabled: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-7 h-4 bg-slate-200 dark:bg-slate-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            {/* Advanced configurations collapsible or toggled inside list */}
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100 dark:border-slate-800/60 text-[11px]" id="collapsed-advanced-serial">
              <div className="space-y-1.5">
                <span className="text-slate-500 dark:text-slate-500 font-bold">Data bits</span>
                <select
                  value={panel.databits}
                  onChange={(e) => updatePanelSettings({ databits: Number(e.target.value) })}
                  disabled={panel.isConnected}
                  className="w-full bg-slate-50 dark:bg-[#020617] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-md py-1.5 px-2 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                >
                  <option value={8}>8</option>
                  <option value={7}>7</option>
                  <option value={6}>6</option>
                  <option value={5}>5</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <span className="text-slate-500 dark:text-slate-500 font-bold">Stop bits</span>
                <select
                  value={panel.stopbits}
                  onChange={(e) => updatePanelSettings({ stopbits: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-slate-50 dark:bg-[#020617] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-md py-1.5 px-2 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                >
                  <option value="1">1</option>
                  <option value="1.5">1.5</option>
                  <option value="2">2</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <span className="text-slate-500 dark:text-slate-500 font-bold">Parity</span>
                <select
                  value={panel.parity}
                  onChange={(e) => updatePanelSettings({ parity: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-slate-50 dark:bg-[#020617] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-md py-1.5 px-2 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                >
                  <option value="None">None</option>
                  <option value="Even">Even</option>
                  <option value="Odd">Odd</option>
                  <option value="Mark">Mark</option>
                  <option value="Space">Space</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <span className="text-slate-500 dark:text-slate-500 font-bold">Flow Control</span>
                <select
                  value={panel.flowControl}
                  onChange={(e) => updatePanelSettings({ flowControl: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-slate-50 dark:bg-[#020617] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-md py-1.5 px-2 focus:ring-2 focus:ring-blue-500/20 disabled:opacity-50"
                >
                  <option value="None">None</option>
                  <option value="RTS/CTS">RTS/CTS</option>
                  <option value="XON/XOFF">XON/XOFF</option>
                </select>
              </div>
            </div>

          </div>
        </div>

        {/* SECTION 2: RX Settings Card */}
        <div className="bg-white/60 dark:bg-slate-900/40 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 space-y-4 backdrop-blur-sm" id="card-config-rx">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800/60" id="header-rx">
            <Activity size={14} className="text-blue-500" />
            <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 tracking-wider uppercase">RX Config</h3>
          </div>

          <div className="space-y-3 text-xs text-slate-600 dark:text-slate-400" id="inputs-rx">
            {/* ASCII/HEX slides toggle */}
            {renderSlideToggle('Format', panel.rxFormat, (val) => updatePanelSettings({ rxFormat: val }))}

            {/* Auto flush interval spin */}
            <div className="flex items-center justify-between py-1" id="field-flush">
              <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Auto Flush</span>
              <div className="flex items-center gap-2" id="flush-timing-spin">
                <input
                  type="checkbox"
                  checked={panel.autoFlush}
                  onChange={(e) => updatePanelSettings({ autoFlush: e.target.checked })}
                  className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-900 h-4 w-4 focus:ring-blue-500/50 cursor-pointer"
                />
                <input
                  type="number"
                  value={panel.autoFlushMs}
                  onChange={(e) => updatePanelSettings({ autoFlushMs: Math.max(10, Number(e.target.value)) })}
                  disabled={!panel.autoFlush}
                  className="w-16 text-center text-[11px] font-bold bg-slate-50 dark:bg-[#020617] px-2 py-1.5 border border-slate-200 dark:border-slate-800 rounded-md outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200 disabled:opacity-50"
                  title="Flush wait timer (ms)"
                />
                <span className="text-[10px] text-slate-400 font-bold">ms</span>
              </div>
            </div>

            {/* Custom check indicators */}
            <div className="space-y-3 pt-3 mt-1 border-t border-slate-100 dark:border-slate-800/60" id="checkboxes-rx-options">
              <label className="flex items-center gap-3 font-medium cursor-pointer py-1">
                <input
                  type="checkbox"
                  checked={panel.showTime}
                  onChange={(e) => updatePanelSettings({ showTime: e.target.checked })}
                  className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-900 h-4 w-4 focus:ring-blue-500/50"
                />
                <span>Show Time (ms)</span>
              </label>

              <label className="flex items-center gap-3 font-medium cursor-pointer py-1">
                <input
                  type="checkbox"
                  checked={panel.useNtp}
                  onChange={(e) => updatePanelSettings({ useNtp: e.target.checked })}
                  className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-900 h-4 w-4 focus:ring-blue-500/50"
                />
                <span>NTP Calibrated</span>
              </label>

              <div className="flex items-center justify-between pt-1" id="max-lines-display">
                <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Max Scroll Lines</span>
                <input
                  type="number"
                  value={panel.maxLines}
                  onChange={(e) => updatePanelSettings({ maxLines: Math.max(500, Number(e.target.value)) })}
                  className="w-20 text-center text-[11px] font-bold bg-slate-50 dark:bg-[#020617] px-2 py-1.5 border border-slate-200 dark:border-slate-800 rounded-md outline-none focus:ring-2 focus:ring-blue-500/20 text-slate-700 dark:text-slate-200"
                />
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 3: TX Settings Card */}
        <div className="bg-white/60 dark:bg-slate-900/40 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm p-4 space-y-4 backdrop-blur-sm" id="card-config-tx">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-100 dark:border-slate-800/60" id="header-tx">
            <Send size={13} className="text-blue-500" />
            <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 tracking-wider uppercase">TX Config</h3>
          </div>

          <div className="space-y-3 text-xs text-slate-600 dark:text-slate-400" id="inputs-tx">
            {/* ASCII/HEX slide toggle */}
            {renderSlideToggle('Format', panel.txFormat, (val) => updatePanelSettings({ txFormat: val }))}

            {/* Line ending dropdown selector */}
            <div className="flex items-center justify-between py-2 mt-1 border-t border-slate-100 dark:border-slate-800/60" id="field-ending">
              <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">Line Ending</span>
              <select
                value={panel.lineEnding}
                onChange={(e) => updatePanelSettings({ lineEnding: e.target.value })}
                className="w-24 text-[11px] bg-slate-50 dark:bg-[#020617] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800 rounded-md py-1.5 px-2 focus:ring-2 focus:ring-blue-500/20"
                id="select-line-ending"
              >
                <option value="\r\n">\r\n (CRLF)</option>
                <option value="\n">\n (LF)</option>
                <option value="\r">\r (CR)</option>
                <option value="\n\r">\n\r</option>
                <option value="">None</option>
              </select>
            </div>

            {/* Additional parameters */}
            <div className="space-y-3 pt-3 border-t border-slate-100 dark:border-slate-800/60" id="checkboxes-tx-options">
              <label className="flex items-center gap-3 font-medium cursor-pointer py-1">
                <input
                  type="checkbox"
                  checked={panel.showSent}
                  onChange={(e) => updatePanelSettings({ showSent: e.target.checked })}
                  className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-900 h-4 w-4 focus:ring-blue-500/50"
                />
                <span>Show Sent Data</span>
              </label>

              <label className="flex items-center gap-3 font-medium cursor-pointer py-1">
                <input
                  type="checkbox"
                  checked={panel.lineByLine}
                  onChange={(e) => updatePanelSettings({ lineByLine: e.target.checked })}
                  className="rounded text-blue-600 border-slate-300 dark:border-slate-700 dark:border-slate-900 h-4 w-4 focus:ring-blue-500/50"
                />
                <span>Line by Line Send</span>
              </label>
            </div>
          </div>
        </div>

      </div>
    </aside>
  );
}
