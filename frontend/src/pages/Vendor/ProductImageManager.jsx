import { useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";
import { Trash2, Upload } from "lucide-react";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const MAX_IMAGES = 5;
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;

function ProductImageManager({ productId, onImagesChange }) {
  const fileInputRef = useRef(null);

  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const refresh = async () => {
    const response = await api.get(`/products/${productId}`);
    const nextImages = response.data.images || [];
    setImages(nextImages);
    if (onImagesChange) onImagesChange(nextImages);
  };

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const response = await api.get(`/products/${productId}`);
        if (!cancelled) setImages(response.data.images || []);
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load images:", error);
          toast.error("Unable to load product images.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [productId]);

  const atMax = images.length >= MAX_IMAGES;

  const handleFilePicked = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-picking the same file
    if (!file) return;

    if (!ALLOWED_EXT.test(file.name)) {
      toast.error("Use a JPG, PNG, or WEBP image.");
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error("Image is too large. Maximum size is 5 MB.");
      return;
    }
    if (atMax) {
      toast.error(`A product can have at most ${MAX_IMAGES} images.`);
      return;
    }

    const formData = new FormData();
    formData.append("image", file);

    setUploading(true);
    setProgress(0);

    try {
      await api.post(`/products/${productId}/images`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (event) => {
          if (event.total) {
            setProgress(Math.round((event.loaded / event.total) * 100));
          }
        },
      });

      await refresh();
      toast.success("Image uploaded.");
    } catch (error) {
      console.error("Failed to upload image:", error);
      toast.error(
        error.response?.data?.message || "Unable to upload that image.",
      );
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    setDeleting(true);

    try {
      await api.delete(
        `/products/${productId}/images/${deleteTarget.id}`,
      );
      await refresh();
      toast.success("Image removed.");
      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete image:", error);
      toast.error(
        error.response?.data?.message || "Unable to remove that image.",
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
      <div className="border-b border-gray-100 px-6 py-5">
        <h2 className="text-xl font-semibold text-gray-900">
          Product images
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          {images.length} of {MAX_IMAGES} used. The first image is the one
          shoppers see in listings.
        </p>
      </div>

      <div className="px-6 py-6">
        {loading ? (
          <p className="text-sm text-gray-500">Loading images...</p>
        ) : (
          <>
            {images.length > 0 && (
              <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
                {images.map((image) => (
                  <div
                    key={image.id}
                    className="group relative aspect-square overflow-hidden rounded-lg border border-gray-200 bg-gray-50"
                  >
                    <img
                      src={image.url}
                      alt="Product"
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(image)}
                      disabled={uploading || deleting}
                      aria-label="Remove image"
                      className="absolute right-2 top-2 rounded-md bg-white/90 p-1.5 text-red-600 shadow-sm transition hover:bg-white disabled:opacity-50"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFilePicked}
            />

            {atMax ? (
              <p className="rounded-lg bg-gray-50 px-4 py-3 text-sm text-gray-500">
                You have reached the maximum of {MAX_IMAGES} images. Remove
                one to upload another.
              </p>
            ) : uploading ? (
              <div className="rounded-lg border border-gray-200 px-4 py-3">
                <p className="text-sm text-gray-600">
                  Uploading... {progress}%
                </p>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
                  <div
                    className="h-full rounded-full bg-emerald-600 transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={deleting}
                className="flex items-center gap-2 rounded-lg border border-dashed border-gray-300 px-4 py-3 text-sm font-medium text-gray-700 transition hover:border-emerald-600 hover:text-emerald-700 disabled:opacity-50"
              >
                <Upload size={16} />
                Upload image
              </button>
            )}

            <p className="mt-2 text-xs text-gray-400">
              JPG, PNG or WEBP, up to 5 MB. One file at a time.
            </p>
          </>
        )}
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Remove image"
        message="Remove this image? This cannot be undone."
        confirmLabel="Remove"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </section>
  );
}

export default ProductImageManager;
