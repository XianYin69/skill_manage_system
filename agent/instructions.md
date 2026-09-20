# skill_manage_system Instructions

## Goal
Act as the "operating system" for Agent skills: discover, pack interfaces, connect context, dispatch, and create skills when missing.

## SMS Home
env `SMS_HOME` -> user cache dir (Windows `%LOCALAPPDATA%`, macOS `~/Library/Caches`, Linux `~/.cache`) -> user home; create `SMS/`.

## Workflow
1. Resolve SMS_HOME; read `SMS/registry/register.json`.
2. Missing -> initial setup: skill_register -> skill_packer -> skill_connector.
3. Present -> detect intent; create `SMS/sessions/<date>/` five-tuple.
4. Use register + interfaces + connections to dispatch the target skill (inject its SKILL.md).
5. No match -> delegate to Skill_Generator -> re-register via skill_register.

## Sub-skills
- skill_register: locations + tools -> register.json
- skill_packer: interfaces + purpose -> interfaces.json
- skill_connector: context chains -> connections.json

## Constraints
- Never delete resistance/; keep runtime SMS data out of the skill source.
- Orphan links = 0; markdown/scripts <= 50 lines; SKILL.md has YAML frontmatter.
- Write session tuple before dispatch; writes default to `--dry-run`; deny ungranted actions.

## Start
Wait for a request, read SKILL.md, begin at "resolve SMS_HOME".