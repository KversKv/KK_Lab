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
    <aside className="w-72 bg-[#F5F5F7] border-r border-gray-200 flex flex-col h-full overflow-y-auto select-none" id="serial-config-sidebar">
      {/* Scrollable Container wrapper to keep scrollbars thin */}
      <div className="p-4 space-y-5 flex-1 pr-3 scrollbar-thin">
        
        {/* SECTION 1: Serial Config Card */}
        <div className="bg-white rounded-xl border border-gray-150 p-3.5 shadow-sm space-y-4" id="card-config-serial">
          <div className="flex items-center gap-2 pb-1 border-b border-gray-100" id="header-config">
            <Sliders size={14} className="text-gray-500" />
            <h3 className="text-xs font-bold text-gray-700 tracking-wide uppercase">Serial Config</h3>
          </div>

          <div className="space-y-3" id="inputs-grid-serial">
            {/* Port dropdown selector */}
            <div className="space-y-1" id="field-port">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-medium text-gray-500">Port</label>
                <button 
                  onClick={onRefreshPorts}
                  title="Scan hardware serial ports"
                  className="p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                  id="btn-scan"
                >
                  <RefreshCw size={11} className={panel.isConnected ? "animate-spin" : ""} />
                </button>
              </div>
              <select
                value={panel.port}
                onChange={handlePortChange}
                disabled={panel.isConnected}
                className="w-full text-xs bg-gray-50 text-gray-800 border border-gray-200 hover:border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-[#007AFF] focus:border-[#007AFF] transition-colors"
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
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-medium text-gray-500">Baud Rate (bps)</label>
                <button
                  onClick={() => setCustomBaud(!customBaud)}
                  className="text-[10px] font-semibold text-[#007AFF] hover:underline"
                  id="btn-baud-mode"
                >
                  {customBaud ? "Select Preset" : "Custom Custom"}
                </button>
              </div>

              {customBaud ? (
                <input
                  type="number"
                  value={panel.baudrate}
                  onChange={handleBaudrateChange}
                  disabled={panel.isConnected && !panel.isMock}
                  className="w-full text-xs bg-gray-50 text-gray-800 border border-gray-200 rounded-lg p-2 focus:outline-none focus:ring-1 focus:ring-[#007AFF] focus:border-[#007AFF]"
                  id="input-custom-baud"
                  placeholder="e.g. 115200"
                />
              ) : (
                <select
                  value={panel.baudrate}
                  onChange={handleBaudrateChange}
                  disabled={panel.isConnected && !panel.isMock}
                  className="w-full text-xs bg-gray-50 text-gray-800 border border-gray-200 rounded-lg p-2 focus:outline-none focus:ring-1"
                  id="select-baud"
                >
                  {SUPPORTED_BAUDRATES.map(b => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Auto Baudrate Detection */}
            <div className="flex items-center justify-between pt-1 border-t border-gray-50" id="field-autodetect">
              <span className="text-[11px] font-medium text-gray-500">Auto-Detect Baud</span>
              <input
                type="checkbox"
                checked={autoBaud.enabled}
                onChange={(e) => updateAutoBaud({ enabled: e.target.checked })}
                className="h-3.5 w-3.5 rounded text-[#007AFF] border-gray-300 focus:ring-[#007AFF] cursor-pointer"
                id="checkbox-auto-baud"
              />
            </div>

            {/* Advanced configurations collapsible or toggled inside list */}
            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-gray-100 text-[11px]" id="collapsed-advanced-serial">
              <div className="space-y-1">
                <span className="text-gray-400 font-medium">Data bits</span>
                <select
                  value={panel.databits}
                  onChange={(e) => updatePanelSettings({ databits: Number(e.target.value) })}
                  disabled={panel.isConnected}
                  className="w-full bg-gray-50 text-gray-700 border border-gray-200 rounded-md p-1 focus:ring-1"
                >
                  <option value={8}>8</option>
                  <option value={7}>7</option>
                  <option value={6}>6</option>
                  <option value={5}>5</option>
                </select>
              </div>

              <div className="space-y-1">
                <span className="text-gray-400 font-medium">Stop bits</span>
                <select
                  value={panel.stopbits}
                  onChange={(e) => updatePanelSettings({ stopbits: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-gray-50 text-gray-700 border border-gray-200 rounded-md p-1 focus:ring-1"
                >
                  <option value="1">1</option>
                  <option value="1.5">1.5</option>
                  <option value="2">2</option>
                </select>
              </div>

              <div className="space-y-1">
                <span className="text-gray-400 font-medium">Parity</span>
                <select
                  value={panel.parity}
                  onChange={(e) => updatePanelSettings({ parity: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-gray-50 text-gray-700 border border-gray-200 rounded-md p-1 focus:ring-1"
                >
                  <option value="None">None</option>
                  <option value="Even">Even</option>
                  <option value="Odd">Odd</option>
                  <option value="Mark">Mark</option>
                  <option value="Space">Space</option>
                </select>
              </div>

              <div className="space-y-1">
                <span className="text-gray-400 font-medium">Flow Control</span>
                <select
                  value={panel.flowControl}
                  onChange={(e) => updatePanelSettings({ flowControl: e.target.value as any })}
                  disabled={panel.isConnected}
                  className="w-full bg-gray-50 text-gray-700 border border-gray-200 rounded-md p-1"
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
        <div className="bg-white rounded-xl border border-gray-150 p-3.5 shadow-sm space-y-3.5" id="card-config-rx">
          <div className="flex items-center gap-2 pb-1 border-b border-gray-100" id="header-rx">
            <Activity size={14} className="text-gray-500" />
            <h3 className="text-xs font-bold text-gray-700 tracking-wide uppercase">RX Config</h3>
          </div>

          <div className="space-y-2.5 text-xs text-gray-600" id="inputs-rx">
            {/* ASCII/HEX slides toggle */}
            {renderSlideToggle('Format', panel.rxFormat, (val) => updatePanelSettings({ rxFormat: val }))}

            {/* Auto flush interval spin */}
            <div className="flex items-center justify-between py-1.5" id="field-flush">
              <span className="text-xs font-medium text-gray-500">Auto Flush</span>
              <div className="flex items-center gap-1.5" id="flush-timing-spin">
                <input
                  type="checkbox"
                  checked={panel.autoFlush}
                  onChange={(e) => updatePanelSettings({ autoFlush: e.target.checked })}
                  className="rounded text-[#007AFF] border-gray-200 cursor-pointer h-3.5 w-3.5"
                />
                <input
                  type="number"
                  value={panel.autoFlushMs}
                  onChange={(e) => updatePanelSettings({ autoFlushMs: Math.max(10, Number(e.target.value)) })}
                  disabled={!panel.autoFlush}
                  className="w-16 text-center text-[11px] font-bold bg-gray-50 p-1 border border-gray-200 rounded-md outline-none focus:ring-1 focus:ring-[#007AFF]"
                  title="Flush wait timer (ms)"
                />
                <span className="text-[10px] text-gray-400 font-semibold">ms</span>
              </div>
            </div>

            {/* Custom check indicators */}
            <div className="space-y-2 pt-2 border-t border-gray-55" id="checkboxes-rx-options">
              <label className="flex items-center gap-2.5 font-medium cursor-pointer py-0.5">
                <input
                  type="checkbox"
                  checked={panel.showTime}
                  onChange={(e) => updatePanelSettings({ showTime: e.target.checked })}
                  className="rounded text-[#007AFF] border-gray-200 h-3.5 w-3.5"
                />
                <span>Show Time (ms)</span>
              </label>

              <label className="flex items-center gap-2.5 font-medium cursor-pointer py-0.5">
                <input
                  type="checkbox"
                  checked={panel.useNtp}
                  onChange={(e) => updatePanelSettings({ useNtp: e.target.checked })}
                  className="rounded text-[#007AFF] border-gray-200 h-3.5 w-3.5"
                />
                <span>NTP Calibrated</span>
              </label>

              <div className="flex items-center justify-between py-0.5" id="max-lines-display">
                <span className="font-medium text-gray-500">Max Scroll Lines</span>
                <input
                  type="number"
                  value={panel.maxLines}
                  onChange={(e) => updatePanelSettings({ maxLines: Math.max(500, Number(e.target.value)) })}
                  className="w-20 text-center text-[11px] bg-gray-50 p-1 border border-gray-205 rounded-md focus:ring-1 focus:ring-[#007AFF]"
                />
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 3: TX Settings Card */}
        <div className="bg-white rounded-xl border border-gray-150 p-3.5 shadow-sm space-y-3.5" id="card-config-tx">
          <div className="flex items-center gap-2 pb-1 border-b border-gray-100" id="header-tx">
            <Send size={13} className="text-gray-500" />
            <h3 className="text-xs font-bold text-gray-700 tracking-wide uppercase">TX Config</h3>
          </div>

          <div className="space-y-2.5 text-xs text-gray-600" id="inputs-tx">
            {/* ASCII/HEX slide toggle */}
            {renderSlideToggle('Format', panel.txFormat, (val) => updatePanelSettings({ txFormat: val }))}

            {/* Line ending dropdown selector */}
            <div className="flex items-center justify-between py-1 border-t border-gray-50" id="field-ending">
              <span className="text-xs font-medium text-gray-500">Line Ending</span>
              <select
                value={panel.lineEnding}
                onChange={(e) => updatePanelSettings({ lineEnding: e.target.value })}
                className="w-24 text-[11px] bg-gray-50 text-gray-700 border border-gray-200 rounded-md p-1 focus:ring-1"
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
            <div className="space-y-2 pt-2 border-t border-gray-55" id="checkboxes-tx-options">
              <label className="flex items-center gap-2.5 font-medium cursor-pointer py-0.5">
                <input
                  type="checkbox"
                  checked={panel.showSent}
                  onChange={(e) => updatePanelSettings({ showSent: e.target.checked })}
                  className="rounded text-[#007AFF] border-gray-200 h-3.5 w-3.5"
                />
                <span>Show Sent Data</span>
              </label>

              <label className="flex items-center gap-2.5 font-medium cursor-pointer py-0.5">
                <input
                  type="checkbox"
                  checked={panel.lineByLine}
                  onChange={(e) => updatePanelSettings({ lineByLine: e.target.checked })}
                  className="rounded text-[#007AFF] border-gray-200 h-3.5 w-3.5"
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
