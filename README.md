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
    rancher-fleet-secrets.deltachaos.de/replicate: some-key:some-copy,someother-key
type: Opaque
data:
  some-key: some-value
  someother-key: someother-value
  foo: bar
```

This will replicate the values from the secret as annotations to the Rancher Fleet Cluster Resource:

```yaml
kind: Cluster
metadata:
  annotations:
    rancher-fleet-secrets.deltachaos.de/secret/some-copy: some-value
    rancher-fleet-secrets.deltachaos.de/secret/someother-key: someother-value
```
