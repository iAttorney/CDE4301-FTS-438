# Repository Formatting & Editing Rules

## HTML Formatting (Mandatory)
- **Never output minified or single-line HTML.** Always format markup across multiple lines using 2-space indentation.
- Keep one block-level element (`<div>`, `<section>`, `<p>`, `<li>`, etc.) per line so diffs remain clean and readable.
- After editing any `.html` file, always run `npx prettier "**/*.html" --write` before finishing your turn.

## Git & Verification Workflow
- Before making edits, check `git status` to confirm a clean working tree.
- Do not create `.zip` archives or duplicate backup files inside the repository.
- Before finishing, verify that no lines exceed standard Prettier formatting and that all tags are properly closed.
