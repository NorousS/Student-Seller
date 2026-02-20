@echo off
cd /d C:\projects\test_antigravity
node -e "const fs = require('fs'); ['frontend/src/api','frontend/src/components','frontend/src/hooks','frontend/src/pages/admin','frontend/src/pages/student','frontend/src/pages/employer','frontend/src/store','frontend/src/styles','frontend/public'].forEach(d => fs.mkdirSync(d, {recursive: true})); console.log('Done')"
