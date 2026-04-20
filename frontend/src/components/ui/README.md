# shadcn/ui components

Only the components used by the `items` example are committed here:

- `button.tsx`
- `input.tsx`
- `card.tsx`
- `form.tsx` (minimal — swap in shadcn's react-hook-form flavor when needed)
- `toast.tsx` (minimal — swap in `sonner` when you need real queues)

When you need another component:

```bash
make shadcn-add NAME=dropdown-menu
```

This wraps the pinned shadcn CLI version (see `DEPENDENCIES.md`). The added
component lands in this directory and can be edited freely — shadcn is a code
generator, not a runtime dependency.
