import { Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import SignIn from "@/pages/SignIn";
import Items from "@/pages/Items";
import type { Session } from "@supabase/supabase-js";

export default function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (session === undefined) {
    return <div className="p-8 text-muted-foreground">Loading…</div>;
  }

  return (
    <Routes>
      <Route path="/signin" element={session ? <Navigate to="/" /> : <SignIn />} />
      <Route path="/" element={session ? <Items /> : <Navigate to="/signin" />} />
      <Route path="*" element={<Navigate to={session ? "/" : "/signin"} />} />
    </Routes>
  );
}
