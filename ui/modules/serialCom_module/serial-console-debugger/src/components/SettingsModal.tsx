import React, { useState } from 'react';
import { AutoBaudSettings, LogPanel } from '../types';
import { Settings, Info, Sliders, Play, FileText, ToggleLeft, RefreshCcw } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  panel: LogPanel;
  updatePanelSettings: (settings: Partial<LogPanel>) => void;
  autoBaud: AutoBaudSettings;
  updateAutoBaud: (settings: Partial<AutoBaudSettings>) => void;
  onResetDefaults: () => void;
}

export function SettingsModal({
  isOpen,
  onClose,
  panel,
  updatePanelSettings,
  autoBaud,
  updateAutoBaud,
  onResetDefaults
}: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'serial' | 'rx_tx' | 'autobaud' | 'about'>('serial');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50 select-none animate-fade-in" id="settings-frame-overlay">
      <div className="bg-white rounded-xl border border-gray-200 w-full max-w-2xl h-[520px] flex flex-col shadow-2xl overflow-hidden text-slate-800 animate-scale-up" id="settings-dialog-card">
        
        {/* Header Title */}
        <div className="px-5 py-4 border-b border-gray-150 flex items-center justify-between bg-gray-50" id="dialog-header">
          <div className="flex items-center gap-2">
            <Settings size={16} className="text-[#007AFF]" />
            <h2 className="text-sm font-bold text-slate-800 tracking-wide uppercase">Serial Console Settings</h2>
          </div>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-gray-700 text-lg font-bold"
          >
            &times;
          </button>
        </div>

        {/* Content Tabs Wrapper */}
        <div className="flex-1 flex overflow-hidden" id="dialog-split-content">
          {/* Left Navigation Menu list */}
          <nav className="w-48 bg-gray-50 border-r border-gray-150 p-2.5 space-y-1 text-xs font-semibold" id="dialog-tabs-navigation">
            <button
              onClick={() => setActiveTab('serial')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                activeTab === 'serial' ? 'bg-[#E8F2FF] text-[#007AFF]' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
              }`}
            >
              <Sliders size={13} />
              <span>Diagnostic Ports</span>
            </button>

            <button
              onClick={() => setActiveTab('rx_tx')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                activeTab === 'rx_tx' ? 'bg-[#E8F2FF] text-[#007AFF]' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
              }`}
            >
              <ToggleLeft size={13} />
              <span>Buffers & Encodes</span>
            </button>

            <button
              onClick={() => setActiveTab('autobaud')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                activeTab === 'autobaud' ? 'bg-[#E8F2FF] text-[#007AFF]' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
              }`}
            >
              <Play size={13} />
              <span>Auto Baud Detect</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                activeTab === 'about' ? 'bg-[#E8F2FF] text-[#007AFF]' : 'text-gray-500 hover:bg-gray-100 hover:text-gray-800'
              }`}
            >
              <Info size={13} />
              <span>About Console</span>
            </button>
          </nav>

          {/* Right Panel fields depending on activeTab */}
          <div className="flex-1 p-5 overflow-y-auto text-xs space-y-4" id="dialog-settings-parameters">
            
            {/* TAB 1: Serial Ports properties */}
            {activeTab === 'serial' && (
              <div className="space-y-4" id="tab-serial">
                <div className="space-y-1.5">
                  <h4 className="font-bold text-gray-700 uppercase tracking-wide text-[10px]">Data Flow Settings</h4>
                  <p className="text-gray-400 leading-normal">Customize stopbits, parity alignment, and buffer limitations for connection speeds.</p>
                </div>

                <div className="grid grid-cols-2 gap-3" id="form-grid-serial">
                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Stop Bits Code</span>
                    <select
                      value={panel.stopbits}
                      onChange={(e) => updatePanelSettings({ stopbits: e.target.value as any })}
                      className="w-full bg-gray-55 border border-gray-200 rounded-lg p-2"
                    >
                      <option value="1">1 Bit</option>
                      <option value="1.5">1.5 Bit</option>
                      <option value="2">2 Bits</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Parity Protocol</span>
                    <select
                      value={panel.parity}
                      onChange={(e) => updatePanelSettings({ parity: e.target.value as any })}
                      className="w-full bg-gray-55 border border-gray-200 rounded-lg p-2"
                    >
                      <option value="None">None</option>
                      <option value="Even">Even (Odd Alignment)</option>
                      <option value="Odd">Odd</option>
                      <option value="Mark">Mark</option>
                      <option value="Space">Space</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Maximum terminal buffer logs</span>
                    <input
                      type="number"
                      value={panel.maxLines}
                      onChange={(e) => updatePanelSettings({ maxLines: Math.round(Math.max(500, Number(e.target.value))) })}
                      className="w-full bg-gray-55 border border-gray-200 rounded-lg p-1.5 font-bold text-center"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: RX_TX formats */}
            {activeTab === 'rx_tx' && (
              <div className="space-y-4" id="tab-rx-tx">
                <div className="space-y-1">
                  <h4 className="font-bold text-gray-700 uppercase tracking-wide text-[10px]">Buffers and Encoding</h4>
                  <p className="text-gray-400">Manage HEX display spacing and formatting when writing to log streams.</p>
                </div>

                <div className="space-y-3 pt-2 text-gray-600 font-medium" id="form-rx-tx">
                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-gray-50">
                    <input
                      type="checkbox"
                      checked={panel.showTime}
                      onChange={(e) => updatePanelSettings({ showTime: e.target.checked })}
                      className="rounded text-[#007AFF] border-gray-200 h-4 w-4"
                    />
                    <span>Append millisecond timestamps automatically in terminal rows</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-gray-50">
                    <input
                      type="checkbox"
                      checked={panel.useNtp}
                      onChange={(e) => updatePanelSettings({ useNtp: e.target.checked })}
                      className="rounded text-[#007AFF] border-gray-200 h-4 w-4"
                    />
                    <span>Acquire Atomic NTP latency offsets upon connection start</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-gray-50">
                    <input
                      type="checkbox"
                      checked={panel.showSent}
                      onChange={(e) => updatePanelSettings({ showSent: e.target.checked })}
                      className="rounded text-[#007AFF] border-gray-200 h-4 w-4"
                    />
                    <span>Print TX (sent data feedback) inside active log dashboards</span>
                  </label>
                </div>
              </div>
            )}

            {/* TAB 3: AutoBaudrate setup */}
            {activeTab === 'autobaud' && (
              <div className="space-y-4 text-xs" id="tab-autobaud">
                <div className="space-y-1">
                  <h4 className="font-bold text-gray-700 uppercase tracking-wide text-[10px]">Auto-Baudrate Calibration Settings</h4>
                  <p className="text-gray-400 leading-normal">Tune the algorithmic thresholds that evaluate incoming stream content to auto-select speed metrics.</p>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2" id="form-grid-autobaud">
                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Baud locking score threshold</span>
                    <input
                      type="number"
                      value={autoBaud.lockThreshold}
                      onChange={(e) => updateAutoBaud({ lockThreshold: Math.min(100, Math.max(10, Number(e.target.value))) })}
                      className="w-full bg-gray-55 border border-gray-200 p-2 rounded-lg text-center"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Scan timeout spacing (ms)</span>
                    <input
                      type="number"
                      value={autoBaud.monitorWindowMaxTimeMs}
                      onChange={(e) => updateAutoBaud({ monitorWindowMaxTimeMs: Math.max(50, Number(e.target.value)) })}
                      className="w-full bg-gray-55 border border-gray-200 p-2 rounded-lg text-center"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Suspect window threshold count</span>
                    <input
                      type="number"
                      value={autoBaud.badWindowsToSuspect}
                      onChange={(e) => updateAutoBaud({ badWindowsToSuspect: Math.max(1, Number(e.target.value)) })}
                      className="w-full bg-gray-55 border border-gray-200 p-2 rounded-lg text-center"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-gray-500">Cooldown timeout register (ms)</span>
                    <input
                      type="number"
                      value={autoBaud.switchCooldownMs}
                      onChange={(e) => updateAutoBaud({ switchCooldownMs: Math.max(100, Number(e.target.value)) })}
                      className="w-full bg-gray-55 border border-gray-200 p-2 rounded-lg text-center"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: About Software info */}
            {activeTab === 'about' && (
              <div className="space-y-4" id="tab-about">
                <div className="bg-gray-50 border border-gray-150 rounded-xl p-4 space-y-2 select-text" id="card-about-detail">
                  <h3 className="font-bold text-slate-800 dark:text-zinc-100 text-sm">KK Serial Terminal Console</h3>
                  <p className="text-gray-400 font-semibold text-[10px]">Web Version 2.4.0 (Engine v2.0)</p>
                  <p className="text-gray-500 leading-relaxed font-medium">
                    A premium web-native Serial Debugging platform built in React & Tailwind CSS. Inspired by professional instrumentation tools, featuring Web Serial API, multiple split windows, automated test script routines, and offline mock-diagnostic playgrounds.
                  </p>
                </div>

                <div className="p-3 bg-red-50 border border-red-100 rounded-lg space-y-2" id="about-recovery-panel">
                  <h4 className="text-[11px] font-bold text-red-700 uppercase tracking-wider">System Recovery Options</h4>
                  <p className="text-red-600 font-medium">Resetting deletes terminal history, buffer limitations, and settings tab values, returning them to factory standard records. Your custom Quick Commands and scripts will remain intact.</p>
                  <button
                    onClick={() => {
                        if (confirm("Restore factory layouts and interface metrics?")) {
                          onResetDefaults();
                          onClose();
                        }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white font-bold rounded-lg hover:bg-red-700 transition-colors shadow-sm cursor-pointer"
                  >
                    <RefreshCcw size={12} />
                    <span>Reset Settings and Layout</span>
                  </button>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Footer actions */}
        <div className="px-5 py-3.5 border-t border-gray-150 flex justify-end gap-2 bg-gray-50" id="dialog-footer">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-gray-200 bg-white hover:bg-gray-50 text-gray-500 font-bold rounded-lg text-xs cursor-pointer"
          >
            Close Settings
          </button>
        </div>

      </div>
    </div>
  );
}
