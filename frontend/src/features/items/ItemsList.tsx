// TEMPLATE: example
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useItems } from "@/features/items/hooks";

export function ItemsList() {
  const { data, isLoading, error } = useItems();

  if (isLoading) return <p className="text-muted-foreground">Loading items…</p>;
  if (error) return <p className="text-destructive">Failed to load: {String(error)}</p>;
  if (!data || data.length === 0) {
    return <p className="text-muted-foreground">No items yet. Create your first one above.</p>;
  }

  return (
    <div className="grid gap-3">
      {data.map((item) => (
        <Card key={item.id}>
          <CardHeader>
            <CardTitle>{item.name}</CardTitle>
          </CardHeader>
          <CardContent>
            {item.description ?? <span className="italic">No description</span>}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
