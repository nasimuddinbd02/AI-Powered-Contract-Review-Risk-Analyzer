"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, Loader2, RefreshCw, ShieldCheck, Trash2, UserCheck, UserX } from "lucide-react";
import { api, type ManagedUser } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export function UserManagement({ onBack }: { onBack: () => void }) {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError("");
    try {
      setUsers(await api.listUsers());
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function act(id: string, fn: () => Promise<unknown>) {
    setPending(id); setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setPending(null);
    }
  }

  const toggleRole = (u: ManagedUser) =>
    act(u.id, () => api.updateUser(u.id, { role: u.role === "admin" ? "user" : "admin" }));
  const toggleActive = (u: ManagedUser) =>
    act(u.id, () => api.updateUser(u.id, { is_active: !u.is_active }));
  const remove = (u: ManagedUser) => {
    if (confirm(`Delete ${u.email}? This cannot be undone.`)) act(u.id, () => api.deleteUser(u.id));
  };

  return (
    <div className="mx-auto max-w-5xl animate-fade-in space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2 mb-1 text-muted-foreground">
            <ArrowLeft className="h-4 w-4" /> Back to dashboard
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">User management</h1>
          <p className="text-sm text-muted-foreground">Manage accounts, roles, and access.</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} /> Refresh
        </Button>
      </div>

      {error && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Accounts ({users.length})</CardTitle>
          <CardDescription>The last remaining admin cannot be demoted or deleted.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => {
                  const isSelf = u.id === me?.id;
                  const isBusy = pending === u.id;
                  return (
                    <TableRow key={u.id}>
                      <TableCell>
                        <div className="font-medium">
                          {u.full_name} {isSelf && <span className="text-xs text-muted-foreground">(you)</span>}
                        </div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={u.role === "admin" ? "default" : "secondary"} className="gap-1">
                          {u.role === "admin" && <ShieldCheck className="h-3 w-3" />}
                          {u.role}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={u.is_active ? "low" : "high"}>{u.is_active ? "Active" : "Disabled"}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(u.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" disabled={isBusy || isSelf} onClick={() => toggleRole(u)}>
                            {u.role === "admin" ? "Demote" : "Promote"}
                          </Button>
                          <Button variant="ghost" size="icon" disabled={isBusy || isSelf} onClick={() => toggleActive(u)}
                            title={u.is_active ? "Deactivate" : "Activate"}>
                            {u.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                          </Button>
                          <Button variant="ghost" size="icon" disabled={isBusy || isSelf} onClick={() => remove(u)}
                            title="Delete" className="text-destructive hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
