# rancher-fleet-secrets-annotater
Replicates secret values to rancher fleet cluster resource annotations

# How to use?

Add the Annotation to your secrets:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  annotations:
    rancher-fleet-secrets.alpha.deltachaos.de/replicate: some-key=some-copy,someother-key
    rancher-fleet-secrets.alpha.deltachaos.de/clusters: fleet-local/*,fleet-default/cluster1
type: Opaque
stringData:
  some-key: some-value
  someother-key: someother-value
  foo: bar
---
apiVersion: v1
kind: Secret
metadata:
  name: my-other-secret
  annotations:
    rancher-fleet-secrets.alpha.deltachaos.de/replicate: other-secret-key
type: Opaque
stringData:
  other-secret-key: test
```

This will replicate the values from the secret as annotations to the Rancher Fleet Cluster Resource:

```yaml
kind: Cluster
metadata:
  name: cluster1
  namespace: fleet-default
  annotations:
    rancher-fleet-secrets-secret.deltachaos.de/other-secret-key: test
---
kind: Cluster
metadata:
  name: cluster2
  namespace: fleet-default
  annotations:
    rancher-fleet-secrets-secret.deltachaos.de/some-copy: some-value
    rancher-fleet-secrets-secret.deltachaos.de/someother-key: someother-value
    rancher-fleet-secrets-secret.deltachaos.de/other-secret-key: test
---
kind: Cluster
metadata:
  name: cluster3
  namespace: fleet-local
  annotations:
    rancher-fleet-secrets-secret.deltachaos.de/some-copy: some-value
    rancher-fleet-secrets-secret.deltachaos.de/someother-key: someother-value
    rancher-fleet-secrets-secret.deltachaos.de/other-secret-key: test
```

# Why is it useful?

If you use Rancher fleet to deploy charts to your cluster, you maybe not want to store secrets in your Git repository. If you get some secrets into your local Rancher cluster using `external-secrets-operator` or `sealed-secrets` you can then use them in your fleet deployments like so:

```yaml
helm:
  chart: oci://registry-1.docker.io/bitnamicharts/mysql
  version: 11.1.10
  releaseName: mysql
  values:
    auth:
      rootPassword: ${ get .ClusterAnnotations "rancher-fleet-secrets.deltachaos.de/secret/some-copy" }
```

# Installation 

## Dependencies

This project is meant to be installed into a Rancher cluster.

## Helm

Install the helm Chart in this repository to your Rancher cluster. If you are using fleet, you can install the Helm
chart with this `fleet.yaml`.

```yaml
defaultNamespace: external-secrets-rso

helm:
  chart: git::https://github.com/Deltachaos/rancher-fleet-secrets-annotater//helm/rancher-fleet-secrets-annotater?ref=main
  version: 0.1.0
