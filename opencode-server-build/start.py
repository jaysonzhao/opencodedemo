import json, os, pathlib, subprocess

os.umask(0o077)
e = os.environ
for k in ['BASE_URL','API_KEY','PROVIDER_ID','MODEL_NAME','OPENCODE_SERVER_PASSWORD',
          'MLFLOW_TRACKING_URI','MLFLOW_WORKSPACE','MLFLOW_EXPERIMENT_NAME']:
    if not e.get(k): raise RuntimeError('Missing environment setting: '+k)
for k in ['HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME']:
    pathlib.Path(e[k]).mkdir(parents=True, exist_ok=True)
workspace = pathlib.Path('/data/workspace')
workspace.mkdir(exist_ok=True)
os.chdir(workspace)
for key, value in [('user.name','OpenCode'),('user.email','opencode@openshift.local'),
                   ('init.defaultBranch','main'),('safe.directory',str(workspace))]:
    subprocess.run(['git','config','--global','--replace-all',key,value], check=True)
if not (workspace/'.git').exists(): subprocess.run(['git','init','-q'], check=True)
pid, model = e['PROVIDER_ID'], e['MODEL_NAME']
context, output = int(e['MODEL_CONTEXT']), int(e['MODEL_OUTPUT'])
if not (0 < output < context): raise RuntimeError('Require 0 < MODEL_OUTPUT < MODEL_CONTEXT')
config = {'$schema':'https://opencode.ai/config.json', 'autoupdate':False,
          'provider':{pid:{'npm':'@ai-sdk/openai-compatible','name':pid,
            'options':{'baseURL':e['BASE_URL'],'apiKey':e['API_KEY']},
            'models':{model:{'name':model,'limit':{'context':context,'output':output}}}}},
          'model':pid+'/'+model, 'small_model':pid+'/'+model, 'enabled_providers':[pid],
          'plugin':['file:///opt/mlflow-ts/integrations/opencode']}
e['OPENCODE_CONFIG_CONTENT'] = json.dumps(config)
# Python uses Kubernetes auth; the patched TypeScript SDK uses MLFLOW_TOKEN_PATH.
# Do not snapshot the rotating token into MLFLOW_TRACKING_TOKEN.
e.pop('MLFLOW_TRACKING_TOKEN', None)
import mlflow
mlflow.set_tracking_uri(e['MLFLOW_TRACKING_URI'])
experiment = mlflow.set_experiment(e['MLFLOW_EXPERIMENT_NAME'])
e['MLFLOW_EXPERIMENT_ID'] = str(experiment.experiment_id)
pathlib.Path('/tmp/mlflow-experiment-id').write_text(e['MLFLOW_EXPERIMENT_ID'])
print('MLflow experiment ready: '+e['MLFLOW_EXPERIMENT_ID'], flush=True)
os.execvp('opencode', ['opencode','serve','--hostname','0.0.0.0','--port','4096'])
