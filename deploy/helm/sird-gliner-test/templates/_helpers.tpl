{{- define "sird-gliner-test.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sird-gliner-test.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- include "sird-gliner-test.name" . }}
{{- end }}
{{- end }}

{{- define "sird-gliner-test.labels" -}}
app.kubernetes.io/name: {{ include "sird-gliner-test.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "sird-gliner-test.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sird-gliner-test.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
