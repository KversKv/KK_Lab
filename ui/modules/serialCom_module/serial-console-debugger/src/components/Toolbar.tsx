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
    <header className="h-14 bg-white border-b border-gray-200 px-4 flex items-center justify-between shadow-xs select-none" id="serial-top-toolbar">
      {/* Group 1: Connection Actions */}
      <div className="flex items-center gap-2" id="toolbar-connection-controls">
        {/* Toggle Connect Button */}
        <button
          onClick={onToggleConnect}
          className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold transition-all border outline-none active:scale-97 cursor-pointer ${
            panel.isConnected
              ? 'bg-[#FFECEA] border-[#FFD3D1] text-[#D70015] hover:bg-[#FFDAD6]'
              : 'bg-[#E8F8EE] border-[#CDEED5] text-[#248A3D] hover:bg-[#DDF7E6]'
          }`}
          id="btn-connection-toggle"
        >
          <span className={`h-2 w-2 rounded-full ${panel.isConnected ? 'bg-[#FF3B30] animate-pulse' : 'bg-[#34C759]'}`} />
          {panel.isConnected ? 'Disconnect' : 'Connect'}
        </button>

        {/* Global Pause toggle */}
        <button
          onClick={onPauseToggle}
          title={panel.autoScroll ? "Pause real-time console streaming" : "Resume terminal scroll"}
          className={`flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
            !panel.autoScroll
              ? 'bg-[#E8F2FF] border-[#BBD7FF] text-[#007AFF] hover:bg-[#D6E7FF]'
              : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
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
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-gray-500 hover:text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:hover:bg-transparent rounded-lg border border-gray-150 transition-all cursor-pointer"
          id="btn-stop-connection"
        >
          <Square size={11} fill="currentColor" />
          <span>Stop</span>
        </button>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-gray-200 mx-2" />

      {/* Group 2: Split Screen Diagnostic Layout Controls */}
      <div className="flex items-center gap-2" id="toolbar-layout-controls">
        {/* Add Log Board Split Panel */}
        <button
          onClick={onAddLogPanel}
          disabled={totalPanels >= 4}
          title="Split screen: Add Serial diagnostic board (Max 4)"
          className="p-2 rounded-lg border border-gray-150 hover:bg-[#E8F8EE] text-[#248A3D] disabled:opacity-40 disabled:hover:bg-transparent transition-all cursor-pointer"
          id="btn-add-split-screen"
        >
          <Plus size={14} className="stroke-[3px]" />
        </button>

        {/* Remove Active Panel */}
        <button
          onClick={onRemoveLogPanel}
          disabled={totalPanels <= 1}
          title="Remove split board"
          className="p-2 rounded-lg border border-gray-150 hover:bg-[#FFECEA] text-[#D70015] disabled:opacity-40 disabled:hover:bg-transparent transition-all cursor-pointer"
          id="btn-remove-split-screen"
        >
          <Minus size={14} className="stroke-[3px]" />
        </button>

        {/* Sidebar Toggle check indicators */}
        <button
          onClick={onToggleSidebar}
          className={`flex items-center gap-1 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all cursor-pointer ${
            sidebarVisible
              ? 'bg-[#E8F2FF] border-[#BBD7FF] text-[#007AFF] hover:bg-[#D6E7FF]'
              : 'bg-white border-gray-205 text-gray-500 hover:bg-gray-50'
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
          className="flex items-center justify-center p-2 text-gray-500 hover:text-gray-900 border border-gray-150 hover:bg-gray-100 rounded-lg transition-all cursor-pointer"
          id="btn-toggle-theme"
        >
          {isDark ? <Sun size={13} className="text-amber-500 hover:scale-110 transition-transform" /> : <Moon size={13} className="bg-transparent hover:scale-110 transition-transform" />}
        </button>

        <button
          onClick={onOpenSettingsModal}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold text-gray-500 hover:text-gray-900 border border-gray-150 hover:bg-gray-100 rounded-lg transition-all cursor-pointer"
          id="btn-global-settings"
        >
          <Settings size={13} />
          <span>Settings</span>
        </button>
      </div>
    </header>
  );
}
