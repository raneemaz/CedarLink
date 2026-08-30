import { useEffect, useState } from "react";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const fieldClass =
  "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none " +
  "focus:border-green-600 focus:ring-1 focus:ring-green-600";

function AdminCategories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const [editId, setEditId] = useState(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    const response = await api.get("/categories");
    setCategories(response.data || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load categories:", error);
          toast.error("Unable to load categories.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!newName.trim()) {
      toast.error("Category name is required.");
      return;
    }
    setCreating(true);
    try {
      await api.post("/categories", {
        name: newName.trim(),
        description: newDescription.trim() || null,
      });
      toast.success("Category created.");
      setNewName("");
      setNewDescription("");
      await load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || "Unable to create the category.",
      );
    } finally {
      setCreating(false);
    }
  };

  const startEdit = (category) => {
    setEditId(category.id);
    setEditName(category.name);
    setEditDescription(category.description || "");
  };

  const saveEdit = async () => {
    if (!editName.trim()) {
      toast.error("Category name is required.");
      return;
    }
    setSavingEdit(true);
    try {
      await api.put(`/categories/${editId}`, {
        name: editName.trim(),
        description: editDescription.trim() || null,
      });
      toast.success("Category updated.");
      setEditId(null);
      await load();
    } catch (error) {
      toast.error(
        error.response?.data?.message || "Unable to update the category.",
      );
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/categories/${deleteTarget.id}`);
      toast.success(`"${deleteTarget.name}" deleted.`);
      await load();
      setDeleteTarget(null);
    } catch (error) {
      toast.error(
        error.response?.data?.message || "Unable to delete the category.",
      );
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading categories...</p>;
  }

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold text-gray-900">Categories</h1>

      <form
        onSubmit={handleCreate}
        className="mb-6 rounded-2xl bg-white p-5 shadow-sm"
      >
        <p className="mb-3 text-sm font-semibold text-gray-700">
          Add a category
        </p>
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-start">
          <input
            type="text"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            placeholder="Name"
            className={fieldClass}
          />
          <input
            type="text"
            value={newDescription}
            onChange={(event) => setNewDescription(event.target.value)}
            placeholder="Description (optional)"
            className={fieldClass}
          />
          <Button type="submit" disabled={creating}>
            {creating ? "Adding..." : "Add"}
          </Button>
        </div>
      </form>

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 text-start text-xs uppercase tracking-wide text-gray-400">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Description</th>
              <th className="px-4 py-3 font-medium text-end">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {categories.map((category) =>
              editId === category.id ? (
                <tr key={category.id} className="bg-emerald-50/40">
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      className={fieldClass}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      value={editDescription}
                      onChange={(event) =>
                        setEditDescription(event.target.value)
                      }
                      className={fieldClass}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-3">
                      <button
                        type="button"
                        onClick={saveEdit}
                        disabled={savingEdit}
                        className="font-medium text-emerald-700 hover:underline disabled:opacity-50"
                      >
                        {savingEdit ? "Saving..." : "Save"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditId(null)}
                        className="font-medium text-gray-500 hover:underline"
                      >
                        Cancel
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={category.id}>
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {category.name}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {category.description || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-4">
                      <button
                        type="button"
                        onClick={() => startEdit(category)}
                        className="font-medium text-emerald-700 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => setDeleteTarget(category)}
                        className="font-medium text-red-600 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete category"
        message={
          deleteTarget
            ? `Delete "${deleteTarget.name}"? Categories that still contain products cannot be deleted.`
            : ""
        }
        confirmLabel="Delete"
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </div>
  );
}

export default AdminCategories;
