import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Trash2, Upload } from "lucide-react";

import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const MAX_IMAGES = 5;
const MAX_BYTES = 5 * 1024 * 1024;
const ALLOWED_EXT = /\.(jpe?g|png|webp)$/i;

let nextDraftImageId = -1;

/**
 * Image picker for a product that doesn't exist yet. `ProductImageManager`
 * uploads straight to `/products/:id/images` and can't run before that id
 * exists; this instead just holds the picked files (with local object-URL
 * previews) in memory, and hands the current list back through `onChange`
 * so the parent form can upload them, in order, once the product itself has
 * been created.
 */
function DraftImagePicker({ images, onChange }) {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  // Object URLs are only good for this tab's lifetime -- release them when
  // the picker (and with it, the add-product page) goes away.
  const imagesRef = useRef(images);
  useEffect(() => {
    imagesRef.current = images;
  }, [images]);
  useEffect(() => {
    return () => {
      imagesRef.current.forEach((image) => URL.revokeObjectURL(image.previewUrl));
    };
  }, []);

  const atMax = images.length >= MAX_IMAGES;

  const handleFilePicked = (event) => {
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

    onChange([
      ...images,
      { id: nextDraftImageId--, file, previewUrl: URL.createObjectURL(file) },
    ]);
  };

  const handleConfirmDelete = () => {
    if (!deleteTarget) return;
    URL.revokeObjectURL(deleteTarget.previewUrl);
    onChange(images.filter((image) => image.id !== deleteTarget.id));
    setDeleteTarget(null);
  };

  return (
    <section className="overflow-hidden rounded-card bg-paper-raised shadow-card">
      <div className="border-b border-line-subtle px-6 py-5">
        <h2 className="text-title font-semibold text-ink">
          {t("productImages.sectionTitle")}
        </h2>
        <p className="mt-1 text-small text-ink-muted">
          {t("productImages.usage", { count: images.length, max: MAX_IMAGES })}
        </p>
      </div>

      <div className="px-6 py-6">
        {images.length > 0 && (
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {images.map((image) => (
              <div
                key={image.id}
                className="group relative aspect-square overflow-hidden rounded-control border border-line bg-paper"
              >
                <img
                  src={image.previewUrl}
                  alt={t("productImages.imageAlt")}
                  className="h-full w-full object-cover"
                />
                <button
                  type="button"
                  onClick={() => setDeleteTarget(image)}
                  aria-label={t("productImages.removeImage")}
                  className="absolute end-2 top-2 rounded-control bg-paper-raised/90 p-1.5 text-danger shadow-card transition hover:bg-paper-raised"
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
          <p className="rounded-control bg-paper px-4 py-3 text-small text-ink-muted">
            {t("productImages.atMax", { max: MAX_IMAGES })}
          </p>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 rounded-control border border-dashed border-line-strong px-4 py-3 text-small font-medium text-ink-body transition hover:border-cedar-ring hover:text-cedar"
          >
            <Upload size={16} />
            {t("productImages.uploadImage")}
          </button>
        )}

        <p className="mt-2 text-micro text-ink-faint">
          {t("productImages.formats")}
        </p>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("productImages.removeTitle")}
        message={t("productImages.removeMessage")}
        confirmLabel={t("productImages.remove")}
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}

export default DraftImagePicker;
