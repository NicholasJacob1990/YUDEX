{{/*
Harvey Backend - Helm Templates
Common labels and functions
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "harvey-backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "harvey-backend.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "harvey-backend.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "harvey-backend.labels" -}}
helm.sh/chart: {{ include "harvey-backend.chart" . }}
{{ include "harvey-backend.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/component: api
app.kubernetes.io/part-of: harvey-backend
{{- end }}

{{/*
Selector labels
*/}}
{{- define "harvey-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "harvey-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "harvey-backend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "harvey-backend.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Create the name of the secret
*/}}
{{- define "harvey-backend.secretName" -}}
{{- printf "%s-secrets" (include "harvey-backend.fullname" .) }}
{{- end }}

{{/*
Create the name of the configmap
*/}}
{{- define "harvey-backend.configMapName" -}}
{{- printf "%s-config" (include "harvey-backend.fullname" .) }}
{{- end }}

{{/*
Create environment variables
*/}}
{{- define "harvey-backend.env" -}}
- name: ENVIRONMENT
  value: {{ .Values.environment | quote }}
- name: LOG_LEVEL
  value: {{ .Values.logging.level | quote }}
- name: LOG_FORMAT
  value: {{ .Values.logging.format | quote }}
- name: METRICS_ENABLED
  value: {{ .Values.metrics.enabled | quote }}
- name: TZ
  value: {{ .Values.timezone | quote }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: database_url
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: redis_url
- name: QDRANT_URL
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: qdrant_url
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: openai_api_key
- name: ANTHROPIC_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: anthropic_api_key
- name: GOOGLE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: google_api_key
- name: JWT_SECRET
  valueFrom:
    secretKeyRef:
      name: {{ include "harvey-backend.secretName" . }}
      key: jwt_secret
{{- end }}

{{/*
Create resource requirements
*/}}
{{- define "harvey-backend.resources" -}}
{{- if .Values.resources }}
resources:
  {{- if .Values.resources.requests }}
  requests:
    {{- if .Values.resources.requests.cpu }}
    cpu: {{ .Values.resources.requests.cpu | quote }}
    {{- end }}
    {{- if .Values.resources.requests.memory }}
    memory: {{ .Values.resources.requests.memory | quote }}
    {{- end }}
  {{- end }}
  {{- if .Values.resources.limits }}
  limits:
    {{- if .Values.resources.limits.cpu }}
    cpu: {{ .Values.resources.limits.cpu | quote }}
    {{- end }}
    {{- if .Values.resources.limits.memory }}
    memory: {{ .Values.resources.limits.memory | quote }}
    {{- end }}
  {{- end }}
{{- end }}
{{- end }}

{{/*
Create security context
*/}}
{{- define "harvey-backend.securityContext" -}}
{{- if .Values.containerSecurityContext.enabled }}
securityContext:
  runAsNonRoot: {{ .Values.containerSecurityContext.runAsNonRoot }}
  runAsUser: {{ .Values.containerSecurityContext.runAsUser }}
  runAsGroup: {{ .Values.containerSecurityContext.runAsGroup }}
  allowPrivilegeEscalation: {{ .Values.containerSecurityContext.allowPrivilegeEscalation }}
  readOnlyRootFilesystem: {{ .Values.containerSecurityContext.readOnlyRootFilesystem }}
  capabilities:
    drop:
      {{- range .Values.containerSecurityContext.capabilities.drop }}
      - {{ . }}
      {{- end }}
{{- end }}
{{- end }}
