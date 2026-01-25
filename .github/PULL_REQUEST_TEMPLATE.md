## Description

<!-- Provide a clear and concise description of your changes -->

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🎨 Code style/formatting update
- [ ] ♻️ Refactoring (no functional changes)
- [ ] 🧪 Test improvements
- [ ] 🔧 Configuration changes
- [ ] 🐳 Docker/deployment changes

## Motivation and Context

<!-- Why is this change required? What problem does it solve? -->
<!-- If it fixes an open issue, please link to the issue here using "Closes #123" -->

## Changes Made

<!-- List the specific changes in this PR -->

-
-
-

## Testing

<!-- Describe the tests you ran to verify your changes -->
<!-- Include instructions so maintainers can reproduce the tests -->

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All existing tests pass

### Test Commands Run

```bash
# Example:
# python -m pytest tests/unit/test_new_feature.py -v
# python -m pytest tests/ --cov=app
```

### Test Scenarios

<!-- Describe specific test scenarios you verified -->

1.
2.
3.

## Quality Checklist

<!-- Ensure your PR meets our quality standards -->

### Code Quality

- [ ] Code follows the project's style guidelines
- [ ] Code has been formatted with Black (`black app/ tests/`)
- [ ] Pylint score is 9.5+ (`pipx run pylint app/*.py --rcfile=.pylintrc`)
- [ ] No new security issues introduced (`pipx run bandit -r app/`)
- [ ] No new dependency vulnerabilities

### Testing

- [ ] Test coverage is ≥50% overall
- [ ] New code has corresponding tests
- [ ] All tests pass locally (`pytest tests/ --cov=app`)
- [ ] Manual testing completed successfully

### Documentation

- [ ] Code changes are self-documenting with clear variable/function names
- [ ] Docstrings added/updated for public functions
- [ ] Comments added for complex logic (only where necessary)
- [ ] README.md updated (if needed)
- [ ] Documentation updated (if needed)
- [ ] CLAUDE.md updated (if workflow changes affect development)

### Configuration

- [ ] `.env.template` updated (if new environment variables added)
- [ ] Configuration documented in relevant files
- [ ] Backward compatible (or breaking changes clearly documented)

## Breaking Changes

<!-- If this PR introduces breaking changes, describe them here -->
<!-- Include migration steps for users -->

- [ ] This PR includes breaking changes
- [ ] Migration guide provided

<!-- If no breaking changes, you can delete this section -->

## Screenshots/Examples

<!-- If applicable, add screenshots or examples to demonstrate the changes -->
<!-- For API changes, include example requests/responses -->
<!-- For UI changes, include before/after screenshots -->

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No significant performance impact
- [ ] Performance improved (describe how)
- [ ] Performance impact acceptable (explain why)

<!-- If performance testing was done, include results -->

## Deployment Notes

<!-- Any special instructions for deployment? -->
<!-- Does this require specific configuration changes? -->
<!-- Are there any dependencies that need to be updated? -->

## Checklist

<!-- Final checks before submitting -->

- [ ] My code follows the contribution guidelines in CONTRIBUTING.md
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code where necessary and in complex areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published
- [ ] I have checked my code and corrected any misspellings
- [ ] I have read and agree to follow the Code of Conduct

## Additional Context

<!-- Add any other context, considerations, or information about the PR -->
<!-- Link to relevant discussions, RFCs, or external references -->

## Post-Merge Tasks

<!-- Are there any follow-up tasks after this is merged? -->

- [ ] Update related issues
- [ ] Notify users of breaking changes (if any)
- [ ] Update deployment documentation (if needed)
- [ ] Monitor production for issues (if applicable)

---

**Building better DNS security, one LEGO brick at a time.** 🧱✨

<!-- Thank you for contributing to DNSSEC Validator! -->
