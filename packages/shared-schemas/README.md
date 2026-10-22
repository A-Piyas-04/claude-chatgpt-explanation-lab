# shared-schemas

The contract shared by `apps/api` and `apps/web`.

**These files are generated.** Edit the Python source of truth, then run:

```bash
cd apps/api && python -m explanationlab.export_schemas
```

| File | Contents |
| ---- | -------- |
| `catalog.json` | Enum members, treatment definitions with their boundaries, prompt conditions, the judge rubric, the seed model catalogue with capability records, and what each evidence class means. |
| `index.ts` | TypeScript union types and typed accessors over `catalog.json`. |

Generating rather than hand-writing this means the frontend's notion of "which
treatments exist" and "which models reject `temperature`" cannot silently drift
from the backend's.
