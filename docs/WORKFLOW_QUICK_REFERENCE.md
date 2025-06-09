# Quick Reference: Development Workflow

## The Golden Rule
**Add to TODO.md BEFORE doing ANY work**

## Four-Step Process

### 1. 📋 PLAN
```markdown
- [ ] **[Task Name]**: Description
  - [ ] Subtask 1
  - [ ] Test step
  - [ ] Documentation update
```

### 2. 📝 DOCUMENT
- Update README if needed
- Create/update docs/ files
- Note configuration changes

### 3. ⚙️ EXECUTE
- Follow project standards
- Test changes locally
- Use proper tools (make, npm scripts)

### 4. ✅ VERIFY
- Check functionality works
- Update documentation
- Commit with descriptive message
- Mark TODO complete

## Quick Commands

```bash
# Setup new environment
make setup

# Check what's available
make help

# Before starting work
git status
git pull origin develop
```

## Commit Format
```
[Type]: [Summary]

- [Change 1] 
- Mark TODO item as complete
```

## Documentation Locations
- `README.md` - Overview and quick start
- `docs/` - Detailed guides (all must be linked in README)
- `TODO.md` - Current work and planning
- Code comments - Complex logic

## Approval Required For
- [ ] Significant features
- [ ] Process changes  
- [ ] External integrations
- [ ] Large refactoring

## Red Flags
- ❌ Starting work without TODO entry
- ❌ Missing documentation updates
- ❌ Broken links in README
- ❌ Uncommitted changes
- ❌ No testing performed

## Success Indicators
- ✅ All docs linked in README
- ✅ TODO accurately reflects progress
- ✅ Changes work as expected
- ✅ Documentation stays current
- ✅ Clear commit history

---
**See [Development Workflow](DEVELOPMENT_WORKFLOW.md) for complete details**
