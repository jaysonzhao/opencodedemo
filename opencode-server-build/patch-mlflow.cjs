const fs = require('node:fs');
const p = '/opt/mlflow-src/libs/typescript/core/src/auth/index.ts';
let s = fs.readFileSync(p, 'utf8');
const anchor = "    if (workspace) {\n      headers['X-MLFLOW-WORKSPACE'] = workspace;\n    }";
if (s.split(anchor).length !== 2) throw new Error('MLflow auth source changed; review patch');
const patch = `    // Local integration: reread the rotating projected token per request.
    if (process.env.MLFLOW_TOKEN_PATH) {
      const { readFile } = await import('node:fs/promises');
      const token = (await readFile(process.env.MLFLOW_TOKEN_PATH, 'utf8')).trim();
      if (!token) throw new Error('Empty MLflow service-account token');
      headers['Authorization'] = 'Bearer ' + token;
    }
`;
fs.writeFileSync(p, s.replace(anchor, patch + anchor));
