// TEMPLATE: example
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Form, FormField, FormLabel, FormError } from "@/components/ui/form";
import { useCreateItem } from "@/features/items/hooks";

export function CreateItemForm() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const create = useCreateItem();

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate(
      { name: name.trim(), description: description.trim() || null },
      {
        onSuccess: () => {
          setName("");
          setDescription("");
        },
      },
    );
  };

  return (
    <Form onSubmit={onSubmit} className="rounded-lg border border-border p-4">
      <FormField>
        <FormLabel htmlFor="name">Name</FormLabel>
        <Input
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
        />
      </FormField>
      <FormField>
        <FormLabel htmlFor="description">Description (optional)</FormLabel>
        <Input
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={2000}
        />
      </FormField>
      {create.error ? <FormError>{String(create.error)}</FormError> : null}
      <Button type="submit" disabled={create.isPending}>
        {create.isPending ? "Creating…" : "Create item"}
      </Button>
    </Form>
  );
}
