import React from 'react';
import { LogPanel } from '../types';
import { 
  Play, Pause, Square, RotateCw, Plus, Minus, Columns, Settings, Sliders, Sun, Moon 
} from 'lucide-react';

interface ToolbarProps {
  panel: LogPanel;
  onToggleConnect: () => void;
  onPauseToggle: () => void;
  onStop: () => void;
  sidebarVisible: boolean;
  onToggleSidebar: () => void;
  onAddLogPanel: () => void;
  onRemoveLogPanel: () => void;
  totalPanels: number;
  onOpenSettingsModal: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
}

export function Toolbar({
  panel,
  onToggleConnect,
  onPauseToggle,
  onStop,
  sidebarVisible,
  onToggleSidebar,
  onAddLogPanel,
  onRemoveLogPanel,
  totalPanels,
  onOpenSettingsModal,
  isDark,
  onToggleTheme
}: ToolbarProps) {
  
  return (
    <header className="h-14 bg-white/80 dark:bg-[#020617]/80 backdrop-blur-xl border-b border-slate-200 dark:border-slate-800/80 px-4 flex items-center justify-between select-none" id="serial-top-toolbar">
      {/* Group 1: Connection Actions */}
      <div className="flex items-center gap-2" id="toolbar-connection-controls">
        {/* Toggle Connect Button */}
        <button
          onClick={onToggleConnect}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold transition-all border outline-none active:scale-95 cursor-pointer ${
            panel.isConnected
              ? 'bg-rose-50/80 border-rose-200/50 text-rose-600 dark:bg-rose-500/10 dark:border-rose-500/20 dark:text-rose-400 hover:bg-rose-100 dark:hover:bg-rose-500/20'
              : 'bg-emerald-50/80 border-emerald-200/50 text-emerald-600 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-500/20'
          }`}
          id="btn-connection-toggle"
        >
          <span className={`h-2 w-2 rounded-full ${panel.isConnected ? 'bg-rose-500 animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.6)]' : 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]'}`} />
          {panel.isConnected ? 'Disconnect' : 'Connect'}
        </button>

        {/* Global Pause toggle */}
        <button
          onClick={onPauseToggle}
          title={panel.autoScroll ? "Pause real-time console streaming" : "Resume terminal scroll"}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
            !panel.autoScroll
              ? 'bg-indigo-50/80 dark:bg-indigo-500/10 border-indigo-200/50 dark:border-indigo-500/20 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-500/20'
              : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80'
          }`}
          id="btn-pause-log"
        >
          {!panel.autoScroll ? <Play size={12} fill="currentColor" /> : <Pause size={12} />}
          <span>{!panel.autoScroll ? 'Resume' : 'Pause'}</span>
        </button>

        {/* Stop Connection button */}
        <button
          onClick={onStop}
          disabled={!panel.isConnected}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:border-rose-200 dark:hover:border-rose-500/30 hover:bg-rose-50 dark:hover:bg-rose-500/10 disabled:opacity-50 disabled:hover:bg-transparent dark:disabled:hover:bg-transparent disabled:hover:border-transparent dark:disabled:hover:border-transparent disabled:hover:text-slate-500 dark:disabled:hover:text-slate-400 rounded-lg border border-transparent transition-all cursor-pointer"
          id="btn-stop-connection"
        >
          <Square size={11} fill="currentColor" />
          <span>Stop</span>
        </button>
      </div>

      {/* Divider */}
      <div className="h-6 w-[1px] bg-slate-200 dark:bg-slate-800 mx-2" />

      {/* Group 2: Split Screen Diagnostic Layout Controls */}
      <div className="flex items-center gap-2" id="toolbar-layout-controls">
        {/* Add Log Board Split Panel */}
        <button
          onClick={onAddLogPanel}
          disabled={totalPanels >= 4}
          title="Split screen: Add Serial diagnostic board (Max 4)"
          className="p-1.5 rounded-lg border border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:border-slate-200 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 disabled:opacity-40 disabled:hover:bg-transparent dark:disabled:hover:bg-transparent disabled:hover:border-transparent disabled:hover:text-slate-600 transition-all cursor-pointer"
          id="btn-add-split-screen"
        >
          <Plus size={14} className="stroke-[3px]" />
        </button>

        {/* Remove Active Panel */}
        <button
          onClick={onRemoveLogPanel}
          disabled={totalPanels <= 1}
          title="Remove split board"
          className="p-1.5 rounded-lg border border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:border-slate-200 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400 disabled:opacity-40 disabled:hover:bg-transparent dark:disabled:hover:bg-transparent disabled:hover:border-transparent disabled:hover:text-slate-600 transition-all cursor-pointer"
          id="btn-remove-split-screen"
        >
          <Minus size={14} className="stroke-[3px]" />
        </button>

        {/* Sidebar Toggle check indicators */}
        <button
          onClick={onToggleSidebar}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
            sidebarVisible
              ? 'bg-blue-50/80 dark:bg-blue-500/10 border-blue-200/50 dark:border-blue-500/20 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-500/20'
              : 'bg-transparent border-transparent text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:border-slate-200 dark:hover:border-slate-700'
          }`}
          id="btn-toggle-config-sidebar"
        >
          <Sliders size={12} />
          <span>Sidebar</span>
        </button>
      </div>

      {/* Stretch spacer */}
      <div className="flex-1" />

      {/* Group 3: Settings & Theme Switch */}
      <div className="flex items-center gap-2" id="toolbar-global-actions">
        {/* Toggle Theme button */}
        <button
          onClick={onToggleTheme}
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
          className="flex items-center justify-center p-2 text-slate-500 dark:text-slate-400 hover:text-amber-500 dark:hover:text-amber-400 border border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:border-slate-200 dark:hover:border-slate-700 rounded-lg transition-all cursor-pointer"
          id="btn-toggle-theme"
        >
          {isDark ? <Sun size={13} className="text-amber-500 hover:scale-110 transition-transform" /> : <Moon size={13} className="bg-transparent hover:scale-110 transition-transform" />}
        </button>

        <button
          onClick={onOpenSettingsModal}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white border border-transparent hover:bg-slate-100 dark:hover:bg-slate-800/80 hover:border-slate-200 dark:hover:border-slate-700 rounded-lg transition-all cursor-pointer"
          id="btn-global-settings"
        >
          <Settings size={13} />
          <span>Settings</span>
        </button>
      </div>
    </header>
  );
}
