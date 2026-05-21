{{/*
Common template helpers for the enhanced-cognee chart.
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "enhanced-cognee.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified resource name = <release>-<chart name>, capped to 63 chars.
*/}}
{{- define "enhanced-cognee.fullname" -}}
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
Chart label (used in labels.app.kubernetes.io/version).
*/}}
{{- define "enhanced-cognee.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Standard labels block.
*/}}
{{- define "enhanced-cognee.labels" -}}
helm.sh/chart: {{ include "enhanced-cognee.chart" . }}
{{ include "enhanced-cognee.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (used in Deployment + Service selectors).
*/}}
{{- define "enhanced-cognee.selectorLabels" -}}
app.kubernetes.io/name: {{ include "enhanced-cognee.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Per-component name helpers -- used so multi-DB resources don't collide.
*/}}
{{- define "enhanced-cognee.postgres.fullname" -}}
{{- printf "%s-postgres" (include "enhanced-cognee.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "enhanced-cognee.qdrant.fullname" -}}
{{- printf "%s-qdrant" (include "enhanced-cognee.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "enhanced-cognee.valkey.fullname" -}}
{{- printf "%s-valkey" (include "enhanced-cognee.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "enhanced-cognee.arcadedb.fullname" -}}
{{- printf "%s-arcadedb" (include "enhanced-cognee.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "enhanced-cognee.mcp.fullname" -}}
{{- printf "%s-mcp" (include "enhanced-cognee.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Resolve a storage tier's host. If the operator overrode the host via values,
use that; otherwise fall back to the in-chart service DNS name.
*/}}
{{- define "enhanced-cognee.storage.graphHost" -}}
{{- if .Values.storage.graph.host -}}
{{- .Values.storage.graph.host -}}
{{- else if .Values.deployments.arcadedb.enabled -}}
{{- include "enhanced-cognee.arcadedb.fullname" . -}}
{{- else -}}
{{- fail "storage.graph.host is empty and deployments.arcadedb.enabled is false -- you must either provide an external host or enable the in-chart deployment." -}}
{{- end -}}
{{- end }}

{{- define "enhanced-cognee.storage.vectorHost" -}}
{{- if .Values.storage.vector.host -}}
{{- .Values.storage.vector.host -}}
{{- else if .Values.deployments.qdrant.enabled -}}
{{- include "enhanced-cognee.qdrant.fullname" . -}}
{{- else -}}
{{- fail "storage.vector.host empty and deployments.qdrant.enabled false." -}}
{{- end -}}
{{- end }}

{{- define "enhanced-cognee.storage.cacheHost" -}}
{{- if .Values.storage.cache.host -}}
{{- .Values.storage.cache.host -}}
{{- else if .Values.deployments.valkey.enabled -}}
{{- include "enhanced-cognee.valkey.fullname" . -}}
{{- else -}}
{{- fail "storage.cache.host empty and deployments.valkey.enabled false." -}}
{{- end -}}
{{- end }}

{{- define "enhanced-cognee.storage.relationalHost" -}}
{{- if .Values.storage.relational.host -}}
{{- .Values.storage.relational.host -}}
{{- else if .Values.deployments.postgres.enabled -}}
{{- include "enhanced-cognee.postgres.fullname" . -}}
{{- else -}}
{{- fail "storage.relational.host empty and deployments.postgres.enabled false." -}}
{{- end -}}
{{- end }}
