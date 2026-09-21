# skill_manage_system Instructions

## Goal
Act as the "operating system" for Agent skills: discover, pack interfaces, connect context, dispatch, and create skills when missing.

## SMS Home
env `SMS_HOME` -> user cache dir (Windows `%LOCALAPPDATA%`, macOS `~/Library/Caches`, Linux `~/.cache`) -> user home; create `SMS/`.

## Workflow
1. Resolve SMS_HOME; read `SMS/registry/register.json`.
2. Missing -> initial setup: skill_register -> skill_packer -> skill_connector.
3. Present -> detect intent; create `SMS/sessions/<date>/` five-tuple.
4. Decompose/integrate the task; run 5 concurrent lanes; register process lifecycle; gate by permissions.
5. Use register + interfaces + connections to dispatch the target skill (inject its SKILL.md).
6. No match -> delegate to Skill_Generator -> re-register via skill_register.

## Sub-skills
- skill_register: locations + tools -> register.json
- skill_packer: interfaces + purpose -> interfaces.json
- skill_connector: context chains -> connections.json
- skill_scheduler: decompose/integrate + concurrent lanes + process lifecycle + permission gating

## Constraints
- Never delete resistance/; keep runtime SMS data out of the skill source.
- Orphan links = 0; markdown/scripts <= 50 lines; SKILL.md has YAML frontmatter.
- Write session tuple + process table before dispatch; data writes go through the emit gate and require the granted `write`; deny ungranted actions with audit.

## Start
Wait for a request, read SKILL.md, begin at "resolve SMS_HOME".