{{- define "sird-ocr.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sird-ocr.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- include "sird-ocr.name" . }}
{{- end }}
{{- end }}

{{- define "sird-ocr.labels" -}}
app.kubernetes.io/name: {{ include "sird-ocr.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end }}

{{- define "sird-ocr.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sird-ocr.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
