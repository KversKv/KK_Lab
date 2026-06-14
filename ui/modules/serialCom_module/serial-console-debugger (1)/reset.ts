import { execSync } from "child_process";
execSync("git checkout -- src/components/*.tsx src/App.tsx", { stdio: "inherit" });
