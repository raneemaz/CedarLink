import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Trash2, Upload } from "lucide-react";

import api from "../../services/api";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const MAX_IMAGES = 5;
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;

function ProductImageManager({ productId, onImagesChange }) {
  const { t } = useTranslation();
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
          toast.error(t("productImages.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [productId, t]);

  const atMax = images.length >= MAX_IMAGES;

  const handleFilePicked = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-picking the same file
    if (!file) return;

    if (!ALLOWED_EXT.test(file.name)) {
      toast.error(t("productImages.errUseFormat"));
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error(t("productImages.errTooLarge"));
      return;
    }
    if (atMax) {
      toast.error(t("productImages.errAtMax", { max: MAX_IMAGES }));
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
      toast.success(t("productImages.toastUploaded"));
    } catch (error) {
      console.error("Failed to upload image:", error);
      toast.error(
        error.response?.data?.message || t("productImages.errUpload"),
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
      toast.success(t("productImages.toastRemoved"));
      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete image:", error);
      toast.error(
        error.response?.data?.message || t("productImages.errRemove"),
      );
    } finally {
      setDeleting(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl bg-paper-raised shadow-sm">
      <div className="border-b border-line-subtle px-6 py-5">
        <h2 className="text-xl font-semibold text-ink">
          {t("productImages.sectionTitle")}
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          {t("productImages.usage", { count: images.length, max: MAX_IMAGES })}
        </p>
      </div>

      <div className="px-6 py-6">
        {loading ? (
          <p className="text-sm text-ink-muted">{t("productImages.loading")}</p>
        ) : (
          <>
            {images.length > 0 && (
              <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
                {images.map((image) => (
                  <div
                    key={image.id}
                    className="group relative aspect-square overflow-hidden rounded-lg border border-line bg-paper"
                  >
                    <img
                      src={image.url}
                      alt={t("productImages.imageAlt")}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(image)}
                      disabled={uploading || deleting}
                      aria-label={t("productImages.removeImage")}
                      className="absolute end-2 top-2 rounded-md bg-paper-raised/90 p-1.5 text-danger shadow-sm transition hover:bg-paper-raised disabled:opacity-50"
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
              <p className="rounded-lg bg-paper px-4 py-3 text-sm text-ink-muted">
                {t("productImages.atMax", { max: MAX_IMAGES })}
              </p>
            ) : uploading ? (
              <div className="rounded-lg border border-line px-4 py-3">
                <p className="text-sm text-ink-secondary">
                  {t("productImages.uploading", { progress })}
                </p>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-paper-sunken">
                  <div
                    className="h-full rounded-full bg-cedar-ring transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={deleting}
                className="flex items-center gap-2 rounded-lg border border-dashed border-line-strong px-4 py-3 text-sm font-medium text-ink-body transition hover:border-cedar-ring hover:text-cedar disabled:opacity-50"
              >
                <Upload size={16} />
                {t("productImages.uploadImage")}
              </button>
            )}

            <p className="mt-2 text-xs text-ink-faint">
              {t("productImages.formats")}
            </p>
          </>
        )}
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("productImages.removeTitle")}
        message={t("productImages.removeMessage")}
        confirmLabel={t("productImages.remove")}
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </section>
  );
}

export default ProductImageManager;
