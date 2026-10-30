# Accodite docs path manifest

| UI | API | Notes |
|----|-----|-------|
| SheetS | sheet | 54×64 gridlines |
| DBase | xlsx | configurable C×R, multi-sheet, formula bar |
| CollabSheet | workspace | place mode; not a team room |
| Presentations | pptx | faces, 70 gradients, transitions, crop/styles |

Room header → `parent_type=room`. Home → general scope. Codespace → repo.

Placement: `GET /sandbox/gsp/place` modes standard|progressive|jump.
Lookup is lexical/token — not placement math.
