# Cognito Module - Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "callback_urls" {
  description = "Allowed callback URLs"
  type        = list(string)
  default     = ["http://localhost:3000/callback"]
}

variable "logout_urls" {
  description = "Allowed logout URLs"
  type        = list(string)
  default     = ["http://localhost:3000"]
}

# Google OIDC
variable "enable_google" {
  description = "Enable Google SSO"
  type        = bool
  default     = false
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  default     = ""
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

# Okta OIDC
variable "enable_okta" {
  description = "Enable Okta SSO"
  type        = bool
  default     = false
}

variable "okta_client_id" {
  description = "Okta OAuth client ID"
  type        = string
  default     = ""
}

variable "okta_client_secret" {
  description = "Okta OAuth client secret"
  type        = string
  sensitive   = true
  default     = ""
}

variable "okta_issuer_url" {
  description = "Okta issuer URL"
  type        = string
  default     = ""
}

# SAML
variable "enable_saml" {
  description = "Enable SAML SSO"
  type        = bool
  default     = false
}

variable "saml_metadata_url" {
  description = "SAML IdP metadata URL"
  type        = string
  default     = ""
}

variable "saml_provider_name" {
  description = "SAML provider name"
  type        = string
  default     = "Enterprise"
}

variable "saml_slo_url" {
  description = "SAML Single Logout URL"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
