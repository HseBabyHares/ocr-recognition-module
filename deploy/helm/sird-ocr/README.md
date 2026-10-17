# sird-ocr

gRPC `sird.ocr.v1 OcrService` on port 50051 for sird-process-service.

## Image

`.github/workflows/sird-ocr-image.yml` publishes
`ghcr.io/hsebabyhares/sird-ocr:sha-<commit>` and `:<branch>` on every push
that changes the image inputs. The package is private.

## Install

```bash
kubectl create secret docker-registry ghcr-pull --docker-server=ghcr.io \
  --docker-username=<github-user> --docker-password=<token with read:packages>

kubectl create secret generic sird-ocr \
  --from-literal=CAPABILITY_KEYS=v1-k1:<64 hex, same as Process CAPABILITY_KEY> \
  --from-literal=S3_ACCESS_KEY=<key> --from-literal=S3_SECRET_KEY=<secret>

helm install sird-ocr deploy/helm/sird-ocr \
  --set image.tag=sha-<commit> \
  --set imagePullSecrets[0].name=ghcr-pull \
  --set existingSecret=sird-ocr \
  --set storage.endpoint=http://<s3-host>:9000 \
  --set storage.bucket=<bucket of sird-task-service>
```

## sird-process-service settings

| Variable | Value |
|---|---|
| `OCR_TARGET` | `sird-ocr.<namespace>.svc:50051` |
| `OCR_PLAINTEXT` | `true` unless `tls.secretName` is set |
| `OCR_CONTRACT_VERSION` | `sird.ocr.v1` |
| `CAPABILITY_KEY_ID` / `CAPABILITY_KEY` | `v1-k1` / the hex in `CAPABILITY_KEYS` |
| `CAPABILITY_ISSUER` / `CAPABILITY_AUDIENCE` | `capability.issuer` / `capability.audience` |
| `OCR_INPUT_POLICY_ID` | `server.policyId` |

Process must sign the `object_key` claim (sird-process-service branch
`fix/task-contract`). Without it OCR refuses every capability.

The `networkPolicy.ingressFrom` default admits pods labelled
`app.kubernetes.io/name: sird-process-service`; change it to match the
Process deployment labels.
