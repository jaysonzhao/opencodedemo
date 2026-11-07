# OpenCode on OpenShift with MiniMax and MLflow

This repository contains the OpenShift deployment source, a disposable service smoke-test client, the supporting scripts, and the deployment skill.

## Deployed configuration

- Namespace: `opencode`
- OpenCode image: `quay.io/opendatahub/odh-opencode-rhel9:v1.18.3`, extended with the MLflow 3.14.0 OpenCode plugin and rotating service-account token support
- Model provider: `minimax-openai` using the OpenAI-compatible endpoint `https://api.minimax.io/v1`
- Model ID: `MiniMax-M2.7-highspeed`
- Configured model limits: 204,800 context tokens and 8,192 output tokens
- MLflow workspace and experiment: `opencode` / `opencode-traces`
- Persistent state: 10 GiB `gp3-csi` RWO PVC
- Service: internal `ClusterIP` on port 4096; no Route is created

The image reference in `opencode-server-build/workload.yaml` points to the validated image digest in the deployment cluster. Rebuild and refresh the digest before applying the workload to another cluster.

## Deploy

Prerequisites include OpenShift 4.20+, the existing MLflow service at `redhat-ods-applications/mlflow:8443/mlflow`, the `mlflow-operator-mlflow-integration` ClusterRole, `gp3-csi`, and permission to build and push to the cluster's internal registry.

Log in to the intended cluster, then create the project if needed and apply the dedicated service account and workspace-scoped MLflow RoleBinding:

```bash
oc get namespace opencode >/dev/null 2>&1 || oc new-project opencode
oc -n opencode create serviceaccount opencode-server --dry-run=client -o yaml | oc apply -f -
oc -n opencode create rolebinding opencode-mlflow \
  --clusterrole=mlflow-operator-mlflow-integration \
  --serviceaccount=opencode:opencode-server --dry-run=client -o yaml | oc apply -f -
```

Create the Secret-backed provider and server credentials. The script reads the MiniMax key from `~/work/minimax.key` by default, sends Secret manifests to `oc` over stdin, and never prints secret values. It creates the random server password only if `opencode-server-auth` does not already exist.

```bash
python3 scripts/create-secrets.py --key-file ~/work/minimax.key
```

Build the image, update the pinned digest in both deployment and smoke-test manifests, then apply the workload:

```bash
oc -n opencode apply -f opencode-server-build/build.yaml
oc -n opencode start-build opencode-server --from-dir=opencode-server-build --follow --wait
python3 scripts/update-image-digest.py --namespace opencode
oc -n opencode apply --dry-run=server -f opencode-server-build/workload.yaml
oc -n opencode apply -f opencode-server-build/workload.yaml
oc -n opencode rollout status deployment/opencode-server --timeout=10m
```

## Smoke test and trace verification

The test client has only the OpenCode server-auth Secret and no Kubernetes service-account token. It checks Service access, Basic-auth enforcement, and a marked model response.

```bash
oc -n opencode delete pod/opencode-client-check configmap/opencode-client-check --ignore-not-found
oc -n opencode create configmap opencode-client-check \
  --from-file=client.py=opencode-server-build/client.py --dry-run=client -o yaml | oc apply -f -
oc -n opencode create -f opencode-server-build/client.yaml
oc -n opencode wait --for=jsonpath='{.status.phase}=Succeeded' pod/opencode-client-check --timeout=6m
oc -n opencode logs pod/opencode-client-check
```

Use the printed marker to verify a matching trace in the `opencode` workspace and `opencode-traces` experiment. Follow the complete MLflow trace and persistence checks in [`SKILL.md`](skills/deploy-opencode-openshift-mlflow/SKILL.md). Remove the disposable test resources after verification:

```bash
oc -n opencode delete pod/opencode-client-check configmap/opencode-client-check
```

## Connect

Inside the cluster, use `http://opencode-server.opencode.svc.cluster.local:4096`. For local access:

```bash
oc -n opencode port-forward svc/opencode-server 4096:4096
```

The Basic-auth username is `opencode`. Retrieve the generated password from the OpenShift Secret when needed:

```bash
oc -n opencode get secret opencode-server-auth \
  -o jsonpath='{.data.OPENCODE_SERVER_PASSWORD}' |
  python3 -c 'import base64,sys; print(base64.b64decode(sys.stdin.buffer.read()).decode())'
```

The MiniMax API key remains in `Secret/opencode-provider`; credentials and local key files are excluded from this repository.
