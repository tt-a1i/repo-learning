# Repository investigation checklist

Use this as a guide, not a form to fill. The final website should contain only
the parts that help someone understand the repository.

## Establish the project story

- Read README, contribution, agent instruction and architecture documents.
- Identify the problem, audience, primary use case and current project phase.
- Write one concrete tagline and a short mental model.
- Record uncertainty instead of filling gaps with generic prose.

## Find the system skeleton

- Locate manifests, package roots, executable entrypoints and deployment files.
- Group directories into a small number of meaningful modules.
- Trace imports and calls before drawing connections.
- Select architecture layers based on the project, not a fixed taxonomy.

## Trace representative flows

- Choose one to three flows that reveal how the system really works.
- Start from an external trigger: HTTP, CLI, job, webhook, event or build command.
- Follow the path through domain logic, persistence and side effects.
- Capture async boundaries, retries, trust boundaries and failure states.

## Learn the project language

- Find model names, public types, database concepts and user-facing terminology.
- Explain concepts in plain language and say why each one matters.
- Prefer project-specific concepts over framework vocabulary.

## Build a code-entry map

- Pick files that unlock the architecture or a representative flow.
- Explain what each file teaches and when to read it.
- Avoid exhaustive directory listings and raw LOC statistics.

## Establish the contributor path

- Read documented install and development commands without automatically running them.
- Order the learning path by understanding outcomes.
- Include tests that demonstrate important behavior.
- Surface missing environment, deployment or operational context as gaps.

## Quality check before generation

- Can the tagline explain the project without marketing filler?
- Does every architecture arrow come from a real call, import or data transfer?
- Does at least one flow reach a real result or side effect?
- Are concepts understandable without reading their implementation first?
- Can a new contributor tell which file to open next?
- Are important unknowns visible?
