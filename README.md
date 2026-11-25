# DevOps Demo: Flask App with CI, GitOps and Monitoring

A small end-to-end project that takes a Python Flask app from code to a running Kubernetes deployment, with automatic image builds, Git-driven deployment and monitoring.

## How it works

    Push to app/  ->  GitHub Actions  ->  image in GitHub Container Registry (GHCR)

    Push to k8s/  ->  Argo CD  ->  kind cluster (namespace: demo, 3 replicas)

    Prometheus scrapes /metrics  ->  Grafana dashboard

1. **App.** A Flask app with three endpoints: `/` (home page), `/health` (used by Kubernetes probes) and `/metrics` (Prometheus format). A custom counter, `app_requests_total`, counts requests to the home page.
2. **CI.** A GitHub Actions workflow runs on every push to `main` that changes `app/`, or manually. It builds the Docker image and pushes it to GHCR, tagged with the commit SHA and `latest`.
3. **GitOps deployment.** Argo CD watches the `k8s/` folder on the `main` branch and applies it to the `demo` namespace. Automated sync, prune and self-heal are on, so Git is the source of truth: anything changed by hand in the cluster is reverted.
4. **Monitoring.** Prometheus and Grafana are installed with Helm using the `kube-prometheus-stack` chart. A ServiceMonitor tells Prometheus to scrape the app's `/metrics` every 15 seconds. A Grafana dashboard shows requests per second and total requests.

## Repository layout

| Path | What it holds |
|------|---------------|
| `app/` | Flask app, `requirements.txt` and `Dockerfile` |
| `.github/workflows/ci.yml` | GitHub Actions pipeline that builds and pushes the image |
| `k8s/` | Namespace, Deployment, Service and ServiceMonitor (managed by Argo CD) |
| `argocd/application.yaml` | Argo CD Application that points at `k8s/` |
| `helm/monitoring-values.yaml` | Custom settings for the `kube-prometheus-stack` Helm chart |
| `grafana/flask-app-dashboard.json` | Exported Grafana dashboard (backup) |

## How to run it

Prerequisites: Docker Desktop, Git, kubectl, kind and Helm.

1. Create the cluster:

        kind create cluster --name devops-demo

2. Install Prometheus and Grafana first. They provide the ServiceMonitor type used in `k8s/`:

        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo update
        helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f helm/monitoring-values.yaml

3. Install Argo CD:

        kubectl create namespace argocd
        kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

4. Tell Argo CD to deploy the app from Git:

        kubectl apply -f argocd/application.yaml

   `argocd/application.yaml` points at this repository. If you fork the repo, change `repoURL` to your fork. The image is pulled from GHCR, so the package must be public.

5. Check everything is running:

        kubectl get applications -n argocd
        kubectl get pods -n demo
        kubectl get pods -n monitoring

## Open the tools

Each command keeps running, so use a separate terminal for each.

| Tool | Command | URL |
|------|---------|-----|
| App | `kubectl port-forward -n demo svc/devops-demo-app 8080:80` | http://localhost:8080 |
| Prometheus | `kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090` | http://localhost:9090 |
| Grafana | `kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80` | http://localhost:3000 |
| Argo CD | `kubectl port-forward -n argocd svc/argocd-server 8081:443` | https://localhost:8081 |

Grafana user is `admin`. To get the password in PowerShell:

    $p = kubectl get secret -n monitoring monitoring-grafana -o jsonpath="{.data.admin-password}"
    [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p))

To load the dashboard in Grafana, go to Dashboards, New, Import, then upload `grafana/flask-app-dashboard.json`.

The counter `app_requests_total` only appears after the home page is requested, so send some traffic:

    1..30 | ForEach-Object { Invoke-WebRequest -UseBasicParsing http://localhost:8080/ | Out-Null }

## Known limitations and next improvements

- **Image tag.** `k8s/deployment.yaml` uses the `latest` tag, which moves. The CI pipeline already pushes a commit-SHA tag too, so the next step is to deploy that tag, which makes every deployment traceable to a commit and lets Argo CD detect new versions through Git.
- **No tests in CI.** The pipeline builds and pushes the image but does not run tests or scan the image. A test step and an image vulnerability scan would come before the push.
- **No alerting.** Alertmanager is turned off to save memory on a laptop. Next steps would be alert rules (for example, high error rate or pods not ready) and a notification channel.
- **Monitoring is not stored in Git as an Argo CD app.** The monitoring stack was installed with `helm install`. It could be managed by Argo CD as well, so the whole cluster state lives in Git.
- **Dashboard is not persistent.** Grafana keeps dashboards inside its pod, so a `helm upgrade` replaced the pod and removed the dashboard. The JSON file in `grafana/` is the backup. Provisioning the dashboard from a ConfigMap would load it automatically.
- **Local cluster.** This runs on a single-node kind cluster, so it is not highly available and Prometheus data is not kept long term.
