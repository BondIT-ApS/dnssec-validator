# Safety CLI Configuration

This directory contains Safety CLI security scanning configuration for the DNSSEC Validator project.

## Files Overview

All Safety CLI configuration files are located in the `.safety/` directory:

- **`.safety-project.ini`** - Links this repository to the Safety Platform project
- **`.safety-policy.yml`** - Local policy file for security scanning
- **`README.md`** - This documentation file

## Policy Hierarchy

Safety CLI v3 uses the following policy precedence (highest to lowest):

1. **Safety Platform Policy** (when authenticated) - fetched from https://platform.safetycli.com
2. **Local Policy File** (`.safety-policy.yml`) - used as fallback or when `--policy-file` flag is used
3. **Default Safety Policies** - built-in defaults

## Current Configuration

### Safety Platform
- **Project**: dnssec-validator
- **URL**: https://platform.safetycli.com/codebases/dnssec-validator/findings
- **Account**: martin@bondit.dk

### Security Policy
The policy is configured to:
- ✅ **Fail on CRITICAL and HIGH severity** vulnerabilities
- ✅ **Scan virtual environments** (do not ignore environment-results)
- ✅ **Scan unpinned requirements** (do not ignore requirements with `>=`)
- ⚠️ **Warn on MEDIUM and LOW** severity (but don't fail)

## Running Safety Scans

### Local Development
```bash
# Basic scan (uses development environment by default)
safety scan

# Scan for production readiness
SAFETY_STAGE=production safety scan

# Detailed output
safety scan --detailed-output

# Use local policy file (override platform policy)
safety scan --policy-file .safety/.safety-policy.yml
```

### CI/CD (GitHub Actions)
Safety scans run automatically on every PR via the Quality Gate workflow.

## Updating the Policy

### Option 1: Update Platform Policy (Recommended)
1. Go to https://platform.safetycli.com/codebases/dnssec-validator/findings
2. Navigate to Settings → Policy
3. Update the JSON policy configuration
4. Changes apply immediately to all scans

### Option 2: Update Local Policy File
1. Edit `.safety/.safety-policy.yml` in the repository
2. Commit and push changes
3. To use: run `safety scan --policy-file .safety/.safety-policy.yml`

**Note**: Platform policy takes precedence over local policy when authenticated.

## Ignoring Specific Vulnerabilities

To ignore a specific vulnerability (use sparingly):

1. **Platform Policy**: Add to `report.dependency-vulnerabilities.auto-ignore-in-report.vulnerabilities`
2. **Local Policy**: Add to `.safety-policy.yml` under `report.dependency-vulnerabilities.auto-ignore-in-report.vulnerabilities`

Example:
```yaml
vulnerabilities:
  "12345":
    reason: "False positive - we don't use the vulnerable component"
    expires: "2026-12-31"
```

## Troubleshooting

### "15 vulnerabilities found, 15 ignored due to policy"
This means the Safety Platform policy is set to auto-ignore vulnerabilities. Check:
- `environment-results: true` → should be `false`
- `unpinned-requirements: true` → should be `false`

### Force Local Policy
To bypass platform policy and use local policy:
```bash
safety scan --policy-file .safety/.safety-policy.yml
```

### Environment Configuration
Safety CLI detects the environment automatically. To scan for production readiness:
```bash
# Set environment to production
SAFETY_STAGE=production safety scan

# Or set it permanently in your CI/CD
export SAFETY_STAGE=production
safety scan
```

Available environments:
- `development` (default for local scans)
- `production` (for production-ready scans)
- `staging` (for staging environment)

## Resources
- [Safety CLI Documentation](https://docs.safetycli.com/)
- [Safety Platform](https://platform.safetycli.com/)
- [Policy File Documentation](https://docs.safetycli.com/safety-docs/safety-3.0/policy-file)
