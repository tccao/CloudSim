---
description: Git workflow for feature development, commits, and pull requests
---

# CloudSim Git Workflow

Standard git workflow simulating a professional software engineering team.

## Branch Naming Convention

```
feature/   - New features (feature/add-vpc-support)
fix/       - Bug fixes (fix/login-redirect)
docs/      - Documentation only (docs/update-readme)
refactor/  - Code refactoring (refactor/api-client)
chore/     - Maintenance tasks (chore/update-dependencies)
```

## Workflow Steps

### 1. Start a New Feature
```bash
# Make sure you're on main and up to date
git checkout main
git pull origin main

# Create and switch to feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Commits (Atomic, Focused)
```bash
# Stage specific files
git add path/to/file.ts

# Or stage all changes
git add .

# Commit with conventional commit message
git commit -m "type: short description"
```

### Commit Message Format
```
type: short description (max 50 chars)

[optional body - explain WHY, not WHAT]

[optional footer - references issues]
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring (no feature change)
- `style:` - Formatting, whitespace
- `test:` - Adding tests
- `chore:` - Maintenance, dependencies

**Examples:**
```bash
git commit -m "feat: Add VPC configuration to instance creation"
git commit -m "fix: Resolve token expiration redirect loop"
git commit -m "docs: Add curl examples to API client"
git commit -m "refactor: Reorganize API client into sections"
```

### 3. Push Branch to Remote
```bash
git push -u origin feature/your-feature-name
```

### 4. Create Pull Request (GitHub)
```bash
# Open GitHub to create PR (or use gh CLI)
# Title: Same format as commit messages
# Description: What, Why, How, Testing

# Using GitHub CLI (if installed):
gh pr create --title "feat: Add VPC support" --body "Description here"
```

### 5. After PR is Merged
```bash
# Switch back to main
git checkout main

# Pull the merged changes
git pull origin main

# Delete the local feature branch
git branch -d feature/your-feature-name

# Delete remote branch (usually done automatically by GitHub)
git push origin --delete feature/your-feature-name
```

## Quick Commands Reference

| Action | Command |
|--------|---------|
| Check status | `git status` |
| View changes | `git diff` |
| Stage file | `git add <file>` |
| Unstage file | `git restore --staged <file>` |
| Discard changes | `git restore <file>` |
| View commit history | `git log --oneline -10` |
| Create branch | `git checkout -b <name>` |
| Switch branch | `git checkout <name>` |
| Push branch | `git push -u origin <name>` |

## Best Practices

1. **Commit often** - Small, focused commits are easier to review
2. **Pull before push** - Avoid merge conflicts
3. **One feature per branch** - Keep PRs focused
4. **Write meaningful messages** - Future you will thank you
5. **Review your own diff** - Before committing, check `git diff`
