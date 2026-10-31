import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';

export const UsersPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: api.getUsers,
    enabled: !!user?.is_admin,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { is_admin?: boolean; is_active?: boolean } }) =>
      api.updateUser(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteUser(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });

  if (!user?.is_admin) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">
        Admin privileges required.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">User Management</h1>
        <p className="mt-1 text-sm text-slate-400">Manage accounts and roles (admin only).</p>
      </div>

      {isLoading && <p className="text-slate-400">Loading...</p>}

      <div className="overflow-x-auto rounded-xl border border-[#1f2433] bg-[#0c0e16]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1f2433] text-left text-xs text-slate-400">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Email</th>
              <th className="px-4 py-3">Admin</th>
              <th className="px-4 py-3">Active</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users?.map((u) => (
              <tr key={u.id} className="border-b border-[#1f2433]/60">
                <td className="px-4 py-3 text-slate-300">{u.id}</td>
                <td className="px-4 py-3 text-slate-100">{u.email}</td>
                <td className="px-4 py-3">
                  <button
                    disabled={u.id === user.id}
                    onClick={() =>
                      updateMutation.mutate({ id: u.id, payload: { is_admin: !u.is_admin } })
                    }
                    className={`rounded px-2 py-1 text-xs font-semibold ${
                      u.is_admin ? 'bg-indigo-600/30 text-indigo-200' : 'bg-slate-700/40 text-slate-300'
                    }`}
                  >
                    {u.is_admin ? 'Yes' : 'No'}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <button
                    disabled={u.id === user.id}
                    onClick={() =>
                      updateMutation.mutate({ id: u.id, payload: { is_active: !u.is_active } })
                    }
                    className={`rounded px-2 py-1 text-xs font-semibold ${
                      u.is_active ? 'bg-emerald-600/30 text-emerald-200' : 'bg-red-600/30 text-red-200'
                    }`}
                  >
                    {u.is_active ? 'Yes' : 'No'}
                  </button>
                </td>
                <td className="px-4 py-3 text-slate-400">{new Date(u.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3">
                  <button
                    disabled={u.id === user.id || deleteMutation.isPending}
                    onClick={() => {
                      if (confirm(`Delete user ${u.email}?`)) deleteMutation.mutate(u.id);
                    }}
                    className="rounded bg-red-600/20 px-2 py-1 text-xs font-semibold text-red-300 hover:bg-red-600/30 disabled:opacity-40"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};