const fs = require('fs');

const files = [
  'src/App.tsx',
  'src/components/Toolbar.tsx',
  'src/components/Sidebar.tsx',
  'src/components/LogGrid.tsx',
  'src/components/QuickCommandsTab.tsx',
  'src/components/ScriptsTab.tsx',
  'src/components/SettingsModal.tsx'
];

files.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  
  // Create a mapping pattern
  const rules = [
    { regex: / (bg-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:bg-slate-$2' },
    { regex: / (text-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:text-slate-$2' },
    { regex: / (border-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:border-slate-$2' },
    { regex: / (hover:bg-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:hover:bg-slate-$2' },
    { regex: / (hover:text-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:hover:text-slate-$2' },
    { regex: / (hover:border-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:hover:border-slate-$2' },
    { regex: / (placeholder:text-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:placeholder:text-slate-$2' },
    { regex: / (scrollbar-thumb-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:scrollbar-thumb-slate-$2' },
    { regex: / (disabled:hover:bg-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:disabled:hover:bg-slate-$2' },
    { regex: / (disabled:hover:text-[a-z0-9/A-Z-]+(?:\[[^\]]+\])?) slate-([0-9/]+)/g, replace: ' $1 dark:disabled:hover:text-slate-$2' },
  ];

  // We loop a few times because some classes are adjacent and the regex might skip overlapping matches
  for (let i = 0; i < 3; i++) {
    for (const rule of rules) {
      content = content.replace(rule.regex, rule.replace);
    }
  }

  // Then add fixes for other things or custom fixes
  content = content.replace(/dark:bg-slate-950/g, 'dark:bg-[#020617]'); // deep dark blue

  // Edge cases if any exist
  
  fs.writeFileSync(file, content);
});

console.log('Restoration complete!');
