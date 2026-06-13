import React, { useState } from 'react';
import { QuickProject, QuickGroup, QuickCommand } from '../types';
import { 
  Plus, FolderPlus, Download, Upload, Zap, Edit3, Trash2, ChevronLeft, ChevronRight, Eye 
} from 'lucide-react';

interface QuickCommandsTabProps {
  projects: QuickProject[];
  setProjects: React.Dispatch<React.SetStateAction<QuickProject[]>>;
  activeProjectId: string;
  setActiveProjectId: (id: string) => void;
  activeGroupId: string;
  setActiveGroupId: (id: string) => void;
  onSendCommand: (cmd: QuickCommand) => void;
}

export function QuickCommandsTab({
  projects,
  setProjects,
  activeProjectId,
  setActiveProjectId,
  activeGroupId,
  setActiveGroupId,
  onSendCommand
}: QuickCommandsTabProps) {
  const [hoveredCommand, setHoveredCommand] = useState<QuickCommand | null>(null);
  const [hoveredPosition, setHoveredPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Dialog configurations
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showCommandModal, setShowCommandModal] = useState(false);

  // Edit variables
  const [modalType, setModalType] = useState<'create' | 'edit'>('create');
  const [currentProjectName, setCurrentProjectName] = useState('');
  const [currentGroupName, setCurrentGroupName] = useState('');

  // Command edit states
  const [commandName, setCommandName] = useState('');
  const [commandContent, setCommandContent] = useState('');
  const [commandFormat, setCommandFormat] = useState<'text' | 'hex'>('text');
  const [commandEnding, setCommandEnding] = useState('\r\n');
  const [commandEncoding, setCommandEncoding] = useState('utf-8');
  const [editingCommandId, setEditingCommandId] = useState<string | null>(null);

  const activeProject = projects.find(p => p.id === activeProjectId) || projects[0];
  const activeGroup = activeProject?.groups.find(g => g.id === activeGroupId) || activeProject?.groups[0];

  // Helper projects/groups actions
  const handleAddNewProject = () => {
    setCurrentProjectName('');
    setModalType('create');
    setShowProjectModal(true);
  };

  const handleEditProject = (p: QuickProject) => {
    setCurrentProjectName(p.name);
    setModalType('edit');
    setShowProjectModal(true);
  };

  const handleDeleteProject = (pId: string) => {
    if (projects.length <= 1) return;
    if (confirm("Are you sure you want to delete this project and all its quick commands?")) {
      const filtered = projects.filter(p => p.id !== pId);
      setProjects(filtered);
      setActiveProjectId(filtered[0].id);
      const nextGroup = filtered[0].groups[0];
      if (nextGroup) setActiveGroupId(nextGroup.id);
    }
  };

  const handleSaveProject = () => {
    if (!currentProjectName.trim()) return;
    if (modalType === 'create') {
      const newProjId = `project_${Date.now()}`;
      const newGroupId = `group_${Date.now()}`;
      const newProj: QuickProject = {
        id: newProjId,
        name: currentProjectName.trim(),
        groups: [
          { id: newGroupId, name: 'Default Group', commands: [] }
        ]
      };
      setProjects([...projects, newProj]);
      setActiveProjectId(newProjId);
      setActiveGroupId(newGroupId);
    } else {
      setProjects(projects.map(p => p.id === activeProjectId ? { ...p, name: currentProjectName.trim() } : p));
    }
    setShowProjectModal(false);
  };

  // Group helpers
  const handleAddNewGroup = () => {
    setCurrentGroupName('');
    setModalType('create');
    setShowGroupModal(true);
  };

  const handleEditGroup = (g: QuickGroup) => {
    setCurrentGroupName(g.name);
    setModalType('edit');
    setShowGroupModal(true);
  };

  const handleDeleteGroup = (gId: string) => {
    if (!activeProject || activeProject.groups.length <= 1) return;
    if (confirm("Delete this group and all its commands?")) {
      const updatedGroups = activeProject.groups.filter(g => g.id !== gId);
      setProjects(projects.map(p => p.id === activeProject.id ? { ...p, groups: updatedGroups } : p));
      setActiveGroupId(updatedGroups[0].id);
    }
  };

  const handleSaveGroup = () => {
    if (!currentGroupName.trim() || !activeProject) return;
    if (modalType === 'create') {
      const newGrpId = `group_${Date.now()}`;
      const newGrp: QuickGroup = {
        id: newGrpId,
        name: currentGroupName.trim(),
        commands: []
      };
      setProjects(projects.map(p => p.id === activeProject.id ? { ...p, groups: [...p.groups, newGrp] } : p));
      setActiveGroupId(newGrpId);
    } else {
      setProjects(projects.map(p => {
        if (p.id === activeProject.id) {
          return {
            ...p,
            groups: p.groups.map(g => g.id === activeGroupId ? { ...g, name: currentGroupName.trim() } : g)
          };
        }
        return p;
      }));
    }
    setShowGroupModal(false);
  };

  // Command helpers
  const handleOpenCommandModal = (type: 'create' | 'edit', cmd?: QuickCommand) => {
    setModalType(type);
    if (type === 'edit' && cmd) {
      setCommandName(cmd.name);
      setCommandContent(cmd.content);
      setCommandFormat(cmd.send_type);
      setCommandEnding(cmd.line_ending);
      setCommandEncoding(cmd.encoding);
      setEditingCommandId(cmd.id);
    } else {
      setCommandName('');
      setCommandContent('');
      setCommandFormat('text');
      setCommandEnding('\r\n');
      setCommandEncoding('utf-8');
      setEditingCommandId(null);
    }
    setShowCommandModal(true);
  };

  const handleSaveCommand = () => {
    if (!commandContent.trim() || !activeProject || !activeGroup) return;
    const finalCmd: QuickCommand = {
      id: editingCommandId || `cmd_${Date.now()}`,
      name: commandName.trim() || commandContent.trim(),
      content: commandContent,
      send_type: commandFormat,
      line_ending: commandEnding,
      encoding: commandEncoding
    };

    setProjects(projects.map(p => {
      if (p.id === activeProject.id) {
        return {
          ...p,
          groups: p.groups.map(g => {
            if (g.id === activeGroup.id) {
              if (modalType === 'edit') {
                return { ...g, commands: g.commands.map(c => c.id === editingCommandId ? finalCmd : c) };
              } else {
                return { ...g, commands: [...g.commands, finalCmd] };
              }
            }
            return g;
          })
        };
      }
      return p;
    }));
    setShowCommandModal(false);
  };

  const handleDeleteCommand = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeProject || !activeGroup) return;
    if (confirm("Delete this command?")) {
      setProjects(projects.map(p => {
        if (p.id === activeProject.id) {
          return {
            ...p,
            groups: p.groups.map(g => {
              if (g.id === activeGroup.id) {
                return { ...g, commands: g.commands.filter(c => c.id !== id) };
              }
              return g;
            })
          };
        }
        return p;
      }));
    }
  };

  // Reorder commands row helpers (simulate drag & drop or click movements)
  const handleMoveCommandIndex = (idx: number, delta: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!activeProject || !activeGroup) return;
    const targetIdx = idx + delta;
    if (targetIdx < 0 || targetIdx >= activeGroup.commands.length) return;
    
    const cmds = [...activeGroup.commands];
    const temp = cmds[idx];
    cmds[idx] = cmds[targetIdx];
    cmds[targetIdx] = temp;

    setProjects(projects.map(p => {
      if (p.id === activeProject.id) {
        return {
          ...p,
          groups: p.groups.map(g => g.id === activeGroup.id ? { ...g, commands: cmds } : g)
        };
      }
      return p;
    }));
  };

  // Import JSON configurations
  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const payload = JSON.parse(event.target?.result as string);
        let parsedProjects: QuickProject[] = [];

        if (Array.isArray(payload.projects)) {
          parsedProjects = payload.projects;
        } else if (payload.quick_commands && Array.isArray(payload.quick_commands.projects)) {
          parsedProjects = payload.quick_commands.projects;
        } else if (Array.isArray(payload)) {
          parsedProjects = payload;
        } else {
          alert("Invalid layout formatting structure.");
          return;
        }

        if (parsedProjects.length > 0) {
          setProjects(parsedProjects);
          setActiveProjectId(parsedProjects[0].id);
          const firstGrp = parsedProjects[0].groups[0];
          if (firstGrp) {
            setActiveGroupId(firstGrp.id);
          }
          alert(`Successfully imported ${parsedProjects.length} projects!`);
        }
      } catch (err) {
        alert("Failed to parse JSON file: " + err);
      }
    };
    reader.readAsText(file);
  };

  // Export JSON configurations
  const handleExportJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ projects, version: "2.0" }, null, 2));
    const dlAnchorElem = document.createElement('a');
    dlAnchorElem.setAttribute("href", dataStr);
    dlAnchorElem.setAttribute("download", "KK_QuickCommands.json");
    dlAnchorElem.click();
  };

  // Handler for mouse positioning hovering preview card
  const handleMouseMove = (cmd: QuickCommand, e: React.MouseEvent) => {
    setHoveredCommand(cmd);
    setHoveredPosition({ x: e.clientX + 14, y: e.clientY + 14 });
  };

  return (
    <div className="flex flex-col h-full bg-[#FAFBFD] dark:bg-zinc-950" id="quick-commands-console">
      {/* 1. PROJECT TOP TABS BAR */}
      <div className="flex items-center justify-between border-b border-gray-150 dark:border-zinc-800 px-4 py-1" id="project-tabs-navigation">
        <div className="flex items-center gap-1.5 overflow-x-auto max-w-[80vw]" id="tabs-container">
          <Zap size={13} className="text-[#FF9F0A] animate-pulse" />
          
          {projects.map((proj) => {
            const isSel = proj.id === activeProjectId;
            return (
              <div
                key={proj.id}
                onClick={() => {
                  setActiveProjectId(proj.id);
                  if (proj.groups[0]) setActiveGroupId(proj.groups[0].id);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-t-lg transition-all border-t border-x cursor-pointer ${
                  isSel 
                    ? 'bg-white text-slate-800 border-gray-200 -mb-[5px] z-10 dark:bg-zinc-900 dark:text-zinc-100 dark:border-zinc-800' 
                    : 'bg-[#F2F2F7] border-transparent text-gray-400 hover:text-slate-700 hover:bg-[#FAFBFD] dark:bg-zinc-800 dark:text-zinc-400 dark:hover:text-zinc-200 dark:hover:bg-zinc-900'
                }`}
              >
                <span>{proj.name}</span>
                {isSel && (
                  <div className="flex gap-0.5 ml-1 opacity-0 hover:opacity-100 transition-opacity">
                    <button onClick={(e) => { e.stopPropagation(); handleEditProject(proj); }} className="hover:text-blue-500 p-0.5"><Edit3 size={10} /></button>
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteProject(proj.id); }} className="hover:text-red-500 p-0.5"><Trash2 size={10} /></button>
                  </div>
                )}
              </div>
            );
          })}

          {/* Add Project prompt trigger */}
          <button 
            onClick={handleAddNewProject}
            className="p-1 text-[#007AFF] hover:bg-blue-50 rounded"
            title="Create new project folder"
          >
            <Plus size={13} className="stroke-[3px]" />
          </button>
        </div>

        {/* Import/Export buttons */}
        <div className="flex items-center gap-1 text-[11px] font-bold text-gray-500 dark:text-zinc-400">
          <label className="flex items-center gap-1 border border-gray-150 rounded-lg p-1.5 bg-white hover:bg-gray-50 dark:bg-zinc-800 dark:border-zinc-700 dark:hover:bg-zinc-700 dark:text-zinc-200 cursor-pointer">
            <Upload size={12} />
            <span>Import</span>
            <input type="file" accept=".json" onChange={handleImportJson} className="hidden" />
          </label>
          
          <button 
            onClick={handleExportJson}
            className="flex items-center gap-1 border border-gray-150 rounded-lg p-1.5 bg-white hover:bg-[#E8F2FF] text-[#007AFF] dark:bg-zinc-800 dark:border-zinc-700 dark:hover:bg-zinc-700 dark:text-blue-400 cursor-pointer"
          >
            <Download size={12} />
            <span>Export</span>
          </button>
        </div>
      </div>

      {/* 2. GROUP SELECTOR AND CONTROLS ACTION ROW */}
      <div className="bg-[#FAFBFD] dark:bg-zinc-900 px-4 py-2 border-b border-gray-150 dark:border-zinc-800 flex items-center justify-between text-xs select-none" id="group-action-row">
        <div className="flex items-center gap-3">
          <span className="font-semibold text-gray-500 dark:text-zinc-400">Group:</span>
          {activeProject ? (
            <div className="flex items-center gap-2">
              <select
                value={activeGroupId}
                onChange={(e) => setActiveGroupId(e.target.value)}
                className="bg-white dark:bg-zinc-800 text-xs border border-gray-200 dark:border-zinc-700 p-1.5 rounded-lg focus:outline-none dark:text-zinc-100"
              >
                {activeProject.groups.map(g => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>

              <button 
                onClick={handleAddNewGroup}
                className="flex items-center gap-0.5 px-2 py-1 bg-white hover:bg-blue-50 text-[#007AFF] dark:bg-zinc-800 dark:hover:bg-zinc-700 dark:text-blue-400 dark:border-zinc-700 border border-gray-150 rounded-lg font-bold transition-all cursor-pointer"
              >
                <FolderPlus size={11} />
                <span>+ Group</span>
              </button>

              {activeGroup && (
                <div className="flex gap-1.5 ml-1">
                  <button onClick={() => handleEditGroup(activeGroup)} className="text-gray-400 hover:text-blue-500"><Edit3 size={11} /></button>
                  <button onClick={() => handleDeleteGroup(activeGroup.id)} className="text-gray-400 hover:text-red-500"><Trash2 size={11} /></button>
                </div>
              )}
            </div>
          ) : (
            <span className="text-gray-400 italic">No groups loaded.</span>
          )}
        </div>

        {/* Add button trigger */}
        <button
          onClick={() => handleOpenCommandModal('create')}
          disabled={!activeGroup}
          className="flex items-center gap-1 px-3 py-1.5 bg-[#007AFF] text-white rounded-lg font-bold hover:bg-[#0A84FF] disabled:opacity-50 transition-all cursor-pointer shadow-sm active:scale-97"
        >
          <Plus size={13} className="stroke-[3px]" />
          <span>Add Command</span>
        </button>
      </div>

      {/* 3. BUTTONS WORKSPACE OR GRID */}
      <div className="p-4 flex-1 overflow-y-auto" id="quick-buttons-panel-scroll">
        {!activeGroup || activeGroup.commands.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 py-16 text-center select-none">
            <Zap size={24} className="stroke-[1.5] text-amber-400 mb-2" />
            <p className="text-xs font-bold text-gray-400 dark:text-zinc-500">Default group is empty</p>
            <p className="text-[10px] text-gray-300 dark:text-zinc-600 mt-0.5">Click &quot;Add Command&quot; to append debug macros or hex sensor directives.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3" id="quick-buttons-grid">
            {activeGroup.commands.map((cmd, idx) => {
              return (
                <div
                  key={cmd.id}
                  onClick={() => onSendCommand(cmd)}
                  onMouseMove={(e) => handleMouseMove(cmd, e)}
                  onMouseLeave={() => setHoveredCommand(null)}
                  className="relative group bg-[#F2F2F7] dark:bg-zinc-800 hover:bg-[#E8F2FF] dark:hover:bg-zinc-700 border border-gray-150 dark:border-zinc-700 hover:border-[#BBD7FF] dark:hover:border-zinc-600 text-slate-800 dark:text-zinc-100 hover:text-[#007AFF] dark:hover:text-blue-400 px-3.5 py-3 rounded-lg text-center font-bold text-xs select-none transition-all active:scale-97 shadow-xs flex flex-col justify-center items-center h-16 cursor-pointer"
                  id={`quick-cmd-btn-${idx}`}
                >
                  {/* Reordering indicators / Edit actions - visible on hover */}
                  <div className="absolute top-1 right-1 flex opacity-0 group-hover:opacity-100 transition-opacity gap-0.5 z-20">
                    <button 
                      onClick={(e) => handleMoveCommandIndex(idx, -1, e)}
                      title="Move Left"
                      disabled={idx === 0}
                      className="text-gray-450 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-600 p-0.5 rounded disabled:opacity-30"
                    >
                      <ChevronLeft size={10} />
                    </button>
                    <button 
                      onClick={(e) => handleMoveCommandIndex(idx, 1, e)}
                      title="Move Right"
                      disabled={idx === activeGroup.commands.length - 1}
                      className="text-gray-455 dark:text-zinc-400 hover:bg-gray-100 dark:hover:bg-zinc-600 p-0.5 rounded disabled:opacity-30"
                    >
                      <ChevronRight size={10} />
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleOpenCommandModal('edit', cmd); }}
                      title="Edit macro"
                      className="text-blue-500 hover:bg-blue-50 dark:hover:bg-zinc-600 p-0.5 rounded"
                    >
                      <Edit3 size={10} />
                    </button>
                    <button 
                      onClick={(e) => handleDeleteCommand(cmd.id, e)}
                      title="Delete macro"
                      className="text-red-500 hover:bg-red-50 dark:hover:bg-zinc-600 p-0.5 rounded"
                    >
                      <Trash2 size={10} />
                    </button>
                  </div>

                  <span className="truncate w-full block text-center break-all">{cmd.name}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 4. HOVER FLOATING PREVIEW CARD (matched style to PySide6 `_QuickCmdPreviewPopup`) */}
      {hoveredCommand && (
        <div 
          className="fixed bg-white dark:bg-zinc-900 border border-gray-250 dark:border-zinc-700 shadow-xl rounded-xl p-3 z-50 pointer-events-none w-72 text-left space-y-2 leading-relaxed animate-fade-in text-gray-850 dark:text-zinc-200"
          style={{ left: hoveredPosition.x, top: hoveredPosition.y }}
          id="cmd-hover-floating-dialog"
        >
          <div className="flex items-center gap-2 border-b border-gray-100 dark:border-zinc-800 pb-1">
            <span className="text-[9px] font-bold text-white bg-[#FF9F0A] px-1.5 py-0.5 rounded">QUICK CMD</span>
            <span className="text-xs font-bold text-gray-800 dark:text-zinc-100 truncate">{hoveredCommand.name}</span>
          </div>
          <div className="bg-gray-50 dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded p-1.5 font-mono text-[10px] break-all max-h-24 overflow-y-auto">
            {hoveredCommand.content}
          </div>
          <div className="flex justify-between text-[9px] text-gray-400 dark:text-zinc-500 font-bold">
            <span>Format: {hoveredCommand.send_type.toUpperCase()}</span>
            <span>Line Ending: {repr(hoveredCommand.line_ending)}</span>
          </div>
        </div>
      )}

      {/* MODAL 1: ADD/EDIT PROJECT */}
      {showProjectModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800">
            <h3 className="text-sm font-bold text-slate-800">{modalType === 'create' ? "New Project" : "Rename Project"}</h3>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-gray-400 tracking-wide uppercase">Project Name</label>
              <input
                type="text"
                placeholder="e.g. ESP32 Sensor"
                value={currentProjectName}
                onChange={(e) => setCurrentProjectName(e.target.value)}
                className="w-full text-xs bg-gray-50 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 text-xs font-bold">
              <button onClick={() => setShowProjectModal(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Cancel</button>
              <button onClick={handleSaveProject} className="px-4 py-2 bg-[#FF9F0A] text-white rounded-lg hover:bg-amber-600 cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: ADD/EDIT GROUP */}
      {showGroupModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-sm w-full p-5 shadow-2xl space-y-4 text-slate-800">
            <h3 className="text-sm font-bold text-slate-800">{modalType === 'create' ? "New Group" : "Rename Group"}</h3>
            <div className="space-y-1">
              <label className="text-[10px] font-bold text-gray-400 tracking-wide uppercase">Group Name</label>
              <input
                type="text"
                placeholder="e.g. WiFi Credentials"
                value={currentGroupName}
                onChange={(e) => setCurrentGroupName(e.target.value)}
                className="w-full text-xs bg-gray-50 border border-gray-200 rounded-lg p-2 focus:ring-1 focus:ring-[#007AFF] outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 text-xs font-bold">
              <button onClick={() => setShowGroupModal(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Cancel</button>
              <button onClick={handleSaveGroup} className="px-4 py-2 bg-[#007AFF] text-white rounded-lg hover:bg-[#0A84FF] cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: ADD/EDIT COMMAND */}
      {showCommandModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-5 shadow-2xl space-y-4 text-slate-800">
            <h3 className="text-sm font-bold text-slate-800">{modalType === 'create' ? "New Quick Command" : "Edit Command"}</h3>
            
            <div className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="font-bold text-gray-400 text-[10px]">指令名称 / Macro Name</label>
                <input
                  type="text"
                  placeholder="e.g. Core Ping"
                  value={commandName}
                  onChange={(e) => setCommandName(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 outline-none focus:ring-1 focus:ring-[#007AFF]"
                />
              </div>

              <div className="space-y-1">
                <label className="font-bold text-gray-400 text-[10px]">指令内容 / Raw Payload</label>
                <input
                  type="text"
                  placeholder="e.g. AT or 01 02 C0 AB"
                  value={commandContent}
                  onChange={(e) => setCommandContent(e.target.value)}
                  className="w-full bg-gray-50 border border-gray-200 rounded-lg p-2 outline-none focus:ring-1 focus:ring-[#007AFF]"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="font-bold text-gray-400 text-[10px]">Format</label>
                  <select
                    value={commandFormat}
                    onChange={(e) => setCommandFormat(e.target.value as any)}
                    className="w-full bg-gray-50 border border-gray-250 p-2 rounded-lg"
                  >
                    <option value="text">TEXT</option>
                    <option value="hex">HEX</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-gray-400 text-[10px]">Line Ending</label>
                  <select
                    value={commandEnding}
                    onChange={(e) => setCommandEnding(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-250 p-2 rounded-lg"
                  >
                    <option value="">None</option>
                    <option value="\r">\r</option>
                    <option value="\n">\n</option>
                    <option value="\r\n">\r\n</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-bold text-gray-400 text-[10px]">Encoding</label>
                  <select
                    value={commandEncoding}
                    onChange={(e) => setCommandEncoding(e.target.value)}
                    className="w-full bg-gray-50 border border-gray-250 p-2 rounded-lg"
                  >
                    <option value="utf-8">UTF-8</option>
                    <option value="ascii">ASCII</option>
                    <option value="gbk">GBK</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 text-xs font-bold pt-2 border-t border-gray-100">
              <button onClick={() => setShowCommandModal(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-gray-500 hover:bg-gray-50 cursor-pointer">Cancel</button>
              <button onClick={handleSaveCommand} className="px-4 py-2 bg-[#34C759] text-white rounded-lg hover:bg-[#30B650] cursor-pointer">OK</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Converts line endings to clean prints on tooltips
function repr(str: string): string {
  if (str === '\r\n') return '\\r\\n';
  if (str === '\n') return '\\n';
  if (str === '\r') return '\\r';
  if (str === '\n\r') return '\\n\\r';
  return 'None';
}
