# Cognito Module - User Authentication

# =============================================================================
# USER POOL
# =============================================================================

resource "aws_cognito_user_pool" "main" {
  name = "${var.name_prefix}-users"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "GenAI Observability - Verify your email"
    email_message        = "Your verification code is {####}"
  }

  schema {
    name                     = "email"
    attribute_data_type      = "String"
    required                 = true
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 256
    }
  }

  schema {
    name                     = "team_id"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 256
    }
  }

  schema {
    name                     = "role"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 0
      max_length = 50
    }
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-users"
  })
}

# =============================================================================
# USER POOL DOMAIN
# =============================================================================

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.name_prefix}-${random_id.domain_suffix.hex}"
  user_pool_id = aws_cognito_user_pool.main.id
}

resource "random_id" "domain_suffix" {
  byte_length = 4
}

# =============================================================================
# USER POOL CLIENT
# =============================================================================

resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.name_prefix}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  supported_identity_providers = concat(
    ["COGNITO"],
    var.enable_google ? ["Google"] : [],
    var.enable_okta ? ["Okta"] : [],
    var.enable_saml ? [var.saml_provider_name] : []
  )

  callback_urls = var.callback_urls
  logout_urls   = var.logout_urls

  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  access_token_validity  = 1
  id_token_validity      = 1
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }

  prevent_user_existence_errors = "ENABLED"

  depends_on = [
    aws_cognito_identity_provider.google,
    aws_cognito_identity_provider.okta,
    aws_cognito_identity_provider.saml
  ]
}

# =============================================================================
# IDENTITY PROVIDERS
# =============================================================================

# Google
resource "aws_cognito_identity_provider" "google" {
  count = var.enable_google ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Google"
  provider_type = "Google"

  provider_details = {
    client_id        = var.google_client_id
    client_secret    = var.google_client_secret
    authorize_scopes = "profile email openid"
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
    name     = "name"
  }
}

# Okta (OIDC)
resource "aws_cognito_identity_provider" "okta" {
  count = var.enable_okta ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "Okta"
  provider_type = "OIDC"

  provider_details = {
    client_id                     = var.okta_client_id
    client_secret                 = var.okta_client_secret
    authorize_scopes              = "profile email openid"
    oidc_issuer                   = var.okta_issuer_url
    attributes_request_method     = "GET"
    attributes_url_add_attributes = false
  }

  attribute_mapping = {
    email    = "email"
    username = "sub"
    name     = "name"
  }
}

# SAML
resource "aws_cognito_identity_provider" "saml" {
  count = var.enable_saml ? 1 : 0

  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = var.saml_provider_name
  provider_type = "SAML"

  provider_details = {
    MetadataURL           = var.saml_metadata_url
    SLORedirectBindingURI = var.saml_slo_url
    IDPSignout            = var.saml_slo_url != "" ? "true" : "false"
  }

  attribute_mapping = {
    email = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    name  = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
  }
}

# =============================================================================
# IDENTITY POOL (for AWS credentials)
# =============================================================================

resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.name_prefix}-identity"
  allow_unauthenticated_identities = false

  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.main.id
    provider_name           = aws_cognito_user_pool.main.endpoint
    server_side_token_check = false
  }

  tags = var.tags
}

# =============================================================================
# IDENTITY POOL ROLES
# =============================================================================

resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    authenticated = aws_iam_role.authenticated.arn
  }
}

resource "aws_iam_role" "authenticated" {
  name = "${var.name_prefix}-cognito-authenticated"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy" "authenticated" {
  name = "${var.name_prefix}-cognito-authenticated"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cognito-sync:*",
          "cognito-identity:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# =============================================================================
# USER GROUPS
# =============================================================================

resource "aws_cognito_user_group" "admin" {
  name         = "admin"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Administrators with full access"
  precedence   = 1
}

resource "aws_cognito_user_group" "user" {
  name         = "user"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Standard users"
  precedence   = 10
}

resource "aws_cognito_user_group" "viewer" {
  name         = "viewer"
  user_pool_id = aws_cognito_user_pool.main.id
  description  = "Read-only viewers"
  precedence   = 20
}
