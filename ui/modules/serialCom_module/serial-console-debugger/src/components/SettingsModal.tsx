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
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50 select-none animate-fade-in" id="settings-frame-overlay">
      <div className="bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl rounded-2xl border border-slate-200/80 dark:border-slate-800/80 w-full max-w-2xl h-[520px] flex flex-col shadow-[0_8px_32px_rgba(0,0,0,0.1)] dark:shadow-none overflow-hidden text-slate-800 dark:text-slate-100 animate-scale-up" id="settings-dialog-card">
        
        {/* Header Title */}
        <div className="px-5 py-4 border-b border-slate-200/80 dark:border-slate-800/80 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50" id="dialog-header">
          <div className="flex items-center gap-2">
            <Settings size={18} className="text-blue-600 dark:text-blue-500" />
            <h2 className="text-sm font-bold text-slate-800 dark:text-slate-100 tracking-wide uppercase">Serial Console Settings</h2>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 bg-transparent hover:bg-rose-50 dark:hover:bg-rose-500/10 h-8 w-8 rounded-full flex items-center justify-center transition-colors font-bold cursor-pointer"
          >
            &times;
          </button>
        </div>

        {/* Content Tabs Wrapper */}
        <div className="flex-1 flex overflow-hidden" id="dialog-split-content">
          {/* Left Navigation Menu list */}
          <nav className="w-48 bg-slate-50/50 dark:bg-[#09090b] border-r border-slate-200/80 dark:border-slate-800/80 p-3 space-y-1 text-xs font-semibold" id="dialog-tabs-navigation">
            <button
              onClick={() => setActiveTab('serial')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer font-bold ${
                activeTab === 'serial' ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-800/50' : 'border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Sliders size={13} />
              <span>Diagnostic Ports</span>
            </button>

            <button
              onClick={() => setActiveTab('rx_tx')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer font-bold ${
                activeTab === 'rx_tx' ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-800/50' : 'border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <ToggleLeft size={13} />
              <span>Buffers & Encodes</span>
            </button>

            <button
              onClick={() => setActiveTab('autobaud')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer font-bold ${
                activeTab === 'autobaud' ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-800/50' : 'border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Play size={13} />
              <span>Auto Baud Detect</span>
            </button>

            <button
              onClick={() => setActiveTab('about')}
              className={`flex items-center gap-2 w-full p-2.5 rounded-lg text-left transition-colors cursor-pointer font-bold ${
                activeTab === 'about' ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-sm border border-slate-200/80 dark:border-slate-800/50' : 'border border-transparent text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:text-slate-800 dark:hover:text-slate-200'
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
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide text-[10px]">Data Flow Settings</h4>
                  <p className="text-slate-400 leading-normal">Customize stopbits, parity alignment, and buffer limitations for connection speeds.</p>
                </div>

                <div className="grid grid-cols-2 gap-3" id="form-grid-serial">
                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Stop Bits Code</span>
                    <select
                      value={panel.stopbits}
                      onChange={(e) => updatePanelSettings({ stopbits: e.target.value as any })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="1">1 Bit</option>
                      <option value="1.5">1.5 Bit</option>
                      <option value="2">2 Bits</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Parity Protocol</span>
                    <select
                      value={panel.parity}
                      onChange={(e) => updatePanelSettings({ parity: e.target.value as any })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2 outline-none focus:ring-1 focus:ring-blue-500"
                    >
                      <option value="None">None</option>
                      <option value="Even">Even (Odd Alignment)</option>
                      <option value="Odd">Odd</option>
                      <option value="Mark">Mark</option>
                      <option value="Space">Space</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Maximum terminal buffer logs</span>
                    <input
                      type="number"
                      value={panel.maxLines}
                      onChange={(e) => updatePanelSettings({ maxLines: Math.round(Math.max(500, Number(e.target.value))) })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-1.5 font-bold text-center outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: RX_TX formats */}
            {activeTab === 'rx_tx' && (
              <div className="space-y-4" id="tab-rx-tx">
                <div className="space-y-1">
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide text-[10px]">Buffers and Encoding</h4>
                  <p className="text-slate-400">Manage HEX display spacing and formatting when writing to log streams.</p>
                </div>

                <div className="space-y-3 pt-2 text-slate-600 dark:text-slate-400 font-medium" id="form-rx-tx">
                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-slate-50 dark:border-slate-800/50">
                    <input
                      type="checkbox"
                      checked={panel.showTime}
                      onChange={(e) => updatePanelSettings({ showTime: e.target.checked })}
                      className="rounded text-blue-600 border-slate-200 dark:border-slate-700 dark:border-slate-800 h-4 w-4 focus:ring-blue-500"
                    />
                    <span>Append millisecond timestamps automatically in terminal rows</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-slate-50 dark:border-slate-800/50">
                    <input
                      type="checkbox"
                      checked={panel.useNtp}
                      onChange={(e) => updatePanelSettings({ useNtp: e.target.checked })}
                      className="rounded text-blue-600 border-slate-200 dark:border-slate-700 dark:border-slate-800 h-4 w-4 focus:ring-blue-500"
                    />
                    <span>Acquire Atomic NTP latency offsets upon connection start</span>
                  </label>

                  <label className="flex items-center gap-2 cursor-pointer py-1 border-b border-slate-50 dark:border-slate-800/50">
                    <input
                      type="checkbox"
                      checked={panel.showSent}
                      onChange={(e) => updatePanelSettings({ showSent: e.target.checked })}
                      className="rounded text-blue-600 border-slate-200 dark:border-slate-700 dark:border-slate-800 h-4 w-4 focus:ring-blue-500"
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
                  <h4 className="font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide text-[10px]">Auto-Baudrate Calibration Settings</h4>
                  <p className="text-slate-400 leading-normal">Tune the algorithmic thresholds that evaluate incoming stream content to auto-select speed metrics.</p>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2" id="form-grid-autobaud">
                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Baud locking score threshold</span>
                    <input
                      type="number"
                      value={autoBaud.lockThreshold}
                      onChange={(e) => updateAutoBaud({ lockThreshold: Math.min(100, Math.max(10, Number(e.target.value))) })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-2 rounded-lg text-center outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Scan timeout spacing (ms)</span>
                    <input
                      type="number"
                      value={autoBaud.monitorWindowMaxTimeMs}
                      onChange={(e) => updateAutoBaud({ monitorWindowMaxTimeMs: Math.max(50, Number(e.target.value)) })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-2 rounded-lg text-center outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Suspect window threshold count</span>
                    <input
                      type="number"
                      value={autoBaud.badWindowsToSuspect}
                      onChange={(e) => updateAutoBaud({ badWindowsToSuspect: Math.max(1, Number(e.target.value)) })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-2 rounded-lg text-center outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <span className="font-bold text-slate-500 dark:text-slate-400">Cooldown timeout register (ms)</span>
                    <input
                      type="number"
                      value={autoBaud.switchCooldownMs}
                      onChange={(e) => updateAutoBaud({ switchCooldownMs: Math.max(100, Number(e.target.value)) })}
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-2 rounded-lg text-center outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: About Software info */}
            {activeTab === 'about' && (
              <div className="space-y-4" id="tab-about">
                <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-2 select-text" id="card-about-detail">
                  <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm">KK Serial Terminal Console</h3>
                  <p className="text-slate-400 font-semibold text-[10px]">Web Version 2.4.0 (Engine v2.0)</p>
                  <p className="text-slate-500 dark:text-slate-400 leading-relaxed font-medium">
                    A premium web-native Serial Debugging platform built in React & Tailwind CSS. Inspired by professional instrumentation tools, featuring Web Serial API, multiple split windows, automated test script routines, and offline mock-diagnostic playgrounds.
                  </p>
                </div>

                <div className="p-3 bg-red-50 dark:bg-red-950/30 border border-red-100 dark:border-red-900/50 rounded-lg space-y-2" id="about-recovery-panel">
                  <h4 className="text-[11px] font-bold text-red-700 dark:text-red-500 uppercase tracking-wider">System Recovery Options</h4>
                  <p className="text-red-600 dark:text-red-400/80 font-medium">Resetting deletes terminal history, buffer limitations, and settings tab values, returning them to factory standard records. Your custom Quick Commands and scripts will remain intact.</p>
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
        <div className="px-5 py-3 border-t border-slate-200/80 dark:border-slate-800/80 flex justify-end gap-2 bg-slate-50/50 dark:bg-slate-900/50" id="dialog-footer">
          <button 
            onClick={onClose}
            className="px-5 py-2 border border-slate-200/80 dark:border-slate-700/80 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 font-bold rounded-lg text-xs cursor-pointer shadow-sm transition-colors"
          >
            Close Settings
          </button>
        </div>

      </div>
    </div>
  );
}
