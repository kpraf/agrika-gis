import React, { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import DashboardSidebar from "../layout/DashboardSidebar";
import { usersApi } from "../../lib/api";

const ROLE_META = {
  administrator: { label: "Administrator", scope: "Province-wide Access" },
  agriculturist: { label: "Agriculturist", scope: "Municipality Access" },
  rice_technician: { label: "Rice Technician", scope: "Field Operations" },
};

const roleLabel = (role) => ROLE_META[role]?.label || role || "—";
const roleScope = (role) => ROLE_META[role]?.scope || "";

const BADGE_COLORS = [
  { bg: "#DBEAFE", text: "#1D4ED8" },
  { bg: "#FFEDD5", text: "#C2410C" },
  { bg: "#F3E8FF", text: "#7E22CE" },
  { bg: "#FEF9C3", text: "#A16207" },
  { bg: "#DCFCE7", text: "#15803D" },
  { bg: "#E0E7FF", text: "#4338CA" },
];

function badgeFor(municipality) {
  if (!municipality) return { bg: "#F3F4F6", text: "#6B7280" };
  let hash = 0;
  for (let i = 0; i < municipality.length; i++) hash = (hash * 31 + municipality.charCodeAt(i)) % BADGE_COLORS.length;
  return BADGE_COLORS[hash];
}

const displayName = (u) => u.full_name || u.username;

function initials(name) {
  const parts = (name || "").split(" ").filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function SortIcon({ direction }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="shrink-0">
      <path d="M3 4.5L6 1.5L9 4.5" stroke={direction === "asc" ? "#1F2937" : "#D1D5DB"} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 7.5L6 10.5L9 7.5" stroke={direction === "desc" ? "#1F2937" : "#D1D5DB"} strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UserForm({ initial, roles, municipalities, onCancel, onSave }) {
  const isEdit = !!initial;
  const [fullName, setFullName] = useState(initial?.full_name || "");
  const [username, setUsername] = useState(initial?.username || "");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState(initial?.role || roles[0] || "agriculturist");
  const [municipalityId, setMunicipalityId] = useState(
    initial?.municipality_id || municipalities[0]?.id || ""
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!username.trim()) return setError("Username is required.");
    if (!isEdit && !password) return setError("Password is required for a new user.");

    const payload = {
      full_name: fullName.trim(),
      role,
      status: initial?.status || "Active",
      municipality_id: role === "administrator" ? null : Number(municipalityId) || null,
    };
    if (!isEdit) payload.username = username.trim();
    if (password) payload.password = password;

    setSaving(true);
    try {
      await onSave(initial, payload);
    } catch (err) {
      setError(err.message || "Save failed.");
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form onSubmit={submit} className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6 flex flex-col gap-4">
        <h2 className="text-lg font-bold text-[#1F2937]">{isEdit ? "Edit User" : "Add User"}</h2>

        {error && (
          <div className="px-3 py-2 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
        )}

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-[#4B5563]">Full Name</span>
          <input
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="e.g. Juan Dela Cruz"
            className="px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none focus:border-[#1F6306]"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-[#4B5563]">Username {isEdit && <span className="text-[#9CA3AF]">(can't be changed)</span>}</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isEdit}
            required
            className="px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none focus:border-[#1F6306] disabled:bg-[#F3F4F6] disabled:text-[#6B7280]"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-[#4B5563]">
            Password {isEdit && <span className="text-[#9CA3AF]">(leave blank to keep current)</span>}
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={isEdit ? "••••••••" : "Set a password"}
            className="px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none focus:border-[#1F6306]"
          />
        </label>

        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-[#4B5563]">Role</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none"
          >
            {roles.map((r) => (
              <option key={r} value={r}>
                {roleLabel(r)}
              </option>
            ))}
          </select>
        </label>

        {role !== "administrator" && (
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-[#4B5563]">Municipality / LGU</span>
            <select
              value={municipalityId}
              onChange={(e) => setMunicipalityId(e.target.value)}
              className="px-3 py-2 border border-[#E5E7EB] rounded-lg outline-none"
            >
              {municipalities.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onCancel} className="px-4 py-2 rounded-lg text-sm font-medium text-[#4B5563] hover:bg-[#F3F4F6]">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="px-4 py-2 rounded-lg bg-[#1F6306] text-white text-sm font-semibold hover:bg-[#286A11] disabled:opacity-60">
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </div>
  );
}

export default function UserAccessManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [municipalities, setMunicipalities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState(new Set());
  const [showFilter, setShowFilter] = useState(false);
  const [sort, setSort] = useState({ field: "name", direction: "asc" });
  const [selected, setSelected] = useState(new Set());
  const [formState, setFormState] = useState(null); // null | "new" | user object
  const [menuOpenFor, setMenuOpenFor] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const refetch = useCallback(async () => {
    const list = await usersApi.list();
    setUsers(list);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [list, meta] = await Promise.all([usersApi.list(), usersApi.meta()]);
        if (!active) return;
        setUsers(list);
        setRoles(meta.roles || []);
        setMunicipalities(meta.municipalities || []);
      } catch (err) {
        if (active) setError(err.message || "Failed to load users.");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users.filter((u) => {
      if (roleFilter.size && !roleFilter.has(u.role)) return false;
      if (!q) return true;
      return (
        (u.username || "").toLowerCase().includes(q) ||
        (u.full_name || "").toLowerCase().includes(q) ||
        roleLabel(u.role).toLowerCase().includes(q) ||
        (u.municipality || "").toLowerCase().includes(q)
      );
    });
  }, [users, search, roleFilter]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      let av, bv;
      if (sort.field === "role") {
        av = roleLabel(a.role);
        bv = roleLabel(b.role);
      } else if (sort.field === "status") {
        av = a.status;
        bv = b.status;
      } else {
        av = displayName(a);
        bv = displayName(b);
      }
      const cmp = String(av).localeCompare(String(bv));
      return sort.direction === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [filtered, sort]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageRows = sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const toggleSort = (field) => {
    setSort((prev) => (prev.field === field ? { field, direction: prev.direction === "asc" ? "desc" : "asc" } : { field, direction: "asc" }));
  };

  const toggleRoleFilter = (role) => {
    setRoleFilter((prev) => {
      const next = new Set(prev);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  };

  const allOnPageSelected = pageRows.length > 0 && pageRows.every((u) => selected.has(u.id));
  const toggleSelectAll = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (allOnPageSelected) pageRows.forEach((u) => next.delete(u.id));
      else pageRows.forEach((u) => next.add(u.id));
      return next;
    });
  };
  const toggleSelectRow = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ---- API-backed actions ----
  const runAction = async (fn) => {
    setError("");
    try {
      await fn();
      await refetch();
    } catch (err) {
      setError(err.message || "Action failed.");
    }
  };

  const handleSave = async (initial, payload) => {
    if (initial) await usersApi.update(initial.id, payload);
    else await usersApi.create(payload);
    await refetch();
    setFormState(null);
  };

  const toggleStatus = (u) =>
    runAction(async () => {
      await usersApi.update(u.id, { status: u.status === "Active" ? "Inactive" : "Active" });
      setMenuOpenFor(null);
    });

  const deleteUser = (u) =>
    runAction(async () => {
      await usersApi.remove(u.id);
      setMenuOpenFor(null);
    });

  const bulkSetStatus = (status) =>
    runAction(async () => {
      await Promise.all([...selected].map((id) => usersApi.update(id, { status })));
      setSelected(new Set());
    });

  const bulkDelete = () =>
    runAction(async () => {
      await Promise.all([...selected].map((id) => usersApi.remove(id)));
      setSelected(new Set());
    });

  return (
    <div className="flex w-full h-screen bg-white font-sans" style={{ fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
      <DashboardSidebar active="settings" />

      <div className="flex flex-col flex-1 min-w-0">
        <header className="flex items-center justify-between px-10 h-20 shrink-0 bg-white border-b border-[#E5E7EB]">
          <h1 className="text-2xl font-bold text-[#1F2937] tracking-[-0.6px]">User Access Management</h1>
        </header>

        <div className="flex-1 overflow-y-auto bg-white p-8">
          <div className="bg-white border border-[#F3F4F6] shadow-sm rounded-2xl overflow-hidden flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-[#F3F4F6]">
              <div className="pb-1 border-b-2 border-[#1F6306] text-sm font-semibold text-[#1F6306]">Users</div>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowFilter((v) => !v)}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-[#E5E7EB] rounded-lg text-sm font-medium text-[#374151] shadow-sm"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 6h16M7 12h10M10 18h4" />
                    </svg>
                    Filter
                    {roleFilter.size > 0 && (
                      <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-[#1F6306] text-white">{roleFilter.size}</span>
                    )}
                  </button>
                  {showFilter && (
                    <div className="absolute right-0 mt-2 w-56 bg-white border border-[#E5E7EB] rounded-xl shadow-lg p-3 z-20 flex flex-col gap-2">
                      <span className="text-xs font-semibold uppercase text-[#9CA3AF] px-1">Filter by role</span>
                      {(roles.length ? roles : Object.keys(ROLE_META)).map((key) => (
                        <label key={key} className="flex items-center gap-2 px-1 py-1 text-sm text-[#374151] cursor-pointer">
                          <input type="checkbox" checked={roleFilter.has(key)} onChange={() => toggleRoleFilter(key)} className="accent-[#1F6306]" />
                          {roleLabel(key)}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => setFormState("new")}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#1F6306] text-white text-sm font-semibold shadow-md hover:bg-[#286A11]"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                  Add User
                </button>
              </div>
            </div>

            {/* Error banner */}
            {error && (
              <div className="flex items-center justify-between px-6 py-3 bg-red-50 border-b border-red-200 text-sm text-red-700">
                <span>{error}</span>
                <button onClick={() => setError("")} className="text-red-500 hover:text-red-700">✕</button>
              </div>
            )}

            {/* Search + Sort */}
            <div className="flex items-center justify-between gap-4 px-6 py-4 border-b border-[#F3F4F6] flex-wrap">
              <div className="relative flex-1 min-w-[240px] max-w-[448px]">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-3 top-1/2 -translate-y-1/2">
                  <circle cx="11" cy="11" r="7" />
                  <path d="M21 21l-3.5-3.5" />
                </svg>
                <input
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Search by name, username, role, or LGU..."
                  className="w-full pl-9 pr-3 py-2.5 text-sm bg-[#F9FAFB] border border-[#E5E7EB] rounded-lg outline-none focus:border-[#1F6306]"
                />
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-[#9CA3AF]">Sort:</span>
                <select
                  value={sort.field}
                  onChange={(e) => setSort((prev) => ({ ...prev, field: e.target.value }))}
                  className="px-2 py-1.5 border border-[#E5E7EB] rounded-lg text-[#374151] outline-none"
                >
                  <option value="name">Name</option>
                  <option value="role">Role</option>
                  <option value="status">Status</option>
                </select>
              </div>
            </div>

            {/* Bulk actions */}
            {selected.size > 0 && (
              <div className="flex items-center justify-between px-6 py-3 bg-[#F0FDF4] border-b border-[#DCFCE7]">
                <span className="text-sm font-medium text-[#15803D]">{selected.size} selected</span>
                <div className="flex gap-2">
                  <button onClick={() => bulkSetStatus("Active")} className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-[#DCFCE7] text-[#15803D]">
                    Activate
                  </button>
                  <button onClick={() => bulkSetStatus("Inactive")} className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-[#E5E7EB] text-[#4B5563]">
                    Deactivate
                  </button>
                  <button onClick={bulkDelete} className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-[#FECACA] text-[#DC2626]">
                    Delete
                  </button>
                </div>
              </div>
            )}

            {/* Pagination info top */}
            <div className="flex items-center justify-between px-6 py-3 text-sm text-[#6B7280]">
              <span>
                {loading
                  ? "Loading users…"
                  : `Showing ${pageRows.length ? (currentPage - 1) * pageSize + 1 : 0}–${(currentPage - 1) * pageSize + pageRows.length} of ${sorted.length} results`}
              </span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="px-2 py-1 border border-[#E5E7EB] rounded-lg bg-[#F9FAFB] text-[#374151] outline-none"
              >
                {[10, 25, 50].map((n) => (
                  <option key={n} value={n}>
                    {n} / page
                  </option>
                ))}
              </select>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-[#F9FAFB]/80 border-y border-[#E5E7EB]">
                  <tr>
                    <th className="px-6 py-3 w-10">
                      <input type="checkbox" checked={allOnPageSelected} onChange={toggleSelectAll} className="accent-[#1F6306]" />
                    </th>
                    <th className="px-4 py-3 text-left">
                      <button onClick={() => toggleSort("name")} className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[#6B7280]">
                        User <SortIcon direction={sort.field === "name" ? sort.direction : null} />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left">
                      <button onClick={() => toggleSort("role")} className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[#6B7280]">
                        Role <SortIcon direction={sort.field === "role" ? sort.direction : null} />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[#6B7280]">Municipality</th>
                    <th className="px-4 py-3 text-left">
                      <button onClick={() => toggleSort("status")} className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-[#6B7280]">
                        Status <SortIcon direction={sort.field === "status" ? sort.direction : null} />
                      </button>
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-[#6B7280]">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((u) => {
                    const badge = badgeFor(u.municipality);
                    return (
                      <tr key={u.id} className="border-t border-[#F3F4F6] hover:bg-[#F9FAFB]/60">
                        <td className="px-6 py-4">
                          <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggleSelectRow(u.id)} className="accent-[#1F6306]" />
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-3">
                            <span className="flex items-center justify-center w-10 h-10 rounded-full bg-[#E1EDE0] text-[#1F6306] font-semibold text-sm shrink-0">
                              {initials(displayName(u))}
                            </span>
                            <div className="flex flex-col">
                              <span className="font-semibold text-[#1F6306]">{displayName(u)}</span>
                              <span className="text-xs text-[#6B7280]">@{u.username}</span>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex flex-col">
                            <span className="text-[#4B5563]">{roleLabel(u.role)}</span>
                            <span className="text-xs text-[#6B7280]">{roleScope(u.role)}</span>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-2">
                            <span
                              className="flex items-center justify-center w-8 h-8 rounded-lg text-xs font-bold shrink-0"
                              style={{ background: badge.bg, color: badge.text }}
                            >
                              {u.municipality ? u.municipality.replace(/^City of /, "").slice(0, 2).toUpperCase() : "ALL"}
                            </span>
                            <span className="text-[#1F2937] font-medium">{u.municipality || "All Municipalities"}</span>
                          </div>
                        </td>
                        <td className="px-4 py-4">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                              u.status === "Active" ? "bg-[#F0FDF4] border border-[#DCFCE7] text-[#15803D]" : "bg-[#F3F4F6] border border-[#E5E7EB] text-[#374151]"
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full ${u.status === "Active" ? "bg-[#22C55E]" : "bg-[#9CA3AF]"}`} />
                            {u.status}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          <div className="relative flex justify-end">
                            <button
                              type="button"
                              onClick={() => setFormState(u)}
                              className="p-2 rounded-lg text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#4B5563]"
                              aria-label={`Edit ${displayName(u)}`}
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 20h9M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
                              </svg>
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                if (menuOpenFor === u.id) {
                                  setMenuOpenFor(null);
                                  return;
                                }
                                const r = e.currentTarget.getBoundingClientRect();
                                setMenuPos({ top: r.bottom + 4, left: r.right - 176 });
                                setMenuOpenFor(u.id);
                              }}
                              className="p-2 rounded-lg text-[#9CA3AF] hover:bg-[#F3F4F6] hover:text-[#4B5563]"
                              aria-label={`More actions for ${displayName(u)}`}
                            >
                              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
                                <circle cx="5" cy="12" r="1.5" />
                                <circle cx="12" cy="12" r="1.5" />
                                <circle cx="19" cy="12" r="1.5" />
                              </svg>
                            </button>
                            {menuOpenFor === u.id &&
                              createPortal(
                                <div className="fixed inset-0 z-[9998]" onClick={() => setMenuOpenFor(null)}>
                                  <div
                                    className="fixed w-44 bg-white border border-[#E5E7EB] rounded-xl shadow-lg py-1 z-[9999]"
                                    style={{ top: menuPos.top, left: menuPos.left }}
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    <button
                                      onClick={() => {
                                        setMenuOpenFor(null);
                                        toggleStatus(u);
                                      }}
                                      className="w-full text-left px-4 py-2 text-sm text-[#374151] hover:bg-[#F9FAFB]"
                                    >
                                      Mark as {u.status === "Active" ? "Inactive" : "Active"}
                                    </button>
                                    <button
                                      onClick={() => {
                                        setMenuOpenFor(null);
                                        deleteUser(u);
                                      }}
                                      className="w-full text-left px-4 py-2 text-sm text-[#DC2626] hover:bg-[#FEF2F2]"
                                    >
                                      Delete User
                                    </button>
                                  </div>
                                </div>,
                                document.body
                              )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {!loading && !pageRows.length && (
                    <tr>
                      <td colSpan={6} className="px-6 py-10 text-center text-sm text-[#9CA3AF]">
                        No users match your search or filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            <div className="flex items-center justify-between px-6 py-4 border-t border-[#F3F4F6]">
              <span className="text-sm text-[#6B7280]">
                Page {currentPage} of {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={currentPage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-3 py-1.5 text-sm rounded-lg border border-[#E5E7EB] text-[#374151] disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={currentPage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="px-3 py-1.5 text-sm rounded-lg border border-[#E5E7EB] text-[#374151] disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {formState && (
        <UserForm
          initial={formState === "new" ? null : formState}
          roles={roles.length ? roles : Object.keys(ROLE_META)}
          municipalities={municipalities}
          onCancel={() => setFormState(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
