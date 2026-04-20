// TEMPLATE: example
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { CreateItemForm } from "@/features/items/CreateItemForm";
import { ItemsList } from "@/features/items/ItemsList";

export default function Items() {
  return (
    <div className="mx-auto max-w-2xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Your items</h1>
        <Button variant="ghost" onClick={() => supabase.auth.signOut()}>
          Sign out
        </Button>
      </header>
      <div className="flex flex-col gap-6">
        <CreateItemForm />
        <ItemsList />
      </div>
    </div>
  );
}
