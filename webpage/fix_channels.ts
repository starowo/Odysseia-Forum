import * as fs from 'fs';

const data = JSON.parse(fs.readFileSync('./.gemini/antigravity/brain/1852de71-019f-4248-9c68-0bc023220f60/.system_generated/steps/632/content.md', 'utf8').split('---')[1].trim());
console.log("Total top-level channels:", data.length);
