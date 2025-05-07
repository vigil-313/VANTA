# Session Protocol

This document outlines the procedure for maintaining project documentation, tracking progress, and ensuring continuity between development sessions for the VANTA project.

## #command SESSION_START

When beginning a new development session:

1. Review the PROGRESS_TRACKING.md file to understand current status
2. Note the timestamp in ISO format (YYYY-MM-DD HH:MM) for session start
3. Identify which prompt file to work on next based on progress
4. Read any STATUS_REPORT.txt from previous session (if exists)
5. Update PROGRESS_TRACKING.md with new session entry:
   ```
   ### Session X (YYYY-MM-DD HH:MM - In Progress)
   - Session goals:
     - [List primary objectives for this session]
   ```

## #command PROGRESS_UPDATE

When making significant progress during a session:

1. Update completion percentage in PROGRESS_TRACKING.md:
   - For the specific module being worked on
   - For the prompt file being addressed
   - Update "Last Updated" timestamp
2. Mark completed tasks with [x] in the detailed tracking section
3. Add any new tasks discovered during implementation
4. Update metrics at the bottom of the file

## #command NEW_MODULE

When creating a new module:

1. Update PROJECT_STRUCTURE.md if the implemented structure differs from plan
2. Add the module to PROGRESS_TRACKING.md if not already listed
3. Ensure the module follows the established architecture patterns
4. Document any architecture decisions that deviate from original plan

## #command SESSION_END

When concluding a development session:

1. Create or update STATUS_REPORT.txt with:
   ```
   Session: X (YYYY-MM-DD)
   Duration: HH:MM - HH:MM
   
   Completed:
   - [List of completed tasks/files]
   
   In Progress:
   - [List of tasks started but not completed]
   
   Next Steps:
   - [List of immediate next tasks for next session]
   
   Blockers:
   - [Any issues blocking progress]
   ```
2. Update PROGRESS_TRACKING.md session entry with end timestamp
3. Update PROGRESS_TRACKING.md overall project completion percentage
4. Log any TODOs or placeholders that need addressing in future sessions
5. Commit progress to version control if applicable

## Documentation Standards

- **Code Comments**: Focused on "why" not "what"
- **Module Documentation**: Each module has a docstring explaining purpose and usage
- **Architecture Decisions**: Recorded in PROGRESS_TRACKING.md
- **TODOs**: Marked in code with format: `# TODO: [description] [YYYY-MM-DD]`

## Prompt Handling

1. Each prompt file should be worked on sequentially
2. When starting a new prompt file, mark it as "In Progress" in PROGRESS_TRACKING.md
3. When completing a prompt file, mark it as "Completed" with 100% and timestamp
4. Log completed files from each prompt in progress_log.txt:
   ```
   [YYYY-MM-DD HH:MM] Completed files for [prompt_file_name]:
   - [file_path_1]
   - [file_path_2]
   ...
   ```

## Versioning

- Record significant version milestones in PROGRESS_TRACKING.md
- Format: v0.X.Y where:
  - X increments for each completed prompt file
  - Y increments for significant progress within a prompt file

## Example Protocol Usage

```
#command SESSION_START
{"session_number": 2, "timestamp": "2025-05-08 09:30", "prompt_file": "02_voice_pipeline_core_loop.txt"}
```

```
#command PROGRESS_UPDATE
{"module": "Voice Pipeline", "completion": 40, "tasks_completed": ["microphone.py", "vad.py"]}
```

```
#command SESSION_END
{"session_number": 2, "end_timestamp": "2025-05-08 12:45", "overall_completion": 15}
```